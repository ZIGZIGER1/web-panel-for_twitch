from __future__ import annotations

import threading
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse


@dataclass
class OverlayState:
    overlay_html: str = ""
    clean_overlay_html: str = ""
    chat_html: str = ""
    chat_config_json: str = "{}"
    overlay_png: bytes = b""
    clean_overlay_png: bytes = b""
    lock: threading.Lock = field(default_factory=threading.Lock)

    def update(
        self,
        *,
        overlay_html: str | None = None,
        clean_overlay_html: str | None = None,
        chat_html: str | None = None,
        chat_config_json: str | None = None,
        overlay_png: bytes | None = None,
        clean_overlay_png: bytes | None = None,
    ) -> None:
        with self.lock:
            if overlay_html is not None:
                self.overlay_html = overlay_html
            if clean_overlay_html is not None:
                self.clean_overlay_html = clean_overlay_html
            if chat_html is not None:
                self.chat_html = chat_html
            if chat_config_json is not None:
                self.chat_config_json = chat_config_json
            if overlay_png is not None:
                self.overlay_png = overlay_png
            if clean_overlay_png is not None:
                self.clean_overlay_png = clean_overlay_png

    def snapshot(self) -> tuple[str, str, str, str, bytes, bytes]:
        with self.lock:
            return (
                self.overlay_html,
                self.clean_overlay_html,
                self.chat_html,
                self.chat_config_json,
                self.overlay_png,
                self.clean_overlay_png,
            )


class OverlayHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True

    def __init__(self, server_address: tuple[str, int], app) -> None:
        super().__init__(server_address, OverlayRequestHandler)
        self.app = app


class OverlayRequestHandler(BaseHTTPRequestHandler):
    server: OverlayHTTPServer

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        query = parsed.query

        overlay_html, clean_overlay_html, chat_html, chat_config_json, overlay_png, clean_overlay_png = self.server.app.overlay_state.snapshot()

        if path in {"/", "/overlay"}:
            content = clean_overlay_html or overlay_html
            self._send_bytes(content.encode("utf-8"), "text/html; charset=utf-8")
            return

        if path == "/overlay-clean":
            content = clean_overlay_html or overlay_html
            self._send_bytes(content.encode("utf-8"), "text/html; charset=utf-8")
            return

        if path == "/overlay-styled":
            self._send_bytes(overlay_html.encode("utf-8"), "text/html; charset=utf-8")
            return

        if path == "/chat":
            if "config=1" in query:
                self._send_bytes(chat_config_json.encode("utf-8"), "application/json; charset=utf-8")
                return
            self._send_bytes(chat_html.encode("utf-8"), "text/html; charset=utf-8")
            return

        if path == "/frame.png":
            self._send_bytes(clean_overlay_png or overlay_png, "image/png")
            return

        if path == "/frame-clean.png":
            self._send_bytes(clean_overlay_png or overlay_png, "image/png")
            return

        if path == "/frame-styled.png":
            self._send_bytes(overlay_png, "image/png")
            return

        self.send_error(404)

    def _send_bytes(self, content: bytes, content_type: str) -> None:
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        try:
            self.wfile.write(content)
        except (ConnectionError, OSError):
            pass

    def log_message(self, format: str, *args) -> None:
        del format, args
