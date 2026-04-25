from __future__ import annotations

from html import escape
import json
import mimetypes
import threading
import time
import webbrowser
from dataclasses import dataclass, replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from audio_monitor import AudioMonitor, InputDevice, list_input_devices
from chat_overlay import build_chat_config, build_chat_overlay_html, build_overlay_html
from constants import (
    APP_TITLE,
    CHAT_SIDE_OPTIONS,
    CHAT_STYLE_OPTIONS,
    HANG_SECONDS,
    INTERNET_PRESET_OPTIONS,
    INTERNET_PRESET_PACKS,
    OVERLAY_PORT_START,
    POLL_MS,
    SCENE_PRESETS,
    SCENE_STYLE_OPTIONS,
    STREAM_MOMENT_OPTIONS,
)
from overlay_server import OverlayState
from scene_renderer import SceneRenderParams, SceneRenderer
from utils import (
    clamp,
    default_image_path,
    extract_twitch_channel,
    normalize_tune2live_url,
    parse_int,
    portable_media_path,
    resolve_media_path,
    user_data_dir,
)


def coerce_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on", "да"}
    if isinstance(value, (int, float)):
        return bool(value)
    return False


@dataclass(slots=True)
class StaticResponse:
    content: bytes
    content_type: str


def build_tune2live_embed_html(title: str, target_url: str, kind: str) -> str:
    safe_title = escape(title)
    safe_target = escape(target_url, quote=True)
    safe_kind = escape(kind, quote=True)
    return f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{safe_title}</title>
  <style>
    html, body {{
      margin: 0;
      width: 100%;
      height: 100%;
      overflow: hidden;
      background: transparent;
      font-family: "Segoe UI Variable", "Segoe UI", sans-serif;
      color: #f4f8ff;
    }}
    body {{
      background:
        radial-gradient(circle at top left, rgba(116, 231, 255, 0.08), transparent 34%),
        radial-gradient(circle at top right, rgba(255, 102, 199, 0.08), transparent 28%),
        rgba(4, 8, 14, 0.92);
    }}
    .music-stage {{
      position: fixed;
      inset: 0;
      overflow: hidden;
      background: transparent;
    }}
    .music-shell {{
      position: absolute;
      inset: 0;
      transition:
        opacity 220ms ease,
        transform 260ms cubic-bezier(0.22, 1, 0.36, 1),
        filter 220ms ease;
      transform-origin: center center;
    }}
    .music-frame {{
      width: 100%;
      height: 100%;
      border: 0;
      background: transparent;
      transition:
        opacity 220ms ease,
        transform 260ms cubic-bezier(0.22, 1, 0.36, 1),
        filter 220ms ease;
    }}
    .music-mask {{
      position: absolute;
      inset: 0;
      pointer-events: none;
      opacity: 0;
      background:
        radial-gradient(circle at top left, rgba(116, 231, 255, 0.12), transparent 32%),
        linear-gradient(180deg, rgba(3, 7, 12, 0.26), rgba(3, 7, 12, 0.72));
      transition: opacity 220ms ease;
    }}
    .music-empty {{
      position: absolute;
      inset: 0;
      display: grid;
      place-content: center;
      gap: 10px;
      text-align: center;
      padding: 24px;
      color: rgba(244, 248, 255, 0.86);
    }}
    .music-empty strong {{
      font-size: 20px;
      letter-spacing: 0.02em;
    }}
    .music-empty span {{
      color: rgba(180, 199, 221, 0.9);
      max-width: 420px;
      line-height: 1.5;
    }}
    .music-shell.engaged.dim .music-frame {{
      opacity: var(--music-floor, 0.35);
      transform: scale(0.992);
      filter: saturate(0.72) brightness(0.72);
    }}
    .music-shell.engaged.dim .music-mask {{
      opacity: 0.38;
    }}
    .music-shell.engaged.hide .music-frame {{
      opacity: 0.02;
      transform: scale(0.985) translateY(10px);
      filter: blur(6px) brightness(0.45);
    }}
    .music-shell.engaged.hide .music-mask {{
      opacity: 0.7;
    }}
    .music-shell.idle .music-mask {{
      opacity: 0;
    }}
  </style>
