#!/usr/bin/env python3
"""电子书清洗与整理脚本

目标文件：十年一觉电影梦-李安传 (张靓蓓  李安) (z-library.sk, 1lib.sk, z-lib.sk).mobi

功能：
1. 将 MOBI 转成 TXT
2. 去掉页眉页脚、目录、ISBN 等无关信息
3. 按章节/主题切块，约500-800字一段
4. 为每个段落打上标签，生成 JSONL 输出

用法：
    python process_mobi_book.py
    python process_mobi_book.py --source "你的文件.mobi" --output-dir output

如果本机安装了 `ebook-convert`，脚本会优先使用它转换 MOBI。
否则会尝试使用 Python 包 `mobi`。
"""

import argparse
import html
import json
import re
import shutil
import subprocess
import zipfile
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import xml.etree.ElementTree as ET

import openai
import requests

DEFAULT_SOURCE = Path("十年一觉电影梦-李安传 (张靓蓓  李安) (z-library.sk, 1lib.sk, z-lib.sk).mobi")

TAG_KEYWORDS = {
    "构图": ["构图", "画面", "镜头", "视线", "框架", "画幅", "取景"],
    "光线": ["光线", "光影", "照明", "明暗", "光线", "阴影", "色温"],
    "调度": ["调度", "机位", "运动", "移动", "运动", "镜头语言", "节奏"],
    "情感控制": ["情绪", "情感", "氛围", "张力", "表达", "节奏", "感受"],
    "剪辑": ["剪辑", "截断", "切换", "蒙太奇", "衔接"],
    "声音": ["声音", "音乐", "对白", "音效", "声响"],
}

NOISE_PATTERNS = [
    r"ISBN[:：]?\s*\S+",
    r"©.*",
    r"版权所有.*",
    r"本书.*出版.*",
    r"目录",
    r"Table of Contents",
    r"All rights reserved",
    r"本文件由.*提供",
    r"第\s*\d+\s*页",
    r"第[一二三四五六七八九十百千]+[章节]?",
]


def check_command(name: str) -> bool:
    return shutil.which(name) is not None


def _extract_text_from_html(html_text: str) -> str:
    text = re.sub(r"<script[\s\S]*?</script>", " ", html_text, flags=re.IGNORECASE)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</(p|div|li|tr|section|article|h[1-6])>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", "\n", text)
    return text.strip()


def _extract_text_from_epub(epub_path: Path) -> str:
    with zipfile.ZipFile(epub_path) as zf:
        parts: List[str] = []
        for name in sorted(zf.namelist()):
            if not name.endswith((".xhtml", ".html", ".xml")):
                continue
            try:
                raw = zf.read(name).decode("utf-8", errors="ignore")
            except Exception:
                continue
            parts.append(_extract_text_from_html(raw))
        return "\n\n".join(part for part in parts if part)


def _extract_text_from_path(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"未找到提取结果文件：{path}")

    suffix = path.suffix.lower()
    if suffix in {".html", ".htm"}:
        return _extract_text_from_html(path.read_text(encoding="utf-8", errors="ignore"))
    if suffix == ".epub":
        return _extract_text_from_epub(path)
    return path.read_text(encoding="utf-8", errors="ignore")


def convert_mobi_to_txt(source: Path, target: Path) -> None:
    if source.suffix.lower() != ".mobi":
        raise ValueError("当前脚本只支持 MOBI 文件转换")

    if not source.exists():
        raise FileNotFoundError(f"未找到 MOBI 文件：{source}")

    if check_command("ebook-convert"):
        print("使用 ebook-convert 进行 MOBI -> TXT 转换...")
        subprocess.run(["ebook-convert", str(source), str(target)], check=True)
        return

    try:
        from mobi import extract as mobi_extract
    except ImportError as exc:
        raise RuntimeError(
            "没有找到 ebook-convert，也没有安装可用的 Python MOBI 解析入口。请安装 Calibre 的 ebook-convert，或确认 mobi 包版本可用。"
        ) from exc

    print("使用 Python mobi 包进行 MOBI 解析...")
    try:
        result = mobi_extract(str(source))
    except Exception as exc:
        raise RuntimeError(f"MOBI 文件解析失败：{exc}") from exc

    extracted_path: Optional[Path] = None
    if isinstance(result, tuple) and len(result) >= 2:
        candidate = result[1]
        extracted_path = Path(candidate)
    elif isinstance(result, (str, Path)):
        extracted_path = Path(result)

    if extracted_path is None:
        raise RuntimeError("MOBI 解析未返回可用的提取文件路径。")

    text = _extract_text_from_path(extracted_path)
    if not text.strip():
        raise RuntimeError(
            "MOBI 文件解析成功，但未提取到可用文本。请安装 Calibre 的 ebook-convert："
            "https://calibre-ebook.com/，然后再运行脚本。"
        )

    target.write_text(text, encoding="utf-8")


