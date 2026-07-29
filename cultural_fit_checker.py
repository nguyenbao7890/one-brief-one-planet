"""
cultural_fit_checker.py
Chấm điểm "cultural fit" cho 1 ảnh đã sinh ra, dựa trên cultural rules của
thị trường mục tiêu. Dùng model vision của Gemini — CÙNG free tier với
model text (khác với model sinh ảnh, vốn có quota riêng đã bị khóa).
"""

import argparse
import json
from pathlib import Path

from google.genai import types

from llm_client import get_client
from prompt_rewriter import build_localization_instruction
from rule_loader import load_market_rules

VISION_MODEL = "gemini-3-flash-preview"  # cùng model dùng ở prompt_rewriter

MIME_TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}


class CulturalFitCheckError(Exception):
    """Raise khi không chấm điểm được (lỗi model, response sai format...)."""
    pass


def check_cultural_fit(image_path: str, market_id: str) -> dict:
    """
    Gửi ảnh + rule văn hóa cho Gemini, nhờ chấm điểm mức độ phù hợp.
    Trả về dict: {score, verdict, issues, reasoning}.
    """
    rules = load_market_rules(market_id)
    instruction = build_localization_instruction(rules)  # tái dùng từ prompt_rewriter

    image_bytes = Path(image_path).read_bytes()
    mime_type = MIME_TYPES.get(Path(image_path).suffix.lower(), "image/png")

    prompt = f"""Bạn là chuyên gia kiểm duyệt creative quảng cáo theo văn hóa.

Thị trường mục tiêu: {rules['market_name']}

{instruction}

Nhiệm vụ: xem ảnh đính kèm, đánh giá xem nó có phù hợp văn hóa thị trường trên
không — kể cả những liên tưởng ngoài ý muốn (VD: chai lọ trông giống rượu dù
không có chữ nào nhắc tới rượu).

Trả lời DUY NHẤT bằng JSON theo format sau, không markdown, không giải thích thêm:
{{
  "score": <số nguyên 0-10, 10 là hoàn toàn phù hợp>,
  "verdict": "<pass hoặc fail; fail nếu score < 6 hoặc có vi phạm nghiêm trọng>",
  "issues": ["<từng vấn đề cụ thể nhìn thấy, để mảng rỗng nếu không có>"],
  "reasoning": "<giải thích ngắn gọn>"
}}"""

    client = get_client()
    response = client.models.generate_content(
        model=VISION_MODEL,
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            prompt,
        ],
    )

    return _parse_response(response.text, market_id)


def _parse_response(text: str, market_id: str) -> dict:
    """Gemini đôi khi bọc JSON trong ```json ... ``` — bóc ra trước khi parse."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
    cleaned = cleaned.strip()

    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise CulturalFitCheckError(
            f"Không parse được response cho market '{market_id}': {text[:300]}"
        ) from exc

    required = {"score", "verdict", "issues", "reasoning"}
    missing = required - result.keys()
    if missing:
        raise CulturalFitCheckError(
            f"Response cho market '{market_id}' thiếu field: {missing}"
        )

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Check cultural fit of a generated image.")
    parser.add_argument("--image", required=True, help="Đường dẫn ảnh cần chấm")
    parser.add_argument("--market", required=True, help="VD: japan")
    args = parser.parse_args()

    result = check_cultural_fit(args.image, args.market)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()