</head>
<body>
  <div class="music-stage">
    <div class="music-shell idle" id="musicShell" style="--music-floor:0.35;">
      <iframe id="musicFrame" class="music-frame" src="{safe_target}" allow="autoplay; encrypted-media; picture-in-picture; fullscreen; clipboard-read; clipboard-write" referrerpolicy="no-referrer-when-downgrade"></iframe>
      <div class="music-mask" id="musicMask"></div>
      <div class="music-empty" id="musicEmpty">
        <strong>{safe_title}</strong>
        <span>Сначала добавь ссылку Tune2Live в панели управления.</span>
      </div>
    </div>
  </div>
  <script>
    const KIND = "{safe_kind}";
    const frame = document.getElementById("musicFrame");
    const shell = document.getElementById("musicShell");
    const empty = document.getElementById("musicEmpty");
    const state = {{
      target: "{safe_target}",
      mode: "off",
      threshold: 18,
      floor: 0.35,
      releaseMs: 900,
      enabled: false,
      level: 0,
      monitorRunning: false,
      lastTrigger: 0,
      eventSource: null,
      configTimer: null,
      tickTimer: null,
    }};

    function targetKey() {{
      return KIND === "player" ? "musicPlayerDirect" : (KIND === "queue" ? "musicQueueDirect" : "musicDockDirect");
    }}

    function enabledKey(settings) {{
      if (KIND === "player") return Boolean(settings.tuneAutoPlayer);
      if (KIND === "queue") return Boolean(settings.tuneAutoQueue);
      return Boolean(settings.tuneAutoDock);
    }}

    function updateFrameTarget(nextTarget) {{
      const safeTarget = String(nextTarget || "").trim();
      state.target = safeTarget;
      if (safeTarget && frame.dataset.target !== safeTarget) {{
        frame.src = safeTarget;
        frame.dataset.target = safeTarget;
      }}
      if (!safeTarget) frame.dataset.target = "";
      const hasTarget = Boolean(safeTarget);
      frame.style.display = hasTarget ? "block" : "none";
      empty.style.display = hasTarget ? "none" : "grid";
    }}

    function applyVisualState() {{
      const engaged = state.enabled
        && state.monitorRunning
        && state.mode !== "off"
        && Boolean(state.target)
        && (state.level >= state.threshold || (Date.now() - state.lastTrigger) < state.releaseMs);

      shell.style.setProperty("--music-floor", String(Math.max(0, Math.min(1, state.floor))));
      shell.classList.remove("dim", "hide", "engaged", "idle");

      if (engaged) {{
        shell.classList.add("engaged", state.mode);
      }} else {{
        shell.classList.add("idle");
      }}
    }}

    async function pullConfig() {{
      try {{
        const response = await fetch("/api/state", {{ cache: "no-store" }});
        if (!response.ok) return;
        const data = await response.json();
        const settings = data.settings || {{}};
        const routes = data.routes || {{}};
        state.mode = String(settings.tuneAutoMode || "off");
        state.threshold = Number(settings.tuneAutoThreshold || 18);
        state.floor = Number(settings.tuneAutoFloor || 35) / 100;
        state.releaseMs = Number(settings.tuneAutoReleaseMs || 900);
        state.enabled = enabledKey(settings);
        updateFrameTarget(routes[targetKey()] || "");
        applyVisualState();
      }} catch (error) {{
        console.error(error);
      }}
    }}

    function connectEvents() {{
      if (state.eventSource) {{
        try {{ state.eventSource.close(); }} catch (error) {{ console.error(error); }}
      }}
      const source = new EventSource("/api/events");
      state.eventSource = source;

      const handleSignal = (event) => {{
        try {{
          const payload = JSON.parse(event.data || "{{}}");
          state.level = Number(payload.audioLevel || 0);
          state.monitorRunning = Boolean(payload.monitorRunning);
          if (state.level >= state.threshold) {{
            state.lastTrigger = Date.now();
          }}
          applyVisualState();
        }} catch (error) {{
          console.error(error);
        }}
      }};

      source.addEventListener("hello", handleSignal);
      source.addEventListener("signal", handleSignal);
      source.onerror = () => {{
        try {{ source.close(); }} catch (error) {{ console.error(error); }}
        state.eventSource = null;
        setTimeout(connectEvents, 1000);
      }};
    }}

    updateFrameTarget(state.target);
    pullConfig();
    connectEvents();
    state.configTimer = setInterval(pullConfig, 1600);
    state.tickTimer = setInterval(applyVisualState, 120);
  </script>
