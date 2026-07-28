"""
prompt_rewriter.py
Dùng cultural rules (từ rule_loader) + brief gốc để tạo ra 1 image prompt
đã "bản địa hóa" cho từng thị trường, thông qua llm_client.
"""

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
    rules = load_market_rules(market_id)
    instruction = build_localization_instruction(rules)

    prompt = f"""Bạn là chuyên gia bản địa hóa creative quảng cáo.

Brief gốc: "{brief}"

Thị trường mục tiêu: {rules['market_name']}

{instruction}

Nhiệm vụ: viết lại brief trên thành 1 mô tả ảnh chi tiết (image prompt bằng tiếng Anh,
vì các model sinh ảnh hiểu tiếng Anh tốt hơn), tuân thủ đúng các quy tắc văn hóa ở trên.
Chỉ trả về mô tả ảnh, không giải thích thêm, không markdown."""

    return call_llm(prompt)


if __name__ == "__main__":
    brief = "Chai trà thảo mộc mát lạnh, phong cách hiện đại, năng động"

    for market in ["japan", "middle_east_gulf"]:
        result = rewrite_brief_for_market(brief, market)
        print(f"\n=== {market} ===")
        print(result)
