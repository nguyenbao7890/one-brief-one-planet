"""
llm_client.py
Lớp trung gian gọi LLM — hiện dùng Gemini (free tier) để test.
Đây là ĐIỂM DUY NHẤT trong codebase gọi tới LLM provider.
Sau này muốn đổi qua Claude API (khi có ngân sách), chỉ cần sửa file này,
không cần đụng vào prompt_rewriter.py hay bất kỳ chỗ nào khác.
"""

import os
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


def call_llm(prompt: str, model: str | None = None) -> str:
    """
    Gửi 1 prompt tới LLM, trả về text response thuần.
    """
    client = _get_client()
    model = model or os.environ.get("GEMINI_MODEL", "gemini-3-flash-preview")
    response = client.models.generate_content(
        model=model,
        contents=prompt,
    )
    if not response.text:
        raise RuntimeError("LLM trả về response rỗng.")
    return response.text.strip()
