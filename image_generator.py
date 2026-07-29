"""
image_generator.py
Sinh ảnh từ prompt qua Pollinations.ai (miễn phí, không cần API key).
Chuyển từ Gemini sang đây vì free tier ảnh của Gemini hiện = 0 cho tài khoản
mới (xác nhận qua lỗi 429 "limit: 0" khi test thực tế trên cả 2 model).
"""

import argparse
from pathlib import Path
from urllib.parse import quote

import requests

BASE_URL = "https://image.pollinations.ai/prompt"
DEFAULT_MODEL = "flux"
DEFAULT_WIDTH = 1024
DEFAULT_HEIGHT = 1024
TIMEOUT_SECONDS = 60


class ImageGenerationError(Exception):
    """Raise khi Pollinations không trả về ảnh hợp lệ."""
    pass


def generate_image(
    prompt: str,
    output_path: str,
    model: str = DEFAULT_MODEL,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
) -> str:
    """
    Sinh 1 ảnh từ prompt qua Pollinations.ai, lưu vào output_path.
    Trả về output_path nếu thành công.
    """
    url = f"{BASE_URL}/{quote(prompt)}"
    params = {
        "model": model,
        "width": width,
        "height": height,
        "nologo": "true",  # tránh logo Pollinations chèn vào ảnh
    }

    response = requests.get(url, params=params, timeout=TIMEOUT_SECONDS)

    content_type = response.headers.get("Content-Type", "")
    if response.status_code != 200 or not content_type.startswith("image/"):
        raise ImageGenerationError(
            f"Pollinations không trả về ảnh hợp lệ "
            f"(status={response.status_code}, content-type={content_type!r}). "
            f"Nội dung: {response.text[:200]}"
        )

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(response.content)
    return str(out)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate an image from a prompt.")
    parser.add_argument("--prompt", required=True, help="Mô tả ảnh (image prompt)")
    parser.add_argument("--output", default="output.png", help="Đường dẫn file lưu ảnh")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    args = parser.parse_args()

    path = generate_image(args.prompt, args.output, model=args.model)
    print(f"Đã lưu ảnh tại: {path}")


if __name__ == "__main__":
    main()