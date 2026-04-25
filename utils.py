from __future__ import annotations

import os
import re
from pathlib import Path
from urllib.parse import urlparse


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def parse_int(value: str, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, parsed))


def normalize_url(raw_url: str) -> str:
    url = raw_url.strip()
    if not url:
        raise ValueError("Сначала вставь ссылку на чат.")
    if not urlparse(url).scheme:
        url = f"https://{url}"
    return url


def extract_twitch_channel(url: str) -> str | None:
    raw = url.strip()
    if not raw:
        return None

    candidate = raw.lstrip("@")
    if re.fullmatch(r"[A-Za-z0-9_]{3,25}", candidate):
        return candidate.lower()

    parsed = urlparse(raw if urlparse(raw).scheme else f"https://{raw}")
    host = parsed.netloc.lower()
    if "twitch.tv" not in host:
        return None

    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) >= 3 and parts[0] == "popout" and parts[2] == "chat":
        return parts[1]
    if len(parts) >= 3 and parts[0] == "embed" and parts[2] == "chat":
        return parts[1]
    if len(parts) >= 2 and parts[1] == "chat":
        return parts[0]
    if len(parts) >= 1:
        return parts[0]
    return None


def normalize_tune2live_url(raw_url: str) -> str:
    raw = str(raw_url or "").strip().strip('"')
    if not raw:
        return ""

    parsed = urlparse(raw if urlparse(raw).scheme else f"https://{raw}")
    host = parsed.netloc.lower()
    if ":" in host:
        host = host.split(":", 1)[0]

    if host == "www.tune2live.com":
        host = "tune2live.com"

    if host != "tune2live.com":
        return ""

    path = parsed.path or "/"
    query = f"?{parsed.query}" if parsed.query else ""
    return f"https://{host}{path}{query}"


def default_image_path(base_dir: Path, filename: str) -> str:
    path = base_dir / filename
    return str(path) if path.exists() else ""


def user_data_dir(app_name: str) -> Path:
    root = os.environ.get("LOCALAPPDATA")
    base = Path(root) if root else (Path.home() / "AppData" / "Local")
    target = base / app_name
    target.mkdir(parents=True, exist_ok=True)
    return target


def portable_media_path(base_dir: Path, value: str) -> str:
    text = str(value or "").strip().strip('"')
    if not text:
        return ""

    path = Path(text)
    if not path.is_absolute():
        return Path(text).as_posix()

    try:
        resolved = path.resolve()
    except OSError:
        resolved = path

    try:
        return resolved.relative_to(base_dir.resolve()).as_posix()
    except ValueError:
        return str(resolved)


def resolve_media_path(base_dir: Path, value: str) -> str:
    text = str(value or "").strip().strip('"')
    if not text:
        return ""

    path = Path(text)
    if not path.is_absolute():
        path = base_dir / path

    try:
        return str(path.resolve())
    except OSError:
        return str(path)