</body>
</html>"""


class WebRuntime:
    def __init__(self, host: str = "127.0.0.1") -> None:
        self.host = host
        self.base_dir = Path(__file__).resolve().parent
        self.web_dir = self.base_dir / "web"
        self.assets_dir = self.base_dir / "assets"
        self.settings_path = user_data_dir(APP_TITLE) / "settings.json"

        self.lock = threading.RLock()
        self.stop_event = threading.Event()
        self.session_id = str(int(time.time() * 1000))

        self.monitor = AudioMonitor()
        self.renderer = SceneRenderer()
        self.overlay_state = OverlayState()

        self.server: WebHTTPServer | None = None
        self.server_thread: threading.Thread | None = None
        self.loop_thread: threading.Thread | None = None
        self.overlay_port = 0

        self.device_map: dict[str, InputDevice] = {}
        self.device_labels: list[str] = []
        self.device_label = ""

        self.image_paths = {
            "idle": portable_media_path(self.base_dir, default_image_path(self.base_dir, "1.png")),
            "talk_a": portable_media_path(self.base_dir, default_image_path(self.base_dir, "2.png")),
            "talk_b": portable_media_path(self.base_dir, default_image_path(self.base_dir, "3.png")),
        }
        self.bg_path = ""
        self.threshold = 12.0

        self.bg_mode = "transparent"
        self.bg_color = "#00FF66"
        self.preset_label = "1280 x 720 (HD)"
        self.scene_style = "Кибер-пульс"
        self.width_text = "1280"
        self.height_text = "720"
        self.anchor_label = "Справа снизу"
        self.scale_percent = 58.0
        self.margin_x = 26.0
        self.margin_y = 18.0
        self.show_scene_frame = False
        self.show_scene_label = False
        self.show_scene_ribbon = False

        self.chat_style = "Аврора"
        self.chat_side = "Справа"
        self.chat_width_percent = 31.0
        self.chat_url = ""
        self.chat_auth_user = ""
        self.chat_auth_token = ""
        self.chat_compact_mode = True
        self.chat_reveal_only = True
        self.tune_player_url = ""
        self.tune_queue_url = ""
        self.tune_dock_url = ""
        self.tune_auto_mode = "off"
        self.tune_auto_threshold = 18.0
        self.tune_auto_floor = 35.0
        self.tune_auto_release_ms = 900
        self.tune_auto_player = True
        self.tune_auto_queue = True
        self.tune_auto_dock = False
        self.internet_pack = "Ночной грид"
        self.stream_moment = "Геймплей"
        self.preset_note = ""

        self.scene_size_cache = SCENE_PRESETS[self.preset_label]
        self.current_frame = "idle"
        self.talk_frame = "talk_a"
        self.last_voice = 0.0
        self.last_anim = 0.0
        self.last_level_value = 0.0
        self.last_render_level = 0.0
        self.last_visual_refresh = 0.0
        self.frame_version = 0
        self.chat_twitch_channel = ""
        self.chat_overlay_config_cache: dict[str, object] = {}
        self._overlay_png = b""
        self._clean_overlay_png = b""
        self.scene_dirty = True

        self.status_text = "Микрофон пока остановлен."
        self.chat_text = "Вставь канал Twitch, ссылку на канал или чат Twitch."
        self.capture_hint = "Локальная web-панель готовится."
        self.scene_meta = "Сцена готовится."
        self.hero_scene = self.scene_style
        self.hero_chat = "Чат не подключен"
        self.hero_signal = "МИК ВЫКЛ"
        self.deck_overlay = "сцена недоступна"
        self.deck_chat = "чат недоступен"
        self.overlay_url = ""
        self.chat_browser_url = ""
        self.music_player_url = ""
        self.music_queue_url = ""
        self.music_dock_url = ""
        self.obs_help = ""
        self.media_errors: list[str] = []
        self.tune_status = "Tune2Live пока не подключен."

        self.refresh_devices()
        self.apply_stream_preset()
        self.load_settings()
        self.refresh_chat_overlay_cache()
        self.refresh_tune2live_cache()
        self.update_guidance()
        self.reload_media(show_errors=False)
        self.render()

    @property
    def dashboard_url(self) -> str:
        return f"http://{self.host}:{self.overlay_port}/"

    def start(self, *, open_browser_on_start: bool = False) -> None:
        port = OVERLAY_PORT_START
        while port < OVERLAY_PORT_START + 25:
            try:
                self.server = WebHTTPServer((self.host, port), self)
                self.overlay_port = port
                break
            except OSError:
                port += 1

        if self.server is None:
            raise RuntimeError("Не удалось поднять локальный web-сервер.")

        with self.lock:
            self.overlay_url = f"http://{self.host}:{self.overlay_port}/overlay"
            self.chat_browser_url = f"http://{self.host}:{self.overlay_port}/chat"
            self.music_player_url = f"http://{self.host}:{self.overlay_port}/music/player"
            self.music_queue_url = f"http://{self.host}:{self.overlay_port}/music/queue"
            self.music_dock_url = f"http://{self.host}:{self.overlay_port}/music/dock"
            self.deck_overlay = f"{self.host}:{self.overlay_port}"
            self.deck_chat = f"{self.host}:{self.overlay_port}/chat"
            self.update_guidance()

        self.server_thread = threading.Thread(
            target=self.server.serve_forever,
            name="mopsyan-web-http",
            daemon=True,
        )
        self.server_thread.start()

        self.loop_thread = threading.Thread(
            target=self._loop,
            name="mopsyan-web-loop",
            daemon=True,
        )
        self.loop_thread.start()

        if open_browser_on_start:
            webbrowser.open_new(self.dashboard_url)

    def shutdown(self) -> None:
        self.stop_event.set()
        self.monitor.stop()

        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
            self.server = None

        if self.server_thread is not None and self.server_thread.is_alive():
            self.server_thread.join(timeout=1.0)
            self.server_thread = None

        if self.loop_thread is not None and self.loop_thread.is_alive():
            self.loop_thread.join(timeout=1.0)
            self.loop_thread = None

    def _loop(self) -> None:
        while not self.stop_event.wait(POLL_MS / 1000.0):
            self.tick()

    def refresh_devices(self) -> None:
        try:
            device_map, labels, default_label = list_input_devices()
        except Exception as error:
            with self.lock:
                self.device_map = {}
                self.device_labels = []
                self.device_label = ""
                self.status_text = f"Не удалось получить список микрофонов: {error}"
            return

        with self.lock:
            self.device_map = device_map
            self.device_labels = labels
            if labels and self.device_label not in device_map:
                self.device_label = default_label or labels[0]
            if not labels:
                self.device_label = ""
                self.status_text = "Микрофоны не найдены."

    def reload_media(self, *, show_errors: bool = True) -> list[str]:
        with self.lock:
            image_paths = {
                key: resolve_media_path(self.base_dir, value)
                for key, value in self.image_paths.items()
            }
            bg_path = resolve_media_path(self.base_dir, self.bg_path)
        errors = self.renderer.load_assets(image_paths, bg_path)
        with self.lock:
            self.media_errors = errors
            if errors and show_errors:
                joined = "; ".join(errors[:3])
                self.status_text = f"Есть проблемы с файлами: {joined}"
            self.scene_dirty = True
        return errors

    def scene_size(self) -> tuple[int, int]:
        with self.lock:
            width = parse_int(self.width_text, 1280, 320, 4096)
            height = parse_int(self.height_text, 720, 240, 4096)
            self.scene_size_cache = (width, height)
            return width, height

    def safe_scene_size(self) -> tuple[int, int]:
        return self.scene_size()

    def apply_stream_preset(self) -> None:
        with self.lock:
            pack = INTERNET_PRESET_PACKS.get(self.internet_pack, INTERNET_PRESET_PACKS["Ночной грид"])
            settings = pack["moments"].get(self.stream_moment, pack["moments"]["Геймплей"])
            self.scene_style = str(pack["scene_style"])
            self.chat_style = str(pack["chat_style"])
            self.anchor_label = str(settings["anchor"])
            self.scale_percent = float(settings["scale"])
            self.margin_x = float(settings["margin_x"])
            self.margin_y = float(settings["margin_y"])
            self.bg_mode = str(settings["bg_mode"])
            self.bg_color = str(settings["bg_color"])
            self.chat_side = str(settings["chat_side"])
            self.chat_width_percent = float(settings["chat_width"])
            self.preset_note = str(pack.get("note", ""))
            self.scene_dirty = True

    def refresh_chat_overlay_cache(self) -> None:
        with self.lock:
            raw = self.chat_url.strip()
            twitch_channel = extract_twitch_channel(raw) or ""
            self.chat_twitch_channel = twitch_channel
            width_percent = clamp(float(self.chat_width_percent), 24.0, 42.0)
            auth_username = self.chat_auth_user.strip()
            auth_token = self.chat_auth_token.strip()

            config = build_chat_config(
                style_name=self.chat_style.strip() or "Аврора",
                side_name=self.chat_side.strip() or "Справа",
                width_percent=width_percent,
                twitch_channel=twitch_channel,
                irc_username=auth_username,
                irc_token=auth_token,
                compact_mode=self.chat_compact_mode,
                reveal_only=self.chat_reveal_only,
            )

            self.chat_overlay_config_cache = config

            if twitch_channel:
                if auth_username and auth_token:
                    self.chat_text = (
                        f"Канал Twitch распознан: {twitch_channel}. Чат идет через авторизацию пользователя {auth_username}. Overlay появляется только когда приходят сообщения."
                    )
                    self.hero_chat = f"{twitch_channel} · автор"
                else:
                    self.chat_text = (
                        f"Канал Twitch распознан: {twitch_channel}. Чат может работать анонимно, но логин и токен дадут стабильнее результат. Overlay появляется только когда приходят сообщения."
                    )
                    self.hero_chat = f"{twitch_channel} · анон"
            elif raw:
                self.chat_text = "Пока поддерживается канал Twitch, ссылка на канал или ссылка на чат."
                self.hero_chat = "Адрес Twitch"
            else:
                self.chat_text = "Вставь канал Twitch, ссылку на канал или чат Twitch."
                self.hero_chat = "Чат не подключен"

            self.scene_dirty = True

    def refresh_tune2live_cache(self) -> None:
        with self.lock:
            self.tune_player_url = normalize_tune2live_url(self.tune_player_url)
            self.tune_queue_url = normalize_tune2live_url(self.tune_queue_url)
            self.tune_dock_url = normalize_tune2live_url(self.tune_dock_url)
            self.tune_auto_threshold = clamp(float(self.tune_auto_threshold), 1.0, 60.0)
            self.tune_auto_floor = clamp(float(self.tune_auto_floor), 0.0, 100.0)
            self.tune_auto_release_ms = int(clamp(float(self.tune_auto_release_ms), 200.0, 3000.0))
            if self.tune_auto_mode not in {"off", "dim", "hide"}:
                self.tune_auto_mode = "off"

            connected_parts: list[str] = []
            if self.tune_player_url:
                connected_parts.append("плеер")
            if self.tune_queue_url:
                connected_parts.append("очередь")
            if self.tune_dock_url:
                connected_parts.append("док-панель")

            auto_parts: list[str] = []
            if self.tune_auto_player:
                auto_parts.append("плеер")
            if self.tune_auto_queue:
                auto_parts.append("очередь")
            if self.tune_auto_dock:
                auto_parts.append("док-панель")

            mode_title = {
                "off": "авторежим выключен",
                "dim": "авторежим: приглушать виджет",
                "hide": "авторежим: скрывать при речи",
            }[self.tune_auto_mode]

            if connected_parts:
                auto_text = mode_title
                if self.tune_auto_mode != "off" and auto_parts:
                    auto_text += (
                        f" · порог {self.tune_auto_threshold:.0f}"
                        f" · возврат {self.tune_auto_release_ms / 1000:.1f} c"
                        f" · цели: {', '.join(auto_parts)}"
                    )
                self.tune_status = (
                    "Tune2Live подключен: "
                    + ", ".join(connected_parts)
                    + ". "
                    + auto_text
                    + ". Для OBS можешь использовать локальные маршруты ниже или прямые ссылки самого сервиса."
                )
            else:
                self.tune_status = (
                    "Tune2Live пока не подключен. Вставь ссылки на виджет плеера, очередь заказов или док-панель из сервиса Tune2Live."
                )

    def settings_payload(self) -> dict[str, object]:
        with self.lock:
            return {
                "presetLabel": self.preset_label,
                "internetPack": self.internet_pack,
                "streamMoment": self.stream_moment,
                "sceneStyle": self.scene_style,
                "chatStyle": self.chat_style,
                "chatSide": self.chat_side,
                "bgMode": self.bg_mode,
                "bgColor": self.bg_color,
                "anchorLabel": self.anchor_label,
                "scalePercent": round(self.scale_percent, 1),
                "marginX": round(self.margin_x, 1),
                "marginY": round(self.margin_y, 1),
                "chatWidthPercent": round(self.chat_width_percent, 1),
                "showSceneFrame": self.show_scene_frame,
                "showSceneLabel": self.show_scene_label,
                "showSceneRibbon": self.show_scene_ribbon,
                "chatCompactMode": self.chat_compact_mode,
                "chatRevealOnly": self.chat_reveal_only,
                "chatUrl": self.chat_url,
                "chatAuthUser": self.chat_auth_user,
                "chatAuthToken": self.chat_auth_token,
                "tunePlayerUrl": self.tune_player_url,
                "tuneQueueUrl": self.tune_queue_url,
                "tuneDockUrl": self.tune_dock_url,
                "tuneAutoMode": self.tune_auto_mode,
                "tuneAutoThreshold": round(self.tune_auto_threshold, 1),
                "tuneAutoFloor": round(self.tune_auto_floor, 1),
                "tuneAutoReleaseMs": int(self.tune_auto_release_ms),
                "tuneAutoPlayer": self.tune_auto_player,
                "tuneAutoQueue": self.tune_auto_queue,
                "tuneAutoDock": self.tune_auto_dock,
                "threshold": round(self.threshold, 1),
                "deviceLabel": self.device_label,
                "imageIdle": self.image_paths["idle"],
                "imageTalkA": self.image_paths["talk_a"],
                "imageTalkB": self.image_paths["talk_b"],
                "backgroundPath": self.bg_path,
            }

    def save_settings(self) -> None:
        payload = self.settings_payload()
        try:
            self.settings_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError:
            pass

    def load_settings(self) -> None:
        if not self.settings_path.exists():
            return

        try:
            payload = json.loads(self.settings_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return

        if isinstance(payload, dict):
            self.apply_updates(payload, save=False)

    def scene_params(self) -> SceneRenderParams:
        with self.lock:
            return SceneRenderParams(
                bg_mode=self.bg_mode,
                bg_color=self.bg_color,
                anchor_label=self.anchor_label,
                scale_percent=float(self.scale_percent),
                margin_x=float(self.margin_x),
                margin_y=float(self.margin_y),
                current_frame=self.current_frame,
                speaking_energy=self.speaking_energy(),
                scene_style=self.scene_style,
                preset_label=self.internet_pack,
                moment_label=self.stream_moment,
                show_scene_frame=self.show_scene_frame,
                show_scene_label=self.show_scene_label,
                show_scene_ribbon=self.show_scene_ribbon,
            )

    def speaking_energy(self) -> float:
        return max(0.0, min(1.0, self.last_level_value / 100.0))

    def build_scene(self, size: tuple[int, int]):
        return self.renderer.build_scene(size, self.scene_params())

    def render(self) -> None:
        scene_size = self.safe_scene_size()
        params = self.scene_params()
        clean_params = replace(params, show_scene_frame=False, show_scene_label=False, show_scene_ribbon=False)
        needs_styled_scene = params.show_scene_frame or params.show_scene_label or params.show_scene_ribbon

        clean_scene = self.renderer.build_scene(scene_size, clean_params)
        clean_overlay_png = self.renderer.image_to_png_bytes(clean_scene)
        if needs_styled_scene:
            styled_scene = self.renderer.build_scene(scene_size, params)
            overlay_png = self.renderer.image_to_png_bytes(styled_scene)
        else:
            overlay_png = clean_overlay_png

        with self.lock:
            chat_config = dict(self.chat_overlay_config_cache)

        self.overlay_state.update(
            overlay_html=build_overlay_html("/frame-styled.png"),
            clean_overlay_html=build_overlay_html("/frame.png"),
            chat_html=build_chat_overlay_html(chat_config),
            chat_config_json=json.dumps(chat_config, ensure_ascii=False),
            overlay_png=overlay_png,
            clean_overlay_png=clean_overlay_png,
        )

        with self.lock:
            self._overlay_png = overlay_png
            self._clean_overlay_png = clean_overlay_png
            self.frame_version += 1
            self.last_render_level = self.last_level_value
            self.last_visual_refresh = time.monotonic()
            self.scene_dirty = False

    def update_guidance(self) -> None:
        width, height = self.safe_scene_size()
        with self.lock:
            mode_label = {
                "transparent": "прозрачный фон",
                "image": "фоновая картинка",
                "color": "цветной фон",
            }.get(self.bg_mode, "сцена")

            if self.bg_mode == "transparent":
                capture_text = "Лучший режим для OBS сейчас: локальный адрес сцены с настоящей прозрачностью."
            elif self.bg_mode == "image":
                capture_text = "Сейчас сцена с картинкой-фоном. Можно использовать локальный адрес или захват окна."
            else:
                capture_text = "Сейчас сцена под цветной фон. Подойдет захват окна или адрес сцены."

            self.capture_hint = f"{capture_text} Активный момент: {self.stream_moment} · Пак: {self.internet_pack}."
            self.hero_scene = f"{self.internet_pack} · {self.stream_moment}"
            self.scene_meta = (
                f"Стиль: {self.scene_style} · Чат: {self.chat_style} · Режим: {mode_label} · Сцена: {width} x {height}"
            )
            help_lines = [
                "1. Добавь Browser Source с адресом сцены."
            ]
            help_lines += [
                f"2. Адрес сцены: {self.overlay_url or 'появится после старта'}",
                f"3. Адрес отдельного чата: {self.chat_browser_url or 'появится после старта'}",
                f"4. Размер сцены: {width} x {height}",
                "5. Для чистой прозрачности используй режим 'Прозрачный'.",
                "6. Для чата лучше использовать локальный /chat, а не прямую страницу Twitch.",
            ]

            next_step = 7
            if self.tune_player_url:
                help_lines.append(f"{next_step}. Tune2Live плеер для OBS: {self.music_player_url or 'появится после старта'}")
                next_step += 1
            if self.tune_queue_url:
                help_lines.append(f"{next_step}. Tune2Live очередь для OBS: {self.music_queue_url or 'появится после старта'}")
                next_step += 1
            if self.tune_dock_url:
                help_lines.append(f"{next_step}. Tune2Live док-панель: {self.music_dock_url or 'появится после старта'}")
                next_step += 1
            if self.tune_auto_mode != "off":
                targets: list[str] = []
                if self.tune_auto_player:
                    targets.append("плеер")
                if self.tune_auto_queue:
                    targets.append("очередь")
                if self.tune_auto_dock:
                    targets.append("док-панель")
                if targets:
                    help_lines.append(
                        f"{next_step}. Автореакция Tune2Live: режим {self.tune_auto_mode}, порог {self.tune_auto_threshold:.0f}, возврат {self.tune_auto_release_ms / 1000:.1f} c, цели: {', '.join(targets)}"
                    )

            self.obs_help = "\n".join(help_lines)

    def is_speaking(self, level: float) -> bool:
        now = time.monotonic()
        if level >= float(self.threshold):
            self.last_voice = now
            return True
        return (now - self.last_voice) <= HANG_SECONDS

    def tick(self) -> None:
        level, monitor_status = self.monitor.snapshot()

        with self.lock:
            self.last_level_value = level
            if self.monitor.running:
                self.hero_signal = f"МИК {level:.0f}%"
            else:
                self.hero_signal = "МИК ВЫКЛ"

            if monitor_status:
                self.status_text = f"Статус микрофона: {monitor_status}"

            changed = False
            if not self.monitor.running:
                if self.current_frame != "idle":
                    self.current_frame = "idle"
                    self.talk_frame = "talk_a"
                    changed = True
            else:
                if self.is_speaking(level):
                    now = time.monotonic()
                    if now - self.last_anim >= 0.14:
                        self.talk_frame = "talk_b" if self.talk_frame == "talk_a" else "talk_a"
                        self.last_anim = now
                    if self.current_frame != self.talk_frame:
                        self.current_frame = self.talk_frame
                        changed = True
                elif self.current_frame != "idle":
                    self.current_frame = "idle"
                    self.talk_frame = "talk_a"
                    changed = True

            needs_render = changed or self.scene_dirty
            if not needs_render and self.monitor.running:
                level_delta = abs(level - self.last_render_level)
                if (time.monotonic() - self.last_visual_refresh) >= 0.06 and (
                    level_delta >= 1.6 or self.current_frame != "idle"
                ):
                    needs_render = True

        if needs_render:
            self.render()

    def start_audio(self, device_label: str | None = None) -> None:
        if device_label:
            with self.lock:
                self.device_label = device_label

        with self.lock:
            selected = self.device_map.get(self.device_label)

        if selected is None:
            raise RuntimeError("Сначала выбери микрофон.")

        self.monitor.start(selected)
        with self.lock:
            self.last_voice = time.monotonic()
            self.status_text = f"Микрофон активен: {selected.name}"
            self.hero_signal = "МИК АКТИВЕН"
            self.scene_dirty = True

    def stop_audio(self) -> None:
        self.monitor.stop()
        with self.lock:
            self.status_text = "Микрофон остановлен."
            self.hero_signal = "МИК ВЫКЛ"
            if self.current_frame != "idle":
                self.current_frame = "idle"
                self.talk_frame = "talk_a"
            self.scene_dirty = True

    def apply_updates(self, payload: dict[str, object], *, save: bool = True) -> None:
        if not isinstance(payload, dict):
            return

        media_changed = False
        recalc_guidance = False
        tune_validation_error = ""

        with self.lock:
            if "presetLabel" in payload and str(payload["presetLabel"]) in SCENE_PRESETS:
                self.preset_label = str(payload["presetLabel"])
                width, height = SCENE_PRESETS[self.preset_label]
                self.width_text = str(width)
                self.height_text = str(height)
                self.scene_size_cache = (width, height)
                recalc_guidance = True

            if "internetPack" in payload and str(payload["internetPack"]) in INTERNET_PRESET_OPTIONS:
                self.internet_pack = str(payload["internetPack"])
            if "streamMoment" in payload and str(payload["streamMoment"]) in STREAM_MOMENT_OPTIONS:
                self.stream_moment = str(payload["streamMoment"])

        if "internetPack" in payload or "streamMoment" in payload:
            self.apply_stream_preset()
            recalc_guidance = True

        with self.lock:
            if "sceneStyle" in payload and str(payload["sceneStyle"]) in SCENE_STYLE_OPTIONS:
                self.scene_style = str(payload["sceneStyle"])
                recalc_guidance = True
            if "chatStyle" in payload and str(payload["chatStyle"]) in CHAT_STYLE_OPTIONS:
                self.chat_style = str(payload["chatStyle"])
                recalc_guidance = True
            if "chatSide" in payload and str(payload["chatSide"]) in CHAT_SIDE_OPTIONS:
                self.chat_side = str(payload["chatSide"])
            if "bgMode" in payload and str(payload["bgMode"]) in {"transparent", "color", "image"}:
                self.bg_mode = str(payload["bgMode"])
                recalc_guidance = True
            if "bgColor" in payload:
                self.bg_color = str(payload["bgColor"]).strip() or self.bg_color
                recalc_guidance = True
            if "anchorLabel" in payload:
                self.anchor_label = str(payload["anchorLabel"]).strip() or self.anchor_label
            if "scalePercent" in payload:
                self.scale_percent = clamp(float(payload["scalePercent"]), 18.0, 90.0)
            if "marginX" in payload:
                self.margin_x = clamp(float(payload["marginX"]), 0.0, 280.0)
            if "marginY" in payload:
                self.margin_y = clamp(float(payload["marginY"]), 0.0, 220.0)
            if "chatWidthPercent" in payload:
                self.chat_width_percent = clamp(float(payload["chatWidthPercent"]), 24.0, 42.0)
            if "showSceneFrame" in payload:
                self.show_scene_frame = coerce_bool(payload["showSceneFrame"])
            if "showSceneLabel" in payload:
                self.show_scene_label = coerce_bool(payload["showSceneLabel"])
            if "showSceneRibbon" in payload:
                self.show_scene_ribbon = coerce_bool(payload["showSceneRibbon"])
            if "chatCompactMode" in payload:
                self.chat_compact_mode = coerce_bool(payload["chatCompactMode"])
            if "chatRevealOnly" in payload:
                self.chat_reveal_only = coerce_bool(payload["chatRevealOnly"])
            if "chatUrl" in payload:
                self.chat_url = str(payload["chatUrl"]).strip()
            if "chatAuthUser" in payload:
                self.chat_auth_user = str(payload["chatAuthUser"]).strip()
            if "chatAuthToken" in payload:
                self.chat_auth_token = str(payload["chatAuthToken"]).strip()
            if "tunePlayerUrl" in payload:
                raw = str(payload["tunePlayerUrl"]).strip()
                normalized = normalize_tune2live_url(raw)
                if raw and not normalized:
                    tune_validation_error = "Для Tune2Live поддерживаются только прямые ссылки tune2live.com."
                self.tune_player_url = normalized
            if "tuneQueueUrl" in payload:
                raw = str(payload["tuneQueueUrl"]).strip()
                normalized = normalize_tune2live_url(raw)
                if raw and not normalized:
                    tune_validation_error = "Для Tune2Live поддерживаются только прямые ссылки tune2live.com."
                self.tune_queue_url = normalized
            if "tuneDockUrl" in payload:
                raw = str(payload["tuneDockUrl"]).strip()
                normalized = normalize_tune2live_url(raw)
                if raw and not normalized:
                    tune_validation_error = "Для Tune2Live поддерживаются только прямые ссылки tune2live.com."
                self.tune_dock_url = normalized
            if "tuneAutoMode" in payload and str(payload["tuneAutoMode"]) in {"off", "dim", "hide"}:
                self.tune_auto_mode = str(payload["tuneAutoMode"])
            if "tuneAutoThreshold" in payload:
                self.tune_auto_threshold = clamp(float(payload["tuneAutoThreshold"]), 1.0, 60.0)
            if "tuneAutoFloor" in payload:
                self.tune_auto_floor = clamp(float(payload["tuneAutoFloor"]), 0.0, 100.0)
            if "tuneAutoReleaseMs" in payload:
                self.tune_auto_release_ms = int(clamp(float(payload["tuneAutoReleaseMs"]), 200.0, 3000.0))
            if "tuneAutoPlayer" in payload:
                self.tune_auto_player = coerce_bool(payload["tuneAutoPlayer"])
            if "tuneAutoQueue" in payload:
                self.tune_auto_queue = coerce_bool(payload["tuneAutoQueue"])
            if "tuneAutoDock" in payload:
                self.tune_auto_dock = coerce_bool(payload["tuneAutoDock"])
            if "threshold" in payload:
                self.threshold = clamp(float(payload["threshold"]), 1.0, 50.0)
            if "deviceLabel" in payload and str(payload["deviceLabel"]) in self.device_map:
                self.device_label = str(payload["deviceLabel"])
            if "imageIdle" in payload:
                self.image_paths["idle"] = portable_media_path(self.base_dir, str(payload["imageIdle"]))
                media_changed = True
            if "imageTalkA" in payload:
                self.image_paths["talk_a"] = portable_media_path(self.base_dir, str(payload["imageTalkA"]))
                media_changed = True
            if "imageTalkB" in payload:
                self.image_paths["talk_b"] = portable_media_path(self.base_dir, str(payload["imageTalkB"]))
                media_changed = True
            if "backgroundPath" in payload:
                self.bg_path = portable_media_path(self.base_dir, str(payload["backgroundPath"]))
                media_changed = True
            self.scene_dirty = True

        self.refresh_chat_overlay_cache()
        self.refresh_tune2live_cache()
        if tune_validation_error:
            with self.lock:
                self.tune_status = tune_validation_error
        if media_changed:
            self.reload_media(show_errors=True)
        if recalc_guidance or "chatUrl" in payload or "chatStyle" in payload or "bgMode" in payload or "tunePlayerUrl" in payload or "tuneQueueUrl" in payload or "tuneDockUrl" in payload or "tuneAutoMode" in payload or "tuneAutoThreshold" in payload or "tuneAutoFloor" in payload or "tuneAutoReleaseMs" in payload or "tuneAutoPlayer" in payload or "tuneAutoQueue" in payload or "tuneAutoDock" in payload:
            self.update_guidance()
        if save:
            self.save_settings()

    def state_snapshot(self) -> dict[str, object]:
        width, height = self.safe_scene_size()
        with self.lock:
            return {
                "appTitle": APP_TITLE,
                "dashboardUrl": self.dashboard_url if self.overlay_port else "",
                "sessionId": self.session_id,
                "frameVersion": self.frame_version,
                "routes": {
                    "overlay": self.overlay_url,
                    "chat": self.chat_browser_url,
                    "musicPlayer": self.music_player_url,
                    "musicQueue": self.music_queue_url,
                    "musicDock": self.music_dock_url,
                    "musicPlayerDirect": self.tune_player_url,
                    "musicQueueDirect": self.tune_queue_url,
                    "musicDockDirect": self.tune_dock_url,
                    "tuneHome": "https://tune2live.com/ru",
                    "tuneDashboard": "https://tune2live.com/ru/dashboard",
                    "overlayShort": self.deck_overlay,
                    "chatShort": self.deck_chat,
                },
                "hero": {
                    "scene": self.hero_scene,
                    "chat": self.hero_chat,
                    "signal": self.hero_signal,
                },
                "status": {
                    "captureHint": self.capture_hint,
                    "sceneMeta": self.scene_meta,
                    "audio": self.status_text,
                    "chat": self.chat_text,
                    "tune2live": self.tune_status,
                    "help": self.obs_help,
                    "mediaErrors": list(self.media_errors),
                },
                "preview": {
                    "width": width,
                    "height": height,
                    "mode": self.bg_mode,
                },
                "devices": {
                    "available": list(self.device_labels),
                    "selected": self.device_label,
                    "running": self.monitor.running,
                    "level": round(self.last_level_value, 1),
                },
                "settings": {
                    "presetLabel": self.preset_label,
                    "sceneStyle": self.scene_style,
                    "sceneWidth": width,
                    "sceneHeight": height,
                    "bgMode": self.bg_mode,
                    "bgColor": self.bg_color,
                    "anchorLabel": self.anchor_label,
                    "scalePercent": round(self.scale_percent, 1),
                    "marginX": round(self.margin_x, 1),
                    "marginY": round(self.margin_y, 1),
                    "showSceneFrame": self.show_scene_frame,
                    "showSceneLabel": self.show_scene_label,
                    "showSceneRibbon": self.show_scene_ribbon,
                    "internetPack": self.internet_pack,
                    "streamMoment": self.stream_moment,
                    "presetNote": self.preset_note,
                    "chatStyle": self.chat_style,
                    "chatSide": self.chat_side,
                    "chatWidthPercent": round(self.chat_width_percent, 1),
                    "chatCompactMode": self.chat_compact_mode,
                    "chatRevealOnly": self.chat_reveal_only,
                    "chatUrl": self.chat_url,
                    "chatAuthUser": self.chat_auth_user,
                    "chatAuthToken": self.chat_auth_token,
                    "tunePlayerUrl": self.tune_player_url,
                    "tuneQueueUrl": self.tune_queue_url,
                    "tuneDockUrl": self.tune_dock_url,
                    "tuneAutoMode": self.tune_auto_mode,
                    "tuneAutoThreshold": round(self.tune_auto_threshold, 1),
                    "tuneAutoFloor": round(self.tune_auto_floor, 1),
                    "tuneAutoReleaseMs": int(self.tune_auto_release_ms),
                    "tuneAutoPlayer": self.tune_auto_player,
                    "tuneAutoQueue": self.tune_auto_queue,
                    "tuneAutoDock": self.tune_auto_dock,
                    "threshold": round(self.threshold, 1),
                    "imageIdle": self.image_paths["idle"],
                    "imageTalkA": self.image_paths["talk_a"],
                    "imageTalkB": self.image_paths["talk_b"],
                    "backgroundPath": self.bg_path,
                },
                "choices": {
                    "presets": list(SCENE_PRESETS.keys()),
                    "sceneStyles": list(SCENE_STYLE_OPTIONS),
                    "packs": list(INTERNET_PRESET_OPTIONS),
                    "moments": list(STREAM_MOMENT_OPTIONS),
                    "chatStyles": list(CHAT_STYLE_OPTIONS),
                    "chatSides": list(CHAT_SIDE_OPTIONS),
                    "anchors": ["Справа снизу", "Слева снизу", "По центру"],
                },
            }

    def event_snapshot(self) -> dict[str, object]:
        with self.lock:
            return {
                "sessionId": self.session_id,
                "frameVersion": self.frame_version,
                "audioLevel": round(self.last_level_value, 1),
                "heroSignal": self.hero_signal,
                "monitorRunning": self.monitor.running,
            }

    def static_response(self, path: str) -> StaticResponse | None:
        if path == "/":
            file_path = self.web_dir / "index.html"
        elif path == "/styles.css":
            file_path = self.web_dir / "styles.css"
        elif path == "/app.js":
            file_path = self.web_dir / "app.js"
        elif path == "/site.webmanifest":
            file_path = self.web_dir / "site.webmanifest"
        elif path == "/favicon.ico":
            file_path = self.base_dir / "z_icon.ico"
        elif path == "/z_icon.png":
            file_path = self.base_dir / "z_icon.png"
        elif path.startswith("/assets/"):
            file_path = (self.base_dir / path.lstrip("/")).resolve()
            if self.assets_dir.resolve() not in file_path.parents and file_path != self.assets_dir.resolve():
                return None
        else:
            return None

        if not file_path.exists() or not file_path.is_file():
            return None

        content_type, _ = mimetypes.guess_type(str(file_path))
        return StaticResponse(
            content=file_path.read_bytes(),
            content_type=content_type or "application/octet-stream",
        )


class WebHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True

    def __init__(self, server_address: tuple[str, int], app: WebRuntime) -> None:
        super().__init__(server_address, WebRequestHandler)
        self.app = app


class WebRequestHandler(BaseHTTPRequestHandler):
    server: WebHTTPServer

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        overlay_html, clean_overlay_html, chat_html, chat_config_json, overlay_png, clean_overlay_png = self.server.app.overlay_state.snapshot()

        if path in {"/", "/styles.css", "/app.js", "/site.webmanifest", "/favicon.ico", "/z_icon.png"} or path.startswith("/assets/"):
            response = self.server.app.static_response(path)
            if response is None:
                self.send_error(404)
                return
            self._send_bytes(response.content, response.content_type)
            return

        if path == "/api/state":
            if "live=1" in parsed.query:
                self._send_json(self.server.app.event_snapshot())
            else:
                self._send_json(self.server.app.state_snapshot())
            return

        if path == "/api/events":
            self._stream_events()
            return

        if path == "/overlay":
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
            if "config=1" in parsed.query:
                self._send_bytes(chat_config_json.encode("utf-8"), "application/json; charset=utf-8")
                return
            self._send_bytes(chat_html.encode("utf-8"), "text/html; charset=utf-8")
            return

        if path == "/music/player":
            self._send_bytes(
                build_tune2live_embed_html("Tune2Live · плеер", self.server.app.tune_player_url, "player").encode("utf-8"),
                "text/html; charset=utf-8",
            )
            return

        if path == "/music/queue":
            self._send_bytes(
                build_tune2live_embed_html("Tune2Live · очередь", self.server.app.tune_queue_url, "queue").encode("utf-8"),
                "text/html; charset=utf-8",
            )
            return

        if path == "/music/dock":
            self._send_bytes(
                build_tune2live_embed_html("Tune2Live · док-панель", self.server.app.tune_dock_url, "dock").encode("utf-8"),
                "text/html; charset=utf-8",
            )
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

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        payload = self._read_json()

        try:
            if path == "/api/settings":
                self.server.app.apply_updates(payload)
                self._send_json(self.server.app.state_snapshot())
                return

            if path == "/api/audio/start":
                self.server.app.start_audio(str(payload.get("deviceLabel", "")) or None)
                self._send_json(self.server.app.state_snapshot())
                return

            if path == "/api/audio/stop":
                self.server.app.stop_audio()
                self._send_json(self.server.app.state_snapshot())
                return

            if path == "/api/devices/refresh":
                self.server.app.refresh_devices()
                self._send_json(self.server.app.state_snapshot())
                return
        except Exception as error:
            self._send_json({"error": str(error)}, status=400)
            return

        self.send_error(404)

    def _read_json(self) -> dict[str, object]:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        if not raw:
            return {}
        try:
            data = json.loads(raw.decode("utf-8"))
        except Exception:
            return {}
        return data if isinstance(data, dict) else {}

    def _send_json(self, payload: dict[str, object], *, status: int = 200) -> None:
        content = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self._send_bytes(content, "application/json; charset=utf-8", status=status)

    def _stream_events(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header("Connection", "keep-alive")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

        last_frame_version = -1
        last_signal = ""
        last_level_bucket = -1
        last_ping = time.monotonic()

        try:
            self._write_event("hello", self.server.app.event_snapshot())
            while not self.server.app.stop_event.wait(0.05):
                snapshot = self.server.app.event_snapshot()
                frame_version = int(snapshot["frameVersion"])
                signal = str(snapshot["heroSignal"])
                level_bucket = int(round(float(snapshot["audioLevel"])))

                if frame_version != last_frame_version:
                    last_frame_version = frame_version
                    self._write_event(
                        "frame",
                        {
                            "sessionId": snapshot["sessionId"],
                            "frameVersion": frame_version,
                        },
                    )

                if signal != last_signal or level_bucket != last_level_bucket:
                    last_signal = signal
                    last_level_bucket = level_bucket
                    self._write_event(
                        "signal",
                        {
                            "audioLevel": level_bucket,
                            "heroSignal": signal,
                            "monitorRunning": bool(snapshot["monitorRunning"]),
                        },
                    )

                now = time.monotonic()
                if now - last_ping >= 12.0:
                    last_ping = now
                    self._write_event("ping", {"t": int(time.time())})
        except (ConnectionError, OSError):
            return

    def _write_event(self, event_name: str, payload: dict[str, object]) -> None:
        data = json.dumps(payload, ensure_ascii=False)
        chunk = f"event: {event_name}\ndata: {data}\n\n".encode("utf-8")
        self.wfile.write(chunk)
        self.wfile.flush()

    def _send_bytes(self, content: bytes, content_type: str, *, status: int = 200) -> None:
        self.send_response(status)
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
