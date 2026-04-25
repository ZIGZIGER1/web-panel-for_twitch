from __future__ import annotations

import json
import re

from constants import APP_TITLE, OVERLAY_REFRESH_MS


HEX_COLOR_RE = re.compile(r"^#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})$")


def safe_hex_color(value: object, fallback: str) -> str:
    candidate = str(value or "").strip()
    if HEX_COLOR_RE.fullmatch(candidate):
        return candidate
    return fallback


def safe_font_stack(value: object, fallback: str) -> str:
    cleaned = " ".join(str(value or "").strip().split())
    return cleaned[:120] if cleaned else fallback


def clamp_float(value: object, minimum: float, maximum: float, fallback: float) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return fallback
    return max(minimum, min(maximum, numeric))


def rgba_from_hex(value: object, alpha: object, fallback: str) -> str:
    color = safe_hex_color(value, fallback).lstrip("#")
    if len(color) == 3:
        color = "".join(ch * 2 for ch in color)
    red = int(color[0:2], 16)
    green = int(color[2:4], 16)
    blue = int(color[4:6], 16)
    opacity = clamp_float(alpha, 0.0, 100.0, 100.0) / 100.0
    return f"rgba({red}, {green}, {blue}, {opacity:.3f})"


def build_chat_config(
    *,
    side_name: str,
    width_percent: float,
    twitch_channel: str,
    irc_username: str,
    irc_token: str,
    compact_mode: bool = False,
    reveal_only: bool = True,
    font_family: str = "",
    title_font_family: str = "",
    accent_color: str = "#74E7FF",
    accent_color_2: str = "#FF66C7",
    accent_color_3: str = "#FFC970",
    text_color: str = "#F5FBFF",
    muted_color: str = "#B4C7DD",
    panel_color: str = "#132033",
    panel_opacity: float = 62.0,
    panel_color_secondary: str = "#1C2A42",
    panel_secondary_opacity: float = 92.0,
    message_color: str = "#18263A",
    message_opacity: float = 88.0,
    message_size_px: float = 20.0,
    shell_radius_px: float = 34.0,
    bubble_radius_px: float = 24.0,
) -> dict[str, object]:
    side_key = "left" if side_name == "Слева" else "right"

    username = irc_username.strip().lower()
    token = irc_token.strip()
    if token and not token.lower().startswith("oauth:"):
        token = f"oauth:{token}"

    auth_mode = "token" if username and token else "anonymous"
    subtitle = f"Twitch • {twitch_channel}" if twitch_channel else "Ожидание Twitch-канала"
    accent = safe_hex_color(accent_color, "#74E7FF")
    accent2 = safe_hex_color(accent_color_2, "#FF66C7")
    accent3 = safe_hex_color(accent_color_3, "#FFC970")
    text = safe_hex_color(text_color, "#F5FBFF")
    muted = safe_hex_color(muted_color, "#B4C7DD")
    panel = rgba_from_hex(panel_color, panel_opacity, "#132033")
    panel2 = rgba_from_hex(panel_color_secondary, panel_secondary_opacity, "#1C2A42")
    message_fill = rgba_from_hex(message_color, message_opacity, "#18263A")
    font_stack = safe_font_stack(font_family, '"Manrope", "Segoe UI", sans-serif')
    title_font_stack = safe_font_stack(title_font_family, '"Unbounded", "Manrope", sans-serif')
    message_size = int(round(clamp_float(message_size_px, 14.0, 32.0, 20.0)))
    shell_radius = int(round(clamp_float(shell_radius_px, 20.0, 44.0, 34.0)))
    bubble_radius = int(round(clamp_float(bubble_radius_px, 16.0, 36.0, 24.0)))

    return {
        "style_key": "custom",
        "style_name": "Ручной",
        "side_name": side_name,
        "side_key": side_key,
        "panel_width_percent": round(width_percent, 1),
        "font_family": font_stack,
        "title_font_family": title_font_stack,
        "accent": accent,
        "accent2": accent2,
        "accent3": accent3,
        "panel": panel,
        "panel2": panel2,
        "panel3": message_fill,
        "message_fill": message_fill,
        "text": text,
        "muted": muted,
        "shadow": rgba_from_hex(accent2, 22.0, accent2),
        "line": rgba_from_hex(accent, 24.0, accent),
        "message_size": f"{message_size}px",
        "shell_radius": f"{shell_radius}px",
        "bubble_radius": f"{bubble_radius}px",
        "title": "ЧАТ TWITCH // ЭФИР",
        "subtitle": subtitle,
        "twitch_channel": twitch_channel,
        "irc_username": username,
        "irc_token": token,
        "auth_mode": auth_mode,
        "compact_mode": bool(compact_mode),
        "reveal_only": bool(reveal_only),
        "idle_fade_ms": 340,
        "message_life_ms": 11800,
        "max_messages": 5,
        "demo_mode": False,
    }


