import base64
import io
from pathlib import Path
from typing import Tuple

from PIL import Image as PILImage
from PIL import UnidentifiedImageError


PNG_MIME_TYPE = "image/png"


def image_path_to_png_data_url(image_path: str) -> Tuple[str, str]:
    """Decode an uploaded image and return PNG data URL plus bare base64."""
    try:
        with PILImage.open(image_path) as pil_img:
            if getattr(pil_img, "is_animated", False):
                pil_img.seek(0)

            has_alpha = pil_img.mode in {"RGBA", "LA"} or "transparency" in pil_img.info
            pil_img = pil_img.convert("RGBA" if has_alpha else "RGB")

            png_buffer = io.BytesIO()
            pil_img.save(png_buffer, format="PNG")
    except UnidentifiedImageError as exc:
        filename = Path(image_path).name
        raise ValueError(
            f"Unsupported or unreadable image file: {filename}. "
            "Please upload a valid PNG, JPEG, WebP, or GIF image."
        ) from exc

    png_base64 = base64.b64encode(png_buffer.getvalue()).decode("ascii")
    return f"data:{PNG_MIME_TYPE};base64,{png_base64}", png_base64


def create_agno_png_image(image_path: str):
    """Create an Agno image object with a PNG payload OpenAI-compatible APIs accept."""
    from agno.media import Image

    data_url, png_base64 = image_path_to_png_data_url(image_path)
    payloads = (
        {"url": data_url},
        {"content": data_url, "mime_type": PNG_MIME_TYPE},
        {"content": png_base64, "mime_type": PNG_MIME_TYPE},
    )

    last_error = None
    for payload in payloads:
        try:
            image = Image(**payload)
            if any(getattr(image, field, None) for field in ("url", "content")):
                return image
        except Exception as exc:
            last_error = exc

    if last_error:
        raise last_error
    raise ValueError("Could not create a valid Agno image payload.")