def remove_repeated_noise(text: str, min_occurrences: int = 8) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    counts = Counter(lines)
    repeated = {line for line, count in counts.items() if count >= min_occurrences and len(line) < 80}
    if not repeated:
        return text
    return "\n".join(line for line in text.splitlines() if line.strip() not in repeated)


def clean_text(raw: str) -> str:
    text = raw.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)

    for pattern in NOISE_PATTERNS:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE | re.MULTILINE)

    text = remove_repeated_noise(text)
    text = re.sub(r"\n{2,}", "\n\n", text)
    text = text.strip()
    return text


def split_into_chunks(text: str, min_size: int = 500, max_size: int = 800) -> List[str]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if len(p.strip()) >= 80]
    chunks: List[str] = []

    for para in paragraphs:
        if len(para) <= max_size:
            chunks.append(para)
            continue

        current = []
        current_len = 0
        sentences = re.split(r"(?<=[。！？!?])", para)
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            if current_len + len(sentence) > max_size and current:
                chunks.append("".join(current).strip())
                current = [sentence]
                current_len = len(sentence)
            else:
                current.append(sentence)
                current_len += len(sentence)

        if current:
            combined = "".join(current).strip()
            if len(combined) < min_size and chunks:
                chunks[-1] = chunks[-1] + "\n" + combined
            else:
                chunks.append(combined)

    return chunks


def tag_paragraph(paragraph: str) -> str:
    for tag, keywords in TAG_KEYWORDS.items():
        for keyword in keywords:
            if keyword in paragraph:
                return tag
    return "综合"


def build_output(chunks: List[str], output_dir: Path) -> Path:
    jsonl_path = output_dir / "paragraphs.jsonl"
    text_path = output_dir / "cleaned_text.txt"
    metadata_path = output_dir / "metadata.json"

    with jsonl_path.open("w", encoding="utf-8") as fh:
        for idx, chunk in enumerate(chunks, start=1):
            record = {
                "id": idx,
                "tag": tag_paragraph(chunk),
                "text": chunk,
                "char_count": len(chunk),
            }
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    with text_path.open("w", encoding="utf-8") as fh:
        fh.write("\n\n".join(chunks))

    metadata = {
        "source": str(DEFAULT_SOURCE),
        "paragraph_count": len(chunks),
        "average_chars": sum(len(c) for c in chunks) / len(chunks) if chunks else 0,
        "tags": list(TAG_KEYWORDS.keys()) + ["综合"],
    }
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return jsonl_path


def batch_items(items: List[str], batch_size: int = 64):
    for i in range(0, len(items), batch_size):
        yield items[i : i + batch_size]


def embed_with_openai(texts: List[str], api_key: str, model: str = "text-embedding-3-small") -> List[List[float]]:
    if not api_key:
        raise RuntimeError("请提供 OpenAI API Key 才能执行 OpenAI 嵌入。")

    try:
        client = openai.OpenAI(api_key=api_key)
    except Exception:
        client = None
        openai.api_key = api_key

    embeddings: List[List[float]] = []
    for batch in batch_items(texts, batch_size=64):
        if client is not None:
            response = client.embeddings.create(model=model, input=batch)
            items = response.data
        else:
            response = openai.Embedding.create(model=model, input=batch)
            items = response["data"]

        for item in items:
            if hasattr(item, "embedding"):
                embeddings.append(list(item.embedding))
            else:
                embeddings.append(list(item["embedding"]))
    return embeddings


