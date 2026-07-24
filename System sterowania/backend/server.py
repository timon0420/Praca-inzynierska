from __future__ import annotations

import hmac
import json
import os
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

MAX_JPEG_SIZE = 200 * 1024
SESSION_PATTERN = re.compile(r"^[0-9A-HJKMNP-TV-Z]{4}-[0-9A-HJKMNP-TV-Z]{4}$")


class AnalysisHandler(BaseHTTPRequestHandler):
    registry: Any
    internal_token: str

    def do_GET(self) -> None:
        if self.path != "/healthz":
            self._json(404, {"error": "not_found"})
            return
        self.send_response(204)
        self.end_headers()

    def do_POST(self) -> None:
        if self.path != "/analyze":
            self._json(404, {"error": "not_found"})
            return
        supplied_token = self.headers.get("X-Internal-Token", "")
        if not self.internal_token or not hmac.compare_digest(
            supplied_token, self.internal_token
        ):
            self._json(401, {"error": "unauthorized"})
            return
        session_code = self.headers.get("X-Session-Code", "")
        if not SESSION_PATTERN.fullmatch(session_code):
            self._json(400, {"error": "invalid_session"})
            return
        if self.headers.get_content_type() != "image/jpeg":
            self._json(415, {"error": "jpeg_required"})
            return
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            content_length = 0
        if content_length < 4 or content_length > MAX_JPEG_SIZE:
            self._json(413, {"error": "invalid_image_size"})
            return
        jpeg = self.rfile.read(content_length)
        if not (
            jpeg.startswith(b"\xff\xd8")
            and jpeg.endswith(b"\xff\xd9")
            and len(jpeg) == content_length
        ):
            self._json(400, {"error": "invalid_jpeg"})
            return
        try:
            result = self.registry.analyze(session_code, jpeg)
        except ValueError:
            self._json(400, {"error": "invalid_jpeg"})
            return
        except Exception:
            self._json(500, {"error": "analysis_failed"})
            return
        self._json(200, result)

    def log_message(self, format: str, *args: object) -> None:
        print(f"{self.address_string()} - {format % args}")

    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    from backend.analyzer import AnalyzerRegistry

    port = int(os.environ.get("PORT", "8090"))
    token = os.environ.get("INTERNAL_SERVICE_TOKEN", "")
    if not token:
        raise RuntimeError("INTERNAL_SERVICE_TOKEN jest wymagany.")
    model_path = os.environ.get("HAND_LANDMARKER_MODEL", "hand_landmarker.task")
    registry = AnalyzerRegistry(model_path)
    AnalysisHandler.registry = registry
    AnalysisHandler.internal_token = token
    server = ThreadingHTTPServer(("0.0.0.0", port), AnalysisHandler)

    def cleanup_loop() -> None:
        while not threading.Event().wait(60):
            registry.cleanup()

    threading.Thread(target=cleanup_loop, daemon=True).start()
    try:
        print(f"Analysis worker działa na porcie {port}")
        server.serve_forever()
    finally:
        server.server_close()
        registry.close()


if __name__ == "__main__":
    main()
