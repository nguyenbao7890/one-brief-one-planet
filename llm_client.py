"""
llm_client.py
Lớp trung gian gọi LLM — hiện dùng Gemini (free tier) để test.
Đây là ĐIỂM DUY NHẤT trong codebase gọi tới LLM provider.
Sau này muốn đổi qua Claude API (khi có ngân sách), chỉ cần sửa file này,
không cần đụng vào prompt_rewriter.py hay bất kỳ chỗ nào khác.
"""

import os
import time
from dotenv import load_dotenv

load_dotenv()  # đọc file .env, lấy GEMINI_API_KEY

_client = None


def _get_client():
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "Không tìm thấy GEMINI_API_KEY. Kiểm tra: "
                "(1) file .env có nằm cùng thư mục với file .py đang chạy không, "
                "(2) nội dung đúng dạng GEMINI_API_KEY=xxx (không có dấu cách/ngoặc kép)."
            )
        from google import genai

        _client = genai.Client(api_key=api_key)
    return _client


def get_client():
    """
    Trả về client Gemini đã cấu hình sẵn (đọc key, tạo 1 lần, tái sử dụng).
    Dùng khi module khác (VD: image_generator) cần gọi Gemini cho việc
    không phải text-only (sinh ảnh...).
    """
    return _get_client()


def _parse_quota_error(exc) -> tuple[str | None, float | None]:
    """
    Trích quotaId (VD: '...PerDay...' hay '...PerMinute...') và retryDelay
    (giây) từ lỗi 429 của Gemini, để biết nên chờ-thử-lại hay bỏ cuộc hôm nay.
    """
    details = getattr(exc, "details", None) or {}
    error_details = details.get("error", {}).get("details", [])

    quota_id = None
    retry_seconds = None
    for item in error_details:
        item_type = item.get("@type", "")
        if item_type.endswith("QuotaFailure"):
            violations = item.get("violations", [])
            if violations:
                quota_id = violations[0].get("quotaId")
        elif item_type.endswith("RetryInfo"):
            raw = item.get("retryDelay", "")
            if raw.endswith("s"):
                try:
                    retry_seconds = float(raw[:-1])
                except ValueError:
                    pass
    return quota_id, retry_seconds


def call_llm(prompt: str, model: str | None = None, _attempt: int = 0) -> str:
    """
    Gửi 1 prompt tới LLM, trả về text response thuần.
    Tự chờ-và-thử-lại nếu bị giới hạn theo PHÚT (transient); báo lỗi rõ ràng
    ngay lập tức (không phí thời gian retry) nếu bị giới hạn theo NGÀY.
    """
    from google.genai import errors as genai_errors

    client = _get_client()
    model = model or os.environ.get("GEMINI_MODEL", "gemini-3-flash-preview")

    try:
        response = client.models.generate_content(model=model, contents=prompt)
    except genai_errors.ClientError as exc:
        if exc.code == 429:
            quota_id, retry_seconds = _parse_quota_error(exc)

            if quota_id and "PerDay" in quota_id:
                raise RuntimeError(
                    f"Đã hết quota MIỄN PHÍ trong ngày cho model '{model}'. "
                    "Quota reset vào nửa đêm giờ Thái Bình Dương (~13-14h chiều "
                    "giờ Việt Nam hôm sau). Thử lại vào ngày mai."
                ) from exc

            if _attempt < 2:
                time.sleep((retry_seconds or 5) + 1)
                return call_llm(prompt, model=model, _attempt=_attempt + 1)
        raise

    if not response.text:
        raise RuntimeError("LLM trả về response rỗng.")
    return response.text.strip()