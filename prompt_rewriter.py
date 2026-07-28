"""
prompt_rewriter.py
Dùng cultural rules (từ rule_loader) + brief gốc để tạo ra 1 image prompt
đã "bản địa hóa" cho từng thị trường, thông qua llm_client.
"""

import argparse

from llm_client import call_llm
from rule_loader import load_market_rules


def build_localization_instruction(rules: dict) -> str:
    """Biến rule JSON (avoid/embrace) thành đoạn hướng dẫn dạng text cho LLM đọc."""
    lines = ["QUY TẮC VĂN HÓA CẦN TUÂN THỦ:\n", "NÊN TRÁNH:"]

    for items in rules["avoid"].values():
        for item in items:
            desc = item.get("item") or item.get("topic")
            lines.append(f"- {desc} (Lý do: {item['reason']})")

    lines.append("\nNÊN ÁP DỤNG:")
    for items in rules["embrace"].values():
        for item in items:
            desc = item.get("value") or item.get("color") or item.get("motif") or item.get("occasion")
            reason = item.get("reason") or item.get("note")
            lines.append(f"- {desc} (Lý do: {reason})")

    return "\n".join(lines)


def rewrite_brief_for_market(brief: str, market_id: str) -> str:
    """
    Nhận brief gốc (tiếng Việt/Anh tự do) + market_id,
    trả về 1 image prompt đã điều chỉnh theo văn hóa thị trường đó.
    """
    return call_llm(build_rewrite_prompt(brief, market_id))


def build_rewrite_prompt(brief: str, market_id: str) -> str:
    """Tạo prompt đầy đủ mà không gọi mạng, hữu ích để preview và debug."""
    rules = load_market_rules(market_id)
    instruction = build_localization_instruction(rules)
    return f"""Bạn là chuyên gia bản địa hóa creative quảng cáo.

Brief gốc: "{brief}"

Thị trường mục tiêu: {rules['market_name']}

{instruction}

Nhiệm vụ: viết lại brief trên thành 1 mô tả ảnh chi tiết (image prompt bằng tiếng Anh,
vì các model sinh ảnh hiểu tiếng Anh tốt hơn), tuân thủ đúng các quy tắc văn hóa ở trên.
Chỉ trả về mô tả ảnh, không giải thích thêm, không markdown."""


def main() -> None:
    parser = argparse.ArgumentParser(description="Localize a creative brief by market.")
    parser.add_argument("--brief", required=True, help="Brief gốc cần bản địa hóa")
    parser.add_argument("--market", required=True, help="Ví dụ: japan")
    parser.add_argument(
        "--preview", action="store_true", help="In prompt, không gọi Gemini"
    )
    args = parser.parse_args()

    prompt = build_rewrite_prompt(args.brief, args.market)
    print(prompt if args.preview else call_llm(prompt))


if __name__ == "__main__":
    main()
