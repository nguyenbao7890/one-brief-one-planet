"""HTTP adapter cho pipeline localization, không phụ thuộc framework bên ngoài."""

import argparse
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from prompt_rewriter import rewrite_brief_for_market
from rule_loader import RuleValidationError

MAX_BODY_BYTES = 1_000_000


def _json_bytes(payload: dict) -> bytes:
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


class LocalizationHandler(BaseHTTPRequestHandler):
    """Nhận request HTTP và chuyển tiếp vào domain function."""

    server_version = "OneBriefOnePlanet/0.1"

    def do_GET(self) -> None:
        if self.path != "/health":
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Endpoint không tồn tại."})
            return
        self._send_json(
            HTTPStatus.OK,
            {"status": "ok", "service": "one-brief-one-planet"},
        )

    def do_POST(self) -> None:
        if self.path != "/localize":
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Endpoint không tồn tại."})
            return

        try:
            payload = self._read_json_body()
            brief, market_id = self._validate_payload(payload)
            result = rewrite_brief_for_market(brief, market_id)
        except ValueError as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        except FileNotFoundError as exc:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": str(exc)})
            return
        except RuleValidationError:
            self._send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": "Cultural rule không hợp lệ trên server."},
            )
            return
        except Exception:
            self._send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": "Không thể tạo localization result."},
            )
            return

        self._send_json(HTTPStatus.OK, result)

    def _read_json_body(self) -> dict[str, Any]:
        content_length = self.headers.get("Content-Length")
        if content_length is None:
            raise ValueError("Request cần Content-Length.")
        try:
            length = int(content_length)
        except ValueError as exc:
            raise ValueError("Content-Length không hợp lệ.") from exc
        if length < 0 or length > MAX_BODY_BYTES:
            raise ValueError("Request body vượt quá giới hạn 1 MB.")

        raw_body = self.rfile.read(length)
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("Body phải là JSON UTF-8 hợp lệ.") from exc
        if not isinstance(payload, dict):
            raise ValueError("Body JSON phải là object.")
        return payload

    @staticmethod
    def _validate_payload(payload: dict[str, Any]) -> tuple[str, str]:
        brief = payload.get("brief")
        market_id = payload.get("market_id")
        if not isinstance(brief, str) or not brief.strip():
            raise ValueError("Field 'brief' phải là text không rỗng.")
        if len(brief) > 10_000:
            raise ValueError("Field 'brief' không được dài quá 10.000 ký tự.")
        if not isinstance(market_id, str) or not market_id.strip():
            raise ValueError("Field 'market_id' phải là text không rỗng.")
        return brief.strip(), market_id.strip()

    def _send_json(self, status: HTTPStatus, payload: dict) -> None:
        body = _json_bytes(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        """Giữ log gọn; production có thể thay bằng logging có request id."""
        return


class LocalizationServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True


def create_server(host: str = "127.0.0.1", port: int = 8000) -> LocalizationServer:
    return LocalizationServer((host, port), LocalizationHandler)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the localization HTTP API.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    server = create_server(args.host, args.port)
    print(f"Localization API đang chạy tại http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nĐang dừng server...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