def embed_with_nomic(texts: List[str], url: str = "http://127.0.0.1:3000/v1/embeddings", model: str = "nomic-embed-text") -> List[List[float]]:
    if not url:
        raise RuntimeError("请提供 Nomic embedding 服务地址。")

    embeddings: List[List[float]] = []
    for batch in batch_items(texts, batch_size=64):
        payload = {"model": model, "input": batch}
        response = requests.post(url, json=payload, timeout=120)
        response.raise_for_status()
        data = response.json()
        embeddings.extend(item["embedding"] for item in data["data"])
    return embeddings


def store_embeddings_lancedb(chunks: List[str], output_dir: Path, embeddings: List[List[float]]) -> Path:
    try:
        from lancedb import connect
    except ImportError as exc:
        raise RuntimeError(
            "LanceDB 未安装。请运行 pip install lancedb 或 pip install lance。"
        ) from exc

    if len(chunks) != len(embeddings):
        raise RuntimeError(f"分段数量 {len(chunks)} 与嵌入数量 {len(embeddings)} 不一致。")

    db_path = output_dir / "lancedb"
    db = connect(str(db_path))

    schema = {
        "id": "int32",
        "tag": "str",
        "text": "str",
        "embedding": "list<float>",
    }

    if "li_an_book" in db.table_names():
        table = db.get_table("li_an_book")
    else:
        table = db.create_table(name="li_an_book", schema=schema)

    rows = []
    for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings), start=1):
        rows.append({
            "id": idx,
            "tag": tag_paragraph(chunk),
            "text": chunk,
            "embedding": embedding,
        })

    if rows:
        table.insert(rows)
    try:
        table.create_index("embedding")
    except Exception:
        pass

    return db_path


def main() -> None:
    parser = argparse.ArgumentParser(description="清洗 MOBI 电子书并切分成段落。")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE, help="MOBI 源文件路径")
    parser.add_argument("--output-dir", type=Path, default=Path("output"), help="输出目录")
    parser.add_argument("--skip-convert", action="store_true", help="跳过 MOBI -> TXT 转换，直接读取已有 TXT")
    parser.add_argument("--txt-file", type=Path, help="如果已存在 TXT，可直接指定该文件")
    parser.add_argument("--embed", action="store_true", help="生成段落向量并存储到 LanceDB")
    parser.add_argument("--use-nomic", action="store_true", help="使用本地 Nomic embedding 服务，而非 OpenAI")
    parser.add_argument("--nomic-url", type=str, default="http://127.0.0.1:3000/v1/embeddings", help="本地 Nomic embedding 服务地址")
    parser.add_argument("--nomic-model", type=str, default="nomic-embed-text", help="Nomic 嵌入模型名称")
    parser.add_argument("--openai-api-key", type=str, default=None, help="OpenAI API Key，用于 OpenAI 嵌入")
    parser.add_argument("--embedding-model", type=str, default="text-embedding-3-small", help="OpenAI 嵌入模型")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    if args.skip_convert and args.txt_file:
        txt_path = args.txt_file
    else:
        txt_path = args.output_dir / f"{args.source.stem}.txt"
        if not txt_path.exists():
            convert_mobi_to_txt(args.source, txt_path)

    print(f"读取文本：{txt_path}")
    raw_text = txt_path.read_text(encoding="utf-8", errors="ignore")
    cleaned = clean_text(raw_text)
    chunks = split_into_chunks(cleaned)
    output_path = build_output(chunks, args.output_dir)

    print(f"清洗完成，段落数量：{len(chunks)}")
    print(f"输出文件：{output_path}")
    print(f"完整文本存储：{args.output_dir / 'cleaned_text.txt'}")
    print(f"元数据存储：{args.output_dir / 'metadata.json'}")

    if args.embed:
        print("开始生成嵌入向量...")
        if args.use_nomic:
            embeddings = embed_with_nomic(chunks, url=args.nomic_url, model=args.nomic_model)
            print(f"使用 Nomic 嵌入，批次数量：{len(list(batch_items(chunks, 64)))}")
        else:
            embeddings = embed_with_openai(chunks, args.openai_api_key or "", model=args.embedding_model)
            print(f"使用 OpenAI 嵌入，模型：{args.embedding_model}")

        db_path = store_embeddings_lancedb(chunks, args.output_dir, embeddings)
        print(f"LanceDB 存储完成：{db_path}")


if __name__ == "__main__":
    main()