def build_chat_overlay_html(config: dict[str, object]) -> str:
    initial_json = json.dumps(config, ensure_ascii=False).replace("<", "\\u003c")
    part1 = """<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>__APP_TITLE__ chat overlay</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=Unbounded:wght@600;700&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --panel-width: 31;
      --body-font: "Manrope", "Segoe UI", sans-serif;
      --title-font: "Unbounded", "Manrope", sans-serif;
      --accent: #8ef7d4;
      --accent-2: #8ea8ff;
      --accent-3: #e28eff;
      --panel: rgba(7, 16, 26, 0.58);
      --panel-2: rgba(14, 29, 41, 0.92);
      --panel-3: rgba(19, 36, 48, 0.82);
      --message-fill: rgba(19, 36, 48, 0.82);
      --text: #f5fbff;
      --muted: #b4c7dd;
      --line: rgba(142, 247, 212, 0.26);
      --shadow: rgba(88, 218, 190, 0.22);
      --message-size: 20px;
      --shell-radius: 34px;
      --bubble-radius: 24px;
      --message-life: 11800ms;
    }

    * {
      box-sizing: border-box;
    }

    html, body {
      margin: 0;
      width: 100%;
      height: 100%;
      overflow: hidden;
      background: transparent;
      font-family: var(--body-font);
      color: var(--text);
    }

    body {
      pointer-events: none;
      text-rendering: optimizeLegibility;
    }

    .stage {
      position: fixed;
      inset: 0;
      overflow: hidden;
    }

    .chat-shell {
      position: absolute;
      top: 20px;
      width: min(max(380px, calc(var(--panel-width) * 1vw)), 560px);
      max-height: calc(100vh - 40px);
      border-radius: var(--shell-radius);
      overflow: hidden;
      isolation: isolate;
      display: flex;
      flex-direction: column;
      background:
        linear-gradient(180deg, var(--panel), var(--panel-2)),
        linear-gradient(140deg, rgba(255,255,255,0.04), transparent 24%);
      border: 1px solid rgba(255,255,255,0.08);
      backdrop-filter: blur(18px) saturate(1.08);
      box-shadow:
        0 28px 70px rgba(0,0,0,0.46),
        0 0 42px var(--shadow);
      transition:
        opacity 220ms ease,
        transform 260ms cubic-bezier(0.22, 1, 0.36, 1),
        filter 220ms ease,
        box-shadow 220ms ease;
    }

    .chat-shell.right { right: 20px; }
    .chat-shell.left { left: 20px; }
    .chat-shell.reveal-only {
      top: 14px;
      max-height: calc(100vh - 28px);
      overflow: visible;
      border: 0;
      border-radius: 0;
      background: transparent;
      backdrop-filter: none;
      box-shadow: none;
    }
    .chat-shell.compact {
      top: 14px;
      border-radius: var(--shell-radius);
      background:
        linear-gradient(180deg, color-mix(in srgb, var(--panel) 86%, transparent), color-mix(in srgb, var(--panel-2) 94%, transparent)),
        linear-gradient(140deg, rgba(255,255,255,0.03), transparent 24%);
      box-shadow:
        0 24px 62px rgba(0,0,0,0.34),
        0 0 32px var(--shadow);
    }
    .chat-shell.compact .chrome,
    .chat-shell.compact .footer {
      display: none;
    }
    .chat-shell.compact .message-zone {
      padding-top: 14px;
      padding-bottom: 16px;
      min-height: 100%;
    }
    .chat-shell.compact .message {
      border-radius: calc(var(--bubble-radius) - 2px);
    }

    .chat-shell.idle-hidden {
      opacity: 0;
      transform: translateY(18px) scale(0.982);
      filter: blur(10px);
      box-shadow: none;
      pointer-events: none;
    }

    .chat-shell.reveal-only .topline,
    .chat-shell.reveal-only .chrome,
    .chat-shell.reveal-only .footer,
    .chat-shell.reveal-only .placeholder,
    .chat-shell.reveal-only::before,
    .chat-shell.reveal-only::after,
    .chat-shell.reveal-only .message-zone::before {
      display: none;
    }

    .chat-shell.idle-hidden::before,
    .chat-shell.idle-hidden::after,
    .chat-shell.idle-hidden .topline,
    .chat-shell.idle-hidden .chrome,
    .chat-shell.idle-hidden .footer {
      opacity: 0;
    }

    .chat-shell.idle-hidden .message-zone {
      min-height: 0;
      max-height: none;
      padding-top: 0;
      padding-bottom: 0;
      background: transparent;
    }

    .chat-shell.reveal-only .message-zone {
      padding: 0;
      min-height: 0;
      max-height: calc(100vh - 28px);
      overflow: visible;
      background: transparent;
    }

    .chat-shell.reveal-only .messages {
      gap: 14px;
      padding-right: 0;
    }

    .chat-shell.reveal-only .message {
      border-radius: calc(var(--bubble-radius) + 4px);
      backdrop-filter: blur(16px) saturate(1.04);
      box-shadow:
        0 18px 34px rgba(0,0,0,0.24),
        0 0 26px color-mix(in srgb, var(--user-color, var(--accent)) 10%, transparent);
    }

    .chat-shell::before,
    .chat-shell::after {
      content: "";
      position: absolute;
      inset: 0;
      pointer-events: none;
    }

    .chat-shell::before {
      background:
        radial-gradient(circle at 8% 12%, color-mix(in srgb, var(--accent) 28%, transparent), transparent 28%),
        radial-gradient(circle at 88% 0%, color-mix(in srgb, var(--accent-2) 25%, transparent), transparent 26%),
        radial-gradient(circle at 76% 100%, color-mix(in srgb, var(--accent-3) 18%, transparent), transparent 24%);
      filter: blur(26px);
      opacity: 0.95;
    }

    .chat-shell::after {
      inset: 1px;
      border-radius: calc(var(--shell-radius) - 1px);
      border: 1px solid rgba(255,255,255,0.05);
      mask: linear-gradient(180deg, rgba(255,255,255,0.9), transparent 26%);
    }

    .topline {
      height: 4px;
      background: linear-gradient(90deg, var(--accent), var(--accent-2), var(--accent-3));
      background-size: 180% 100%;
      animation: sweep 5.8s linear infinite;
      position: relative;
      z-index: 3;
    }

    .chrome {
      position: relative;
      z-index: 3;
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 16px;
      padding: 18px 20px 14px;
      background:
        linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.01)),
        linear-gradient(180deg, rgba(255,255,255,0.02), transparent);
      border-bottom: 1px solid rgba(255,255,255,0.06);
    }

    .status {
      display: flex;
      align-items: flex-start;
      gap: 12px;
      min-width: 0;
      flex: 1 1 auto;
    }

    .orb-wrap {
      width: 42px;
      height: 42px;
      border-radius: 16px;
      background: linear-gradient(135deg, rgba(255,255,255,0.08), rgba(255,255,255,0.03));
      border: 1px solid rgba(255,255,255,0.08);
      display: grid;
      place-items: center;
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.05);
      flex: 0 0 auto;
    }

    .orb {
      width: 14px;
      height: 14px;
      border-radius: 999px;
      background: linear-gradient(180deg, var(--accent-2), var(--accent));
      box-shadow:
        0 0 18px color-mix(in srgb, var(--accent) 70%, transparent),
        0 0 28px color-mix(in srgb, var(--accent-2) 30%, transparent);
      animation: pulseDot 1.8s ease-in-out infinite;
    }

    .titles {
      min-width: 0;
      flex: 1 1 auto;
    }

    .eyebrow {
      font-family: var(--title-font);
      font-size: 11px;
      font-weight: 800;
      letter-spacing: 0.16em;
      text-transform: uppercase;
      color: color-mix(in srgb, var(--accent) 80%, white 20%);
      margin-bottom: 5px;
    }

    .title {
      font-family: var(--title-font);
      font-size: 15px;
      font-weight: 900;
      letter-spacing: 0.05em;
      text-transform: uppercase;
    }

    .subtitle {
      margin-top: 4px;
      font-size: 12px;
      color: var(--muted);
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
    }

    .subtitle .mode {
      padding: 4px 8px;
      border-radius: 999px;
      background: rgba(255,255,255,0.08);
      border: 1px solid rgba(255,255,255,0.06);
      font-size: 10px;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }

    .meta-panel {
      flex: 0 0 auto;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .badge {
      padding: 10px 14px;
      border-radius: 999px;
      font-size: 11px;
      font-weight: 900;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: #08111a;
      background: linear-gradient(120deg, var(--accent), var(--accent-2));
      box-shadow: 0 0 22px color-mix(in srgb, var(--accent) 38%, transparent);
    }

    .badge.retry,
    .badge.idle {
      color: var(--text);
      background: rgba(255,255,255,0.08);
      box-shadow: none;
    }

    .signal {
      min-width: 72px;
      padding: 10px 12px;
      border-radius: 18px;
      background: rgba(255,255,255,0.05);
      border: 1px solid rgba(255,255,255,0.06);
      display: flex;
      align-items: flex-end;
      justify-content: center;
      gap: 4px;
      height: 38px;
    }

    .signal span {
      width: 4px;
      border-radius: 999px;
      background: linear-gradient(180deg, var(--accent-2), var(--accent));
      animation: signal 1.2s ease-in-out infinite;
      transform-origin: bottom center;
    }

    .signal span:nth-child(1) { height: 10px; animation-delay: 0.0s; }
    .signal span:nth-child(2) { height: 18px; animation-delay: 0.1s; }
    .signal span:nth-child(3) { height: 13px; animation-delay: 0.2s; }
    .signal span:nth-child(4) { height: 21px; animation-delay: 0.3s; }
    .signal span:nth-child(5) { height: 12px; animation-delay: 0.4s; }
"""
    part2 = """
    .message-zone {
      position: relative;
      z-index: 2;
      padding: 14px 14px 10px;
      overflow: hidden;
      min-height: 220px;
      max-height: calc(100vh - 156px);
      background:
        linear-gradient(180deg, rgba(255,255,255,0.015), transparent 28%),
        linear-gradient(0deg, rgba(0,0,0,0.12), transparent 18%);
    }

    .message-zone::before {
      content: "";
      position: absolute;
      inset: 0;
      pointer-events: none;
      background:
        linear-gradient(180deg, rgba(255,255,255,0.06), transparent 18%),
        repeating-linear-gradient(
          180deg,
          rgba(255,255,255,0.014),
          rgba(255,255,255,0.014) 1px,
          transparent 1px,
          transparent 3px
        );
      opacity: 0.35;
      mix-blend-mode: screen;
    }

    .messages {
      position: relative;
      z-index: 2;
      display: flex;
      flex-direction: column;
      gap: 12px;
      padding-right: 2px;
    }

    .message {
      position: relative;
      display: grid;
      grid-template-columns: 54px minmax(0, 1fr);
      gap: 12px;
      padding: 14px;
      border-radius: var(--bubble-radius);
      background:
        linear-gradient(180deg, rgba(255,255,255,0.08), rgba(255,255,255,0.035)),
        linear-gradient(135deg, color-mix(in srgb, var(--message-fill) 88%, transparent), transparent 52%),
        linear-gradient(90deg, color-mix(in srgb, var(--accent) 10%, transparent), transparent 34%);
      border: 1px solid rgba(255,255,255,0.07);
      box-shadow:
        0 14px 30px rgba(0,0,0,0.24),
        inset 0 1px 0 rgba(255,255,255,0.06);
      overflow: hidden;
      opacity: 0;
      transform: translateY(22px) scale(0.985);
      filter: blur(10px);
      animation:
        messageIn 520ms cubic-bezier(0.22, 1, 0.36, 1) forwards,
        messageOut 720ms ease forwards;
      animation-delay:
        0ms,
        calc(var(--message-life) - 720ms);
    }

    .message::before {
      content: "";
      position: absolute;
      inset: 0;
      background:
        linear-gradient(90deg, color-mix(in srgb, var(--user-color, var(--accent)) 28%, transparent), transparent 26%);
      opacity: 0.9;
      pointer-events: none;
    }

    .message.highlight {
      border-color: color-mix(in srgb, var(--accent-2) 30%, rgba(255,255,255,0.08));
      box-shadow:
        0 16px 34px rgba(0,0,0,0.28),
        0 0 30px color-mix(in srgb, var(--accent-2) 18%, transparent);
    }

    .message.removing {
      animation: messageOutNow 420ms ease forwards !important;
    }

    .avatar-wrap {
      position: relative;
      width: 54px;
      height: 54px;
      flex: 0 0 auto;
    }

    .avatar-ring {
      position: absolute;
      inset: -2px;
      border-radius: 18px;
      background: linear-gradient(135deg, var(--user-color, var(--accent)), var(--accent-2));
      opacity: 0.35;
      filter: blur(10px);
    }

    .avatar {
      position: relative;
      width: 54px;
      height: 54px;
      border-radius: 18px;
      display: grid;
      place-items: center;
      font-size: 15px;
      font-weight: 900;
      color: white;
      background: linear-gradient(135deg, var(--user-color, var(--accent)), var(--accent-2));
      border: 1px solid rgba(255,255,255,0.08);
      box-shadow: 0 10px 22px rgba(0,0,0,0.22);
      overflow: hidden;
    }

    .content {
      min-width: 0;
      position: relative;
      z-index: 1;
    }

    .meta {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 8px;
      margin-bottom: 8px;
    }

    .identity {
      min-width: 0;
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
    }

    .name {
      font-family: var(--title-font);
      font-size: 15px;
      font-weight: 900;
      line-height: 1.1;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      color: var(--user-color, var(--text));
    }

    .chips {
      display: flex;
      align-items: center;
      gap: 6px;
      flex-wrap: wrap;
    }

    .chip {
      padding: 4px 8px;
      border-radius: 999px;
      font-size: 10px;
      font-weight: 800;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      background: rgba(255,255,255,0.08);
      border: 1px solid rgba(255,255,255,0.06);
      color: var(--text);
    }

    .chip.mod {
      background: color-mix(in srgb, var(--accent) 20%, rgba(255,255,255,0.04));
    }

    .chip.caster,
    .chip.bits {
      background: color-mix(in srgb, var(--accent-2) 22%, rgba(255,255,255,0.04));
    }

    .chip.reply {
      background: color-mix(in srgb, var(--accent-3) 16%, rgba(255,255,255,0.04));
      color: var(--muted);
      max-width: 100%;
    }

    .chip.reply span {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      display: inline-block;
      max-width: 100%;
    }

    .time {
      flex: 0 0 auto;
      font-size: 11px;
      color: var(--muted);
      padding-top: 2px;
    }

    .text {
      font-size: var(--message-size);
      line-height: 1.38;
      font-weight: 600;
      color: var(--text);
      word-break: break-word;
      text-shadow: 0 1px 1px rgba(0,0,0,0.20);
      display: flex;
      align-items: center;
      flex-wrap: wrap;
      gap: 6px;
    }

    .text-piece {
      white-space: pre-wrap;
    }

    .emote {
      height: 34px;
      width: auto;
      vertical-align: middle;
      filter: drop-shadow(0 2px 8px rgba(0,0,0,0.28));
    }

    .placeholder {
      position: relative;
      z-index: 2;
      margin: 14px;
      padding: 20px;
      border-radius: calc(var(--bubble-radius) + 2px);
      background:
        linear-gradient(180deg, rgba(255,255,255,0.05), rgba(255,255,255,0.03)),
        linear-gradient(135deg, color-mix(in srgb, var(--accent) 8%, transparent), transparent 40%);
      border: 1px solid rgba(255,255,255,0.06);
      color: var(--muted);
      line-height: 1.55;
      font-size: 14px;
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.05);
    }

    .placeholder.hidden {
      display: none;
    }

    .footer {
      position: relative;
      z-index: 3;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      padding: 0 16px 16px;
      font-size: 11px;
      color: rgba(255,255,255,0.54);
    }

    .footer strong {
      color: var(--text);
    }

    .chat-shell[data-style="aurora"] .message {
      border-radius: 30px;
      background:
        linear-gradient(180deg, rgba(255,255,255,0.12), rgba(255,255,255,0.04)),
        linear-gradient(135deg, color-mix(in srgb, var(--accent) 18%, transparent), color-mix(in srgb, var(--accent-2) 10%, transparent) 62%, transparent);
      box-shadow:
        0 18px 38px rgba(0,0,0,0.24),
        0 0 26px color-mix(in srgb, var(--accent-2) 10%, transparent),
        inset 0 1px 0 rgba(255,255,255,0.08);
    }

    .chat-shell[data-style="aurora"] .avatar,
    .chat-shell[data-style="aurora"] .avatar-ring {
      border-radius: 999px;
    }

    .chat-shell[data-style="nightgrid"] {
      font-family: "JetBrains Mono", "Segoe UI", monospace;
    }

    .chat-shell[data-style="nightgrid"] .message-zone {
      background:
        linear-gradient(180deg, rgba(255,255,255,0.02), transparent 24%),
        linear-gradient(0deg, rgba(4,8,18,0.22), transparent 18%),
        repeating-linear-gradient(
          90deg,
          rgba(105,242,255,0.035),
          rgba(105,242,255,0.035) 1px,
          transparent 1px,
          transparent 28px
        );
    }

    .chat-shell[data-style="nightgrid"] .message {
      border-radius: 16px;
      border-color: color-mix(in srgb, var(--accent) 34%, rgba(255,255,255,0.08));
      background:
        linear-gradient(180deg, rgba(11,18,34,0.96), rgba(8,12,24,0.98)),
        linear-gradient(135deg, rgba(105,242,255,0.08), transparent 54%);
      box-shadow:
        0 20px 34px rgba(0,0,0,0.30),
        inset 0 0 0 1px rgba(105,242,255,0.08);
    }

    .chat-shell[data-style="nightgrid"] .message::before {
      background: linear-gradient(90deg, color-mix(in srgb, var(--user-color, var(--accent)) 40%, transparent), transparent 18%);
    }

    .chat-shell[data-style="nightgrid"] .message::after {
      content: "";
      position: absolute;
      top: 10px;
      right: 12px;
      width: 56px;
      height: 2px;
      background: linear-gradient(90deg, var(--accent), transparent);
      opacity: 0.95;
    }

    .chat-shell[data-style="nightgrid"] .avatar,
    .chat-shell[data-style="nightgrid"] .avatar-ring {
      border-radius: 14px;
    }

    .chat-shell[data-style="nightgrid"] .chip,
    .chat-shell[data-style="nightgrid"] .time,
    .chat-shell[data-style="nightgrid"] .eyebrow,
    .chat-shell[data-style="nightgrid"] .title {
      font-family: "JetBrains Mono", "Segoe UI", monospace;
      letter-spacing: 0.08em;
    }

    .chat-shell[data-style="nightgrid"] .text {
      font-size: 18px;
    }

    .chat-shell[data-style="glass"] .message {
      background:
        linear-gradient(180deg, rgba(255,255,255,0.14), rgba(255,255,255,0.05)),
        linear-gradient(135deg, rgba(119,228,255,0.12), rgba(146,176,255,0.07));
      border: 1px solid rgba(255,255,255,0.16);
      box-shadow:
        0 18px 32px rgba(0,0,0,0.18),
        inset 0 1px 0 rgba(255,255,255,0.18);
      backdrop-filter: blur(18px) saturate(1.08);
    }

    .chat-shell[data-style="glass"] .avatar,
    .chat-shell[data-style="glass"] .avatar-ring {
      border-radius: 20px;
    }

    .chat-shell[data-style="ember"] .message {
      border-radius: 20px;
      border-color: rgba(255,139,103,0.18);
      background:
        linear-gradient(180deg, rgba(45,24,20,0.94), rgba(28,18,16,0.98)),
        linear-gradient(135deg, rgba(255,139,103,0.12), transparent 56%);
      box-shadow:
        0 18px 34px rgba(0,0,0,0.30),
        0 0 24px rgba(255,139,103,0.10);
    }

    .chat-shell[data-style="ember"] .message::before {
      background: linear-gradient(90deg, rgba(255,139,103,0.28), rgba(255,195,109,0.12), transparent 38%);
    }

    .chat-shell[data-style="lounge"] .message {
      border-radius: 26px;
      border-color: rgba(126,242,199,0.18);
      background:
        linear-gradient(180deg, rgba(13,35,34,0.92), rgba(20,42,45,0.98)),
        radial-gradient(circle at left center, rgba(126,242,199,0.12), transparent 36%);
      box-shadow:
        0 18px 36px rgba(0,0,0,0.24),
        0 0 28px rgba(126,242,199,0.08);
    }

    .chat-shell[data-style="lounge"] .message::before {
      background: linear-gradient(90deg, rgba(255,208,125,0.12), transparent 28%);
    }

    .chat-shell[data-style="lounge"] .avatar,
    .chat-shell[data-style="lounge"] .avatar-ring {
      border-radius: 999px;
    }

    .chat-shell[data-style="paper"] {
      font-family: "Georgia", "Times New Roman", serif;
    }

    .chat-shell[data-style="paper"] .message {
      border-radius: 18px;
      border-color: rgba(110,84,61,0.18);
      background:
        linear-gradient(180deg, rgba(247,239,225,0.98), rgba(236,225,204,0.97)),
        linear-gradient(135deg, rgba(198,111,83,0.08), transparent 46%);
      box-shadow:
        0 12px 18px rgba(75,57,42,0.12),
        inset 0 1px 0 rgba(255,255,255,0.55);
    }

    .chat-shell[data-style="paper"] .message::before {
      background: linear-gradient(90deg, rgba(198,111,83,0.18), rgba(229,181,108,0.08), transparent 36%);
    }

    .chat-shell[data-style="paper"] .avatar,
    .chat-shell[data-style="paper"] .avatar-ring {
      border-radius: 12px;
    }

    .chat-shell[data-style="paper"] .name,
    .chat-shell[data-style="paper"] .title {
      letter-spacing: 0.02em;
    }

    .chat-shell[data-style="paper"] .chip {
      background: rgba(91,138,128,0.12);
      border-color: rgba(91,138,128,0.18);
      color: #5d4b40;
    }

    .chat-shell[data-style="paper"] .time {
      color: #7d695c;
    }

    .chat-shell[data-style="arena"] .message {
      border-radius: 18px;
      border-color: rgba(255,103,103,0.22);
      background:
        linear-gradient(180deg, rgba(14,17,27,0.95), rgba(20,27,40,0.98)),
        linear-gradient(135deg, rgba(255,103,103,0.10), rgba(88,218,255,0.08) 52%, transparent 72%);
      box-shadow:
        0 18px 32px rgba(0,0,0,0.32),
        0 0 24px rgba(255,103,103,0.12);
    }

    .chat-shell[data-style="arena"] .message::before {
      background: linear-gradient(90deg, rgba(255,103,103,0.20), rgba(88,218,255,0.16) 38%, transparent 72%);
    }

    .chat-shell[data-style="arena"] .message::after {
      content: "";
      position: absolute;
      left: 0;
      right: 0;
      bottom: 0;
      height: 3px;
      background: linear-gradient(90deg, var(--accent), var(--accent-2), var(--accent-3));
      opacity: 0.95;
    }

    .chat-shell[data-style="arena"] .avatar,
    .chat-shell[data-style="arena"] .avatar-ring {
      border-radius: 16px;
      clip-path: polygon(18% 0, 100% 0, 100% 82%, 82% 100%, 0 100%, 0 18%);
    }

    .chat-shell[data-style="arena"] .chip {
      letter-spacing: 0.10em;
    }

    .chat-shell[data-style="noir"] {
      font-family: "Georgia", "Times New Roman", serif;
    }

    .chat-shell[data-style="noir"] .topline {
      animation: none;
      opacity: 0.46;
      background: linear-gradient(90deg, transparent, var(--accent), transparent);
    }

    .chat-shell[data-style="noir"] .message {
      grid-template-columns: 46px minmax(0, 1fr);
      border-radius: 14px;
      border-color: rgba(240,213,150,0.16);
      background:
        linear-gradient(180deg, rgba(16,17,21,0.96), rgba(23,24,28,0.98));
      box-shadow:
        0 12px 22px rgba(0,0,0,0.30);
    }

    .chat-shell[data-style="noir"] .message::before {
      background: linear-gradient(90deg, rgba(240,213,150,0.20), transparent 12%);
      opacity: 0.72;
    }

    .chat-shell[data-style="noir"] .avatar,
    .chat-shell[data-style="noir"] .avatar-ring {
      border-radius: 14px;
    }

    .chat-shell[data-style="noir"] .name,
    .chat-shell[data-style="noir"] .title {
      letter-spacing: 0.06em;
      text-transform: uppercase;
    }

    .chat-shell[data-style="noir"] .text {
      font-size: 19px;
      font-weight: 500;
    }

    .chat-shell[data-style="noir"] .time,
    .chat-shell[data-style="noir"] .chip {
      font-family: "JetBrains Mono", "Segoe UI", monospace;
    }

    @keyframes messageIn {
      0% {
        opacity: 0;
        transform: translateY(22px) scale(0.985);
        filter: blur(10px);
      }
      100% {
        opacity: 1;
        transform: translateY(0) scale(1);
        filter: blur(0);
      }
    }

    @keyframes messageOut {
      0%, 84% {
        opacity: 1;
        transform: translateY(0) scale(1);
        filter: blur(0);
      }
      100% {
        opacity: 0;
        transform: translateY(-10px) scale(0.985);
        filter: blur(10px);
      }
    }

    @keyframes messageOutNow {
      from {
        opacity: 1;
        transform: translateY(0) scale(1);
        filter: blur(0);
      }
      to {
        opacity: 0;
        transform: translateY(-8px) scale(0.985);
        filter: blur(8px);
      }
    }

    @keyframes pulseDot {
      0%, 100% { opacity: 0.72; transform: scale(1); }
      50% { opacity: 1; transform: scale(1.16); }
    }

    @keyframes signal {
      0%, 100% { transform: scaleY(0.72); opacity: 0.7; }
      50% { transform: scaleY(1.18); opacity: 1; }
    }

    @keyframes sweep {
      0% { background-position: 0% 50%; }
      100% { background-position: 180% 50%; }
    }

    @media (max-width: 900px) {
      .chat-shell {
        width: min(max(300px, calc(var(--panel-width) * 1vw)), 94vw);
        top: 12px;
      }

      .text {
        font-size: 18px;
      }
    }
  </style>
</head>
<body>
  <div class="stage">
    <section class="chat-shell right" id="chatShell">
      <div class="topline"></div>

      <div class="chrome">
        <div class="status">
          <div class="orb-wrap">
            <div class="orb"></div>
          </div>

          <div class="titles">
            <div class="eyebrow">Локальный рендер</div>
            <div class="title" id="chatTitle">ЧАТ TWITCH // ЭФИР</div>
            <div class="subtitle" id="chatSubtitle">
              <span>Подключение…</span>
              <span class="mode" id="chatMode">anon</span>
            </div>
          </div>
        </div>

        <div class="meta-panel">
          <div class="signal" aria-hidden="true">
            <span></span><span></span><span></span><span></span><span></span>
          </div>
          <div class="badge idle" id="chatBadge">IDLE</div>
        </div>
      </div>

      <div class="message-zone">
        <div class="messages" id="messages"></div>

        <div class="placeholder" id="placeholder">
          Вставь Twitch-канал или ссылку на чат. Для более надежного подключения можно указать логин и OAuth token, тогда overlay подключится к IRC не анонимно.
        </div>
      </div>

      <div class="footer">
        <div id="footerText"><strong>ЛОКАЛЬНЫЙ РЕНДЕР</strong> · без iframe · OBS-ready</div>
        <div id="counterText">0 сообщений</div>
      </div>
    </section>
  </div>

  <script id="chat-config" type="application/json">__INITIAL_JSON__</script>
  <script>
    const root = document.documentElement;
    const shell = document.getElementById("chatShell");
    const messages = document.getElementById("messages");
    const placeholder = document.getElementById("placeholder");
    const titleEl = document.getElementById("chatTitle");
    const subtitleEl = document.getElementById("chatSubtitle");
    const badgeEl = document.getElementById("chatBadge");
    const modeEl = document.getElementById("chatMode");
    const footerEl = document.getElementById("footerText");
    const counterEl = document.getElementById("counterText");

    let currentConfig = {};
    let twitchSocket = null;
    let reconnectTimer = null;
    let reconnectAttempts = 0;
    let currentSignature = "";
    let currentChannel = "";
    let visualSignature = "";
    let recentMessageIds = new Map();
    let joinAcknowledged = false;
    let hideShellTimer = null;
"""
    part3 = """

    function updateCounter() {
      const count = messages.children.length;
      counterEl.textContent = `${count} сообщ${count === 1 ? "ение" : count < 5 ? "ения" : "ений"}`;
    }

    function revealOnlyEnabled() {
      return Boolean(currentConfig.reveal_only);
    }

    function clearHideShellTimer() {
      if (!hideShellTimer) return;
      clearTimeout(hideShellTimer);
      hideShellTimer = null;
    }

    function setShellVisible(visible) {
      shell.classList.toggle("idle-hidden", revealOnlyEnabled() && !visible);
    }

    function syncChatVisibility(forceVisible = false) {
      const hasMessages = messages.children.length > 0;
      shell.classList.toggle("reveal-only", revealOnlyEnabled());
      placeholder.classList.toggle("hidden", revealOnlyEnabled() || hasMessages);
      updateCounter();

      if (!revealOnlyEnabled()) {
        clearHideShellTimer();
        setShellVisible(true);
        return;
      }

      if (forceVisible || hasMessages) {
        clearHideShellTimer();
        setShellVisible(true);
        return;
      }

      clearHideShellTimer();
      hideShellTimer = setTimeout(() => {
        if (!messages.children.length) {
          setShellVisible(false);
        }
      }, Number(currentConfig.idle_fade_ms || 340));
    }

    function updateConnectionState(state, note = "") {
      shell.dataset.state = state;
      badgeEl.className = "badge " + state;
      badgeEl.textContent = state === "live" ? "ЭФИР" : state === "retry" ? "ПОВТОР" : state === "sync" ? "СИНК" : "ОЖИДАНИЕ";
      if (note) {
        footerEl.innerHTML = note;
      }
    }

    function configVisualSignature(config) {
      return JSON.stringify({
        style_key: config.style_key || "custom",
        side_key: config.side_key || "right",
        compact_mode: Boolean(config.compact_mode),
        reveal_only: Boolean(config.reveal_only),
        title: config.title || "",
        subtitle: config.subtitle || "",
        auth_mode: config.auth_mode || "",
        accent: config.accent || "",
        accent2: config.accent2 || "",
        accent3: config.accent3 || "",
        panel: config.panel || "",
        panel2: config.panel2 || "",
        panel3: config.panel3 || "",
        text: config.text || "",
        muted: config.muted || "",
        line: config.line || "",
        shadow: config.shadow || "",
        panel_width_percent: Number(config.panel_width_percent || 31),
        font_family: config.font_family || "",
        title_font_family: config.title_font_family || "",
        message_fill: config.message_fill || "",
        message_size: config.message_size || "",
        shell_radius: config.shell_radius || "",
        bubble_radius: config.bubble_radius || "",
      });
    }

    function applyShellLayout(config) {
      shell.classList.remove("left", "right", "compact");
      shell.classList.add(config.side_key === "left" ? "left" : "right");
      shell.classList.toggle("compact", Boolean(config.compact_mode));
      shell.dataset.style = String(config.style_key || "custom");
    }

    function setVar(name, value) {
      root.style.setProperty(name, value);
    }

    function safeInitials(name) {
      const clean = (name || "?").trim();
      const parts = clean.split(/\\s+/).filter(Boolean);
      if (parts.length > 1) {
        return (parts[0][0] + parts[1][0]).toUpperCase();
      }
      return clean.slice(0, 2).toUpperCase();
    }

    function hashGradient(name) {
      let hash = 0;
      for (let i = 0; i < name.length; i++) {
        hash = ((hash << 5) - hash) + name.charCodeAt(i);
        hash |= 0;
      }
      const hue = Math.abs(hash) % 360;
      return `linear-gradient(135deg, hsl(${hue} 78% 62%), hsl(${(hue + 44) % 360} 84% 64%))`;
    }

    function hashColor(name) {
      let hash = 0;
      for (let i = 0; i < name.length; i++) {
        hash = ((hash << 5) - hash) + name.charCodeAt(i);
        hash |= 0;
      }
      const hue = Math.abs(hash) % 360;
      return `hsl(${hue} 78% 64%)`;
    }

    function rememberMessageId(messageId) {
      if (!messageId) return false;
      const now = Date.now();
      for (const [key, value] of recentMessageIds.entries()) {
        if ((now - value) > 30000) {
          recentMessageIds.delete(key);
        }
      }
      if (recentMessageIds.has(messageId)) {
        return true;
      }
      recentMessageIds.set(messageId, now);
      return false;
    }

    function parseTags(raw) {
      const tags = {};
      if (!raw.startsWith("@")) return tags;
      const spaceIndex = raw.indexOf(" ");
      if (spaceIndex === -1) return tags;
      const body = raw.slice(1, spaceIndex);
      for (const part of body.split(";")) {
        const eq = part.indexOf("=");
        if (eq === -1) {
          tags[part] = "";
        } else {
          tags[part.slice(0, eq)] = part.slice(eq + 1);
        }
      }
      return tags;
    }

    function parseBadgeList(tags) {
      const badges = [];
      const raw = String(tags["badges"] || "");
      const names = raw ? raw.split(",").map((part) => part.split("/")[0]) : [];

      if (names.includes("broadcaster")) badges.push({ label: "caster", kind: "caster" });
      if (names.includes("moderator")) badges.push({ label: "mod", kind: "mod" });
      if (names.includes("vip")) badges.push({ label: "vip", kind: "vip" });
      if (names.includes("subscriber")) badges.push({ label: "sub", kind: "sub" });
      if (tags["first-msg"] === "1") badges.push({ label: "first", kind: "first" });
      if (tags["returning-chatter"] === "1") badges.push({ label: "return", kind: "return" });

      const bits = Number(tags["bits"] || 0);
      if (bits > 0) badges.push({ label: `${bits} bits`, kind: "bits" });
      return badges;
    }

    function parseEmotes(text, rawEmotes) {
      if (!rawEmotes) {
        return [{ type: "text", text }];
      }

      const items = [];
      for (const group of String(rawEmotes).split("/")) {
        const [id, positionsRaw] = group.split(":");
        if (!id || !positionsRaw) continue;
        for (const entry of positionsRaw.split(",")) {
          const [startRaw, endRaw] = entry.split("-");
          const start = Number(startRaw);
          const end = Number(endRaw);
          if (Number.isFinite(start) && Number.isFinite(end)) {
            items.push({ id, start, end });
          }
        }
      }

      items.sort((left, right) => left.start - right.start);
      const parts = [];
      let cursor = 0;
      for (const item of items) {
        if (item.start < cursor) continue;
        if (item.start > cursor) {
          parts.push({ type: "text", text: text.slice(cursor, item.start) });
        }
        parts.push({ type: "emote", id: item.id, text: text.slice(item.start, item.end + 1) });
        cursor = item.end + 1;
      }
      if (cursor < text.length) {
        parts.push({ type: "text", text: text.slice(cursor) });
      }
      return parts.length ? parts : [{ type: "text", text }];
    }

    function buildRichText(text, tags) {
      const fragment = document.createDocumentFragment();
      for (const part of parseEmotes(text, tags["emotes"])) {
        if (part.type === "emote") {
          const img = document.createElement("img");
          img.className = "emote";
          img.alt = part.text;
          img.src = `https://static-cdn.jtvnw.net/emoticons/v2/${part.id}/default/dark/2.0`;
          fragment.appendChild(img);
          continue;
        }

        const span = document.createElement("span");
        span.className = "text-piece";
        span.textContent = part.text;
        fragment.appendChild(span);
      }
      return fragment;
    }

    function addMessage(username, text, color = "", tags = {}) {
      if (!text.trim()) return;

      const badges = parseBadgeList(tags);
      const item = document.createElement("div");
      const isHighlight = badges.some((badge) => badge.kind === "caster" || badge.kind === "bits");
      item.className = "message" + (isHighlight ? " highlight" : "");
      item.style.setProperty("--message-life", `${Number(currentConfig.message_life_ms || 11800)}ms`);
      item.style.setProperty("--user-color", color || hashColor(username));

      const avatarWrap = document.createElement("div");
      avatarWrap.className = "avatar-wrap";
      const avatarRing = document.createElement("div");
      avatarRing.className = "avatar-ring";
      const avatar = document.createElement("div");
      avatar.className = "avatar";
      avatar.textContent = safeInitials(username);
      avatar.style.background = color ? `linear-gradient(135deg, ${color}, var(--accent-2))` : hashGradient(username);
      avatarWrap.appendChild(avatarRing);
      avatarWrap.appendChild(avatar);

      const content = document.createElement("div");
      content.className = "content";
      const meta = document.createElement("div");
      meta.className = "meta";
      const identity = document.createElement("div");
      identity.className = "identity";

      const nameEl = document.createElement("div");
      nameEl.className = "name";
      nameEl.textContent = username || "user";
      if (color) {
        nameEl.style.color = color;
      }

      const chips = document.createElement("div");
      chips.className = "chips";
      for (const badge of badges) {
        const chip = document.createElement("div");
        chip.className = "chip " + badge.kind;
        chip.textContent = badge.label;
        chips.appendChild(chip);
      }

      if (tags["reply-parent-display-name"]) {
        const replyChip = document.createElement("div");
        replyChip.className = "chip reply";
        const span = document.createElement("span");
        span.textContent = `ответ: ${tags["reply-parent-display-name"]}`;
        replyChip.appendChild(span);
        chips.appendChild(replyChip);
      }

      identity.appendChild(nameEl);
      if (chips.children.length) {
        identity.appendChild(chips);
      }

      const timeEl = document.createElement("div");
      timeEl.className = "time";
      timeEl.textContent = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

      meta.appendChild(identity);
      meta.appendChild(timeEl);

      const textEl = document.createElement("div");
      textEl.className = "text";
      textEl.appendChild(buildRichText(text, tags));

      content.appendChild(meta);
      content.appendChild(textEl);
      item.appendChild(avatarWrap);
      item.appendChild(content);
      messages.appendChild(item);

      const maxItems = Number(currentConfig.max_messages || 5);
      while (messages.children.length > maxItems) {
        const first = messages.firstElementChild;
        if (!first) break;
        first.classList.add("removing");
        setTimeout(() => first.remove(), 430);
        break;
      }

      syncChatVisibility(true);
      const life = Number(currentConfig.message_life_ms || 11800);
      setTimeout(() => {
        if (item.isConnected) {
          item.remove();
          syncChatVisibility();
        }
      }, life + 160);
    }

    function clearMessages() {
      messages.innerHTML = "";
      syncChatVisibility();
    }

    function normalizeToken(raw) {
      const token = String(raw || "").trim();
      if (!token) return "";
      return token.toLowerCase().startsWith("oauth:") ? token : `oauth:${token}`;
    }

    function desiredSignature(config) {
      return [
        String(config.twitch_channel || "").trim(),
        String(config.irc_username || "").trim().toLowerCase(),
        normalizeToken(config.irc_token || ""),
      ].join("|");
    }

    function disconnectTwitch() {
      joinAcknowledged = false;
      if (reconnectTimer) {
        clearTimeout(reconnectTimer);
        reconnectTimer = null;
      }
      if (twitchSocket) {
        try {
          twitchSocket.close();
        } catch (error) {
        }
        twitchSocket = null;
      }
    }

    function connectTwitch(channel) {
      disconnectTwitch();
      if (!channel) {
        currentChannel = "";
        updateConnectionState("idle", "<strong>LOCAL RENDER</strong> · укажи Twitch-канал");
        return;
      }

      const useAuth = Boolean(currentConfig.irc_username && currentConfig.irc_token);
      currentChannel = channel;
      joinAcknowledged = false;
      updateConnectionState(
        "sync",
        useAuth
          ? `<strong>IRC-авторизация</strong> · логин: ${currentConfig.irc_username}`
          : "<strong>Анонимный IRC</strong> · для надежности можно добавить OAuth token"
      );

      const socket = new WebSocket("wss://irc-ws.chat.twitch.tv:443");
      twitchSocket = socket;

      socket.addEventListener("open", () => {
        reconnectAttempts = 0;
        const nick = useAuth
          ? String(currentConfig.irc_username).trim().toLowerCase()
          : "justinfan" + Math.floor(Math.random() * 100000);
        const pass = useAuth ? normalizeToken(currentConfig.irc_token) : "SCHMOOPIIE";
        socket.send(`PASS ${pass}`);
        socket.send(`NICK ${nick}`);
        socket.send("CAP REQ :twitch.tv/tags twitch.tv/commands twitch.tv/membership");
        socket.send(`JOIN #${channel}`);
        updateConnectionState("sync", `<strong>IRC-синхронизация</strong> · подключаемся к каналу: ${channel}`);
      });

      socket.addEventListener("message", (event) => {
        const rawText = String(event.data || "");
        for (const line of rawText.split("\\r\\n")) {
          handleIrcLine(line);
        }
      });

      socket.addEventListener("close", () => {
        if (currentChannel !== channel) return;
        joinAcknowledged = false;
        reconnectAttempts += 1;
        updateConnectionState(
          "retry",
          useAuth
            ? "<strong>IRC-переподключение</strong> · переподключаемся к чату…"
            : "<strong>Анонимный IRC</strong> · Twitch может требовать авторизацию, добавь логин и OAuth token"
        );
        reconnectTimer = setTimeout(
          () => connectTwitch(channel),
          Math.min(6500, 1800 + reconnectAttempts * 700)
        );
      });

      socket.addEventListener("error", () => {
        try {
          socket.close();
        } catch (error) {
        }
      });
    }

    function handleIrcLine(line) {
      if (!line) return;
      if (line.startsWith("PING")) {
        if (twitchSocket && twitchSocket.readyState === WebSocket.OPEN) {
          twitchSocket.send(line.replace("PING", "PONG"));
        }
        return;
      }

      if (line === "RECONNECT") {
        if (currentChannel) {
          connectTwitch(currentChannel);
        }
        return;
      }

      if (line.includes(" NOTICE ")) {
        const notice = line.split(" :")[1] || "Twitch отправил notice";
        updateConnectionState("retry", `<strong>Сообщение Twitch</strong> · ${notice}`);
        return;
      }

      if (line.includes(" 001 ") || line.includes(" ROOMSTATE ")) {
        if (!joinAcknowledged) {
          joinAcknowledged = true;
          const authText = currentConfig.auth_mode === "token" ? "IRC в эфире" : "Анонимный IRC в эфире";
          updateConnectionState("live", `<strong>${authText}</strong> · канал: ${currentChannel}`);
        }
        if (!line.includes("PRIVMSG")) {
          return;
        }
      }

      if (line.includes(" CLEARCHAT ")) {
        clearMessages();
        return;
      }

      if (!line.includes("PRIVMSG")) return;
      const tags = parseTags(line);
      const match = line.match(/^(?:@[^ ]+ )?:([^!]+)![^ ]+ PRIVMSG #[^ ]+ :(.*)$/);
      if (!match) return;

      const username = tags["display-name"] || match[1];
      const message = match[2] || "";
      const color = tags["color"] || "";
      const messageId = tags["id"] || `${username}|${message}|${tags["tmi-sent-ts"] || ""}`;
      if (rememberMessageId(messageId)) return;
      addMessage(username, message, color, tags);
    }

    function applyConfig(config) {
      currentConfig = config || {};

      setVar("--panel-width", String(config.panel_width_percent || 31));
      setVar("--body-font", config.font_family || '"Manrope", "Segoe UI", sans-serif');
      setVar("--title-font", config.title_font_family || '"Unbounded", "Manrope", sans-serif');
      setVar("--accent", config.accent || "#8ef7d4");
      setVar("--accent-2", config.accent2 || "#8ea8ff");
      setVar("--accent-3", config.accent3 || "#e28eff");
      setVar("--panel", config.panel || "rgba(7, 16, 26, 0.58)");
      setVar("--panel-2", config.panel2 || "rgba(14, 29, 41, 0.92)");
      setVar("--panel-3", config.panel3 || "rgba(19, 36, 48, 0.82)");
      setVar("--message-fill", config.message_fill || "rgba(19, 36, 48, 0.82)");
      setVar("--text", config.text || "#f5fbff");
      setVar("--muted", config.muted || "#b4c7dd");
      setVar("--line", config.line || "rgba(142, 247, 212, 0.26)");
      setVar("--shadow", config.shadow || "rgba(88, 218, 190, 0.22)");
      setVar("--message-size", config.message_size || "20px");
      setVar("--shell-radius", config.shell_radius || "34px");
      setVar("--bubble-radius", config.bubble_radius || "24px");

      const nextVisualSignature = configVisualSignature(config);
      if (nextVisualSignature !== visualSignature) {
        visualSignature = nextVisualSignature;
        applyShellLayout(config);
        titleEl.textContent = config.title || "ЧАТ TWITCH // ЭФИР";
        subtitleEl.firstElementChild.textContent = config.subtitle || "Ожидание канала";
        modeEl.textContent = config.auth_mode === "token" ? "автор" : "анон";
      }
      syncChatVisibility();

      const signature = desiredSignature(config);
      const channel = String(config.twitch_channel || "").trim();
      if (!channel) {
        currentSignature = "";
        disconnectTwitch();
        clearMessages();
        updateConnectionState("idle", "<strong>ЛОКАЛЬНЫЙ РЕНДЕР</strong> · укажи Twitch-канал");
        return;
      }

      if (signature !== currentSignature || !twitchSocket) {
        currentSignature = signature;
        connectTwitch(channel);
      }
    }

    async function pollConfig() {
      try {
        const response = await fetch("/chat?config=1&ts=" + Date.now(), { cache: "no-store" });
        if (!response.ok) return;
        const config = await response.json();
        applyConfig(config);
      } catch (error) {
      }
    }

    try {
      const initialConfig = JSON.parse(document.getElementById("chat-config").textContent || "{}");
      applyConfig(initialConfig);
    } catch (error) {
    }

    setInterval(pollConfig, 1500);
  </script>
</body>
</html>
"""
    template = part1 + part2 + part3
    return template.replace("__APP_TITLE__", APP_TITLE).replace("__INITIAL_JSON__", initial_json)


def build_overlay_html(frame_path: str = "/frame.png") -> str:
    template = """<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>__APP_TITLE__ overlay</title>
  <style>
    html, body {
      margin: 0;
      width: 100%;
      height: 100%;
      overflow: hidden;
      background: transparent;
    }
    img {
      display: block;
      width: 100%;
      height: 100%;
      object-fit: fill;
      image-rendering: auto;
    }
  </style>
</head>
<body>
  <img id="frame" src="__FRAME_PATH__?boot=1" alt="">
  <script>
    const frame = document.getElementById("frame");
    setInterval(() => {
      frame.src = "__FRAME_PATH__?ts=" + Date.now();
    }, __OVERLAY_REFRESH_MS__);
  </script>
</body>
</html>
"""
    return (
        template
        .replace("__APP_TITLE__", APP_TITLE)
        .replace("__OVERLAY_REFRESH_MS__", str(OVERLAY_REFRESH_MS))
        .replace("__FRAME_PATH__", frame_path)
    )
