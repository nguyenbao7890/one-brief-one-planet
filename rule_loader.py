"""
rule_loader.py
Đọc và validate file cultural rule (JSON) cho từng thị trường.
Dùng làm nền cho pipeline: n8n sẽ gọi module này (qua HTTP endpoint nhỏ
hoặc subprocess) để lấy rule trước khi rewrite prompt.
"""

import json
from pathlib import Path

RULES_DIR = Path(__file__).parent / "cultural_rules"

REQUIRED_TOP_LEVEL_KEYS = ["market_id", "market_name", "avoid", "embrace", "sources"]


class RuleValidationError(Exception):
    """Raise khi file rule thiếu field bắt buộc hoặc sai định dạng."""
    pass


def load_market_rules(market_id: str) -> dict:
    """
    Đọc file cultural_rules/{market_id}.json, validate, và trả về dict.
    Raise FileNotFoundError nếu chưa có rule cho thị trường này.
    Raise RuleValidationError nếu file thiếu field bắt buộc.
    """
    if not market_id or Path(market_id).name != market_id:
        raise ValueError("market_id chỉ được chứa tên file đơn giản, ví dụ: japan")

    file_path = RULES_DIR / f"{market_id}.json"

    if not file_path.exists():
        raise FileNotFoundError(
            f"Chưa có rule cho thị trường '{market_id}'. "
            f"Kỳ vọng file tại: {file_path}"
        )

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        raise RuleValidationError(
            f"Rule '{market_id}' không phải JSON hợp lệ: {exc.msg}"
        ) from exc

    _validate(data, market_id)
    return data


def _validate(data: dict, market_id: str) -> None:
    if not isinstance(data, dict):
        raise RuleValidationError(f"Rule '{market_id}' phải là một JSON object.")

    missing = [key for key in REQUIRED_TOP_LEVEL_KEYS if key not in data]
    if missing:
        raise RuleValidationError(
            f"Rule '{market_id}' thiếu field bắt buộc: {missing}"
        )

    if data["market_id"] != market_id:
        raise RuleValidationError(
            f"Rule '{market_id}' có market_id không khớp: {data['market_id']!r}"
        )

    if not isinstance(data["market_name"], str) or not data["market_name"].strip():
        raise RuleValidationError(f"Rule '{market_id}' cần market_name dạng text.")

    for section in ("avoid", "embrace"):
        if not isinstance(data[section], dict):
            raise RuleValidationError(f"Rule '{market_id}' cần {section} là object.")
        if not all(isinstance(items, list) for items in data[section].values()):
            raise RuleValidationError(
                f"Rule '{market_id}' có nhóm trong {section} không phải list."
            )

    if not isinstance(data["sources"], list) or not all(
        isinstance(source, str) and source.strip() for source in data["sources"]
    ):
        raise RuleValidationError(
            f"Rule '{market_id}' cần sources là list các chuỗi không rỗng."
        )
    if not data["sources"]:
        raise RuleValidationError(
            f"Rule '{market_id}' không có nguồn (sources) — không được để trống."
        )


def list_available_markets() -> list[str]:
    """Liệt kê tất cả market_id đang có file rule trong cultural_rules/."""
    return sorted(p.stem for p in RULES_DIR.glob("*.json"))


if __name__ == "__main__":
    print("Các thị trường đang có rule:", list_available_markets())

    for market in list_available_markets():
        rules = load_market_rules(market)
        avoid_count = sum(len(v) for v in rules["avoid"].values())
        embrace_count = sum(len(v) for v in rules["embrace"].values())
        print(
            f"\n[{rules['market_name']}] "
            f"{avoid_count} điều nên tránh, {embrace_count} điều nên áp dụng, "
            f"{len(rules['sources'])} nguồn tham khảo"
        )
