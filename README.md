# FilmLens Agent Console

一个把李安式思考、电影分析和日常闲聊放在一起的对话项目。支持图片分析、文字对话和电影信息检索，回答会尽量保持李安第一人称口吻，偏口语化、克制、自然。

## 功能
- 图片分析：上传截图或剧照，分析构图、光线、空间和情绪
- 文字闲聊：按李安的思路思考，用第一人称回应
- 电影检索：可调用 OMDb 获取电影信息
- 图片预览：聊天中的图片可以点开查看大图
- 本地配置：保存 API Key 和模型设置

## 技术栈
- 后端：FastAPI + Agno
- 前端：React + Vite + MUI
- 存储：SQLite
- 资源：`skill/` 下的李安 skill 与 `output/paragraphs.jsonl` 语料

## 项目结构

```text
.
├── app.py                 # 主应用入口（后端 + Agent）
├── frontend/              # React 前端源码
├── image_utils.py         # 图片处理辅助
├── output/                # 语料清洗结果与元数据
├── process_mobi_book.py   # 书籍语料生成脚本
├── requirements.txt       # Python 依赖
├── skill/                 # 李安对话 skill
└── README.md              # 项目说明
```

## 运行方式
1. 安装后端依赖
```bash
pip install -r requirements.txt
```

2. 安装前端依赖并构建
```bash
cd frontend
npm install
npm run build
```

3. 启动后端
```bash
python app.py
```

4. 打开浏览器
```bash
http://localhost:8000
```

## 配置项
首次进入页面后，在配置面板填写：
- `OpenAI API Key`
- `模型 ID`
- `OMDb API Key`（可选）
- `API 中转站`（可选）

## 说明
- 当前前端通过 `frontend/dist` 静态挂载
- 回答会尽量保持李安第一人称、口语化的表达方式
- 页面角落的免责声明仅用于交流学习，不代表导演本人立场

## 语料来源
项目会参考 `output/paragraphs.jsonl` 中的书籍语料来辅助口吻和思路对齐；如果需要重新生成，可查看 `process_mobi_book.py`。
