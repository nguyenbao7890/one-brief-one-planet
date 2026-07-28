"""
prompt_rewriter.py
Dùng cultural rules (từ rule_loader) + brief gốc để tạo ra 1 image prompt
đã "bản địa hóa" cho từng thị trường, thông qua llm_client.
"""

import argparse
import json

from llm_client import call_llm
from rule_loader import load_market_rules


def build_localization_instruction(rules: dict) -> str:
    """Biến rule JSON (avoid/embrace) thành đoạn hướng dẫn dạng text cho LLM đọc."""
    lines = ["QUY TẮC VĂN HÓA CẦN TUÂN THỦ:\n", "NÊN TRÁNH:"]

    for rule in _collect_rules(rules, "avoid"):
        lines.append(f"- {rule['description']} (Lý do: {rule['reason']})")

    lines.append("\nNÊN ÁP DỤNG:")
    for rule in _collect_rules(rules, "embrace"):
        lines.append(f"- {rule['description']} (Lý do: {rule['reason']})")

    return "\n".join(lines)


def _collect_rules(rules: dict, section: str) -> list[dict]:
    """Chuẩn hóa các item khác nhau trong JSON thành format dùng bởi output."""
    collected = []
    for group, items in rules[section].items():
        for item in items:
            description = (
                item.get("item")
                or item.get("topic")
                or item.get("value")
                or item.get("color")
                or item.get("motif")
                or item.get("occasion")
            )
            collected.append(
                {
                    "group": group,
                    "description": description,
                    "reason": item.get("reason") or item.get("note"),
                    "source": item.get("source"),
                }
            )
    return collected


def rewrite_brief_for_market(brief: str, market_id: str) -> dict:
    """
    Nhận brief gốc (tiếng Việt/Anh tự do) + market_id,
    trả về kết quả bản địa hóa có cấu trúc, sẵn sàng serialize thành JSON.
    """
    rules = load_market_rules(market_id)
    localized_prompt = call_llm(_build_rewrite_prompt(brief, rules))
    return build_localization_result(brief, rules, localized_prompt)


def build_localization_result(
    brief: str, rules: dict, localized_prompt: str
) -> dict:
    """Đóng gói output để CLI, n8n hoặc frontend không phải parse text."""
    return {
        "brief": brief,
        "market_id": rules["market_id"],
        "market_name": rules["market_name"],
        "rule_schema_version": rules["schema_version"],
        "rule_last_reviewed": rules["last_reviewed"],
        "rule_review_status": rules["review_status"],
        "localized_prompt": localized_prompt,
        "applied_rules": _collect_rules(rules, "embrace"),
        "avoid_rules": _collect_rules(rules, "avoid"),
        "sources": rules["sources"],
    }


def build_rewrite_prompt(brief: str, market_id: str) -> str:
    """Tạo prompt đầy đủ mà không gọi mạng, hữu ích để preview và debug."""
    return _build_rewrite_prompt(brief, load_market_rules(market_id))


def _build_rewrite_prompt(brief: str, rules: dict) -> str:
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

    if args.preview:
        print(build_rewrite_prompt(args.brief, args.market))
        return

    result = rewrite_brief_for_market(args.brief, args.market)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
