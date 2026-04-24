from __future__ import annotations

import ctypes
import json
import os
import threading
import time
import webbrowser
from pathlib import Path

import tkinter as tk
from PIL import Image, ImageColor, ImageDraw, ImageFont, ImageOps, ImageTk
from tkinter import colorchooser, filedialog, messagebox, scrolledtext, ttk

from audio_monitor import AudioMonitor, InputDevice, list_input_devices
from chat_overlay import build_chat_config, build_chat_overlay_html, build_overlay_html
from constants import (
    ANCHORS,
    APP_TITLE,
    CHAT_PREVIEW_FALLBACK,
    CHAT_SIDE_OPTIONS,
    CHAT_STYLE_OPTIONS,
    DEFAULT_COLORS,
    FILE_TYPES,
    HANG_SECONDS,
    INTERNET_PRESET_OPTIONS,
    INTERNET_PRESET_PACKS,
    OVERLAY_PORT_START,
    POLL_MS,
    PREVIEW_FALLBACK,
    SCENE_PRESETS,
    SCENE_STYLE_OPTIONS,
    STREAM_MOMENT_OPTIONS,
)
from obs_window import OBSWindow
from overlay_server import OverlayHTTPServer, OverlayState
from scene_renderer import SceneRenderParams, SceneRenderer
from utils import clamp, default_image_path, extract_twitch_channel, normalize_url, parse_int


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.base_dir = Path(__file__).resolve().parent
        self.ui_assets_dir = self.base_dir / "assets" / "ui"
        self.monitor = AudioMonitor()
        self.renderer = SceneRenderer()
        self.overlay_state = OverlayState()

        self.device_map: dict[str, InputDevice] = {}
        self.obs_win: OBSWindow | None = None
        self.preview_photo: ImageTk.PhotoImage | None = None
        self.chat_preview_photo: ImageTk.PhotoImage | None = None
        self.brand_icon_photo: ImageTk.PhotoImage | None = None
        self.window_icon_photo: ImageTk.PhotoImage | None = None
        self.ui_header_source = None
        self.ui_sidebar_source = None
        self.ui_wallpaper_source = None
        self.ui_header_photo: ImageTk.PhotoImage | None = None
        self.ui_sidebar_photo: ImageTk.PhotoImage | None = None
        self.ui_wallpaper_photo: ImageTk.PhotoImage | None = None
        self.work_art_photo: ImageTk.PhotoImage | None = None
        self.preview_art_photo: ImageTk.PhotoImage | None = None
        self.overlay_server: OverlayHTTPServer | None = None
        self.overlay_thread: threading.Thread | None = None
        self.overlay_port = 0
        self._overlay_png = b""
        self._font_cache: dict[tuple[int, bool], ImageFont.ImageFont] = {}
        self._render_after_id: str | None = None
        self._layout_after_id: str | None = None
        self._resize_cooldown_until = 0.0
        self._ui_texture_sizes: dict[str, tuple[int, int] | None] = {
            "shell": None,
            "hero": None,
            "rail": None,
            "work": None,
            "preview": None,
        }

        self.scene_size_cache = SCENE_PRESETS["1280 x 720 (HD)"]
        self.current_frame = "idle"
        self.talk_frame = "talk_a"
        self.last_voice = 0.0
        self.last_anim = 0.0
        self.last_level_value = 0.0
        self.last_render_level = 0.0
        self.last_visual_refresh = 0.0
        self.last_chat_preview_refresh = 0.0
        self.scene_dirty = True
        self.chat_preview_dirty = True
        self.chat_overlay_config_cache: dict[str, object] = {}
        self.chat_twitch_channel = ""

        self.title(APP_TITLE)
        self._set_initial_geometry()
        self.minsize(1180, 720)
        self.configure(bg="#070A11")
        self.icon_path = self.base_dir / "z_icon.png"
        self.icon_ico_path = self.base_dir / "z_icon.ico"

        self.image_vars = {
            "idle": tk.StringVar(value=default_image_path(self.base_dir, "1.png")),
            "talk_a": tk.StringVar(value=default_image_path(self.base_dir, "2.png")),
            "talk_b": tk.StringVar(value=default_image_path(self.base_dir, "3.png")),
        }
        self.bg_path_var = tk.StringVar()
        self.device_var = tk.StringVar()
        self.threshold_var = tk.DoubleVar(value=12.0)
        self.threshold_text = tk.StringVar(value="12")
        self.level_text = tk.StringVar(value="0 / 100")
        self.status_var = tk.StringVar(value="Микрофон пока остановлен.")
        self.obs_text = tk.StringVar(value="OBS-окно еще не открыто.")
        self.overlay_url_var = tk.StringVar(value="")
        self.capture_hint_var = tk.StringVar(value="Лучший способ вывода подберем автоматически.")
        self.scene_meta_var = tk.StringVar(value="Сцена готовится.")
        self.chat_url_var = tk.StringVar()
        self.chat_browser_url_var = tk.StringVar(value="")
        self.chat_text = tk.StringVar(value="Вставь ссылку на чат Twitch или канал.")
        self.bg_mode_var = tk.StringVar(value="transparent")
        self.bg_color_var = tk.StringVar(value="#00FF66")
        self.preset_var = tk.StringVar(value="1280 x 720 (HD)")
        self.scene_style_var = tk.StringVar(value="Кибер-пульс")
        self.width_var = tk.StringVar(value="1280")
        self.height_var = tk.StringVar(value="720")
        self.anchor_var = tk.StringVar(value="Справа снизу")
        self.scale_var = tk.DoubleVar(value=58.0)
        self.scale_text = tk.StringVar(value="58%")
        self.margin_x_var = tk.DoubleVar(value=26.0)
        self.margin_x_text = tk.StringVar(value="26 px")
        self.margin_y_var = tk.DoubleVar(value=18.0)
        self.margin_y_text = tk.StringVar(value="18 px")
        self.borderless_var = tk.BooleanVar(value=False)
        self.topmost_var = tk.BooleanVar(value=False)

        self.chat_style_var = tk.StringVar(value="Аврора")
        self.chat_side_var = tk.StringVar(value="Справа")
        self.chat_width_var = tk.DoubleVar(value=31.0)
        self.chat_width_text = tk.StringVar(value="31%")
        self.chat_auth_user_var = tk.StringVar()
        self.chat_auth_token_var = tk.StringVar()
        self.internet_pack_var = tk.StringVar(value="Ночной грид")
        self.stream_moment_var = tk.StringVar(value="Геймплей")
        self.preset_note_var = tk.StringVar(value="")

        self.control_tabs = None
        self.control_pages: dict[str, tk.Frame] = {}
        self.control_nav_buttons: dict[str, tk.Button] = {}
        self.combo_widgets: list[ttk.Combobox] = []
        self.active_control_page = "studio"
        self.control_scroll_canvas: tk.Canvas | None = None
        self.control_scroll_inner: tk.Frame | None = None
        self.control_scroll_window_id: int | None = None
        self.control_scrollbar: ttk.Scrollbar | None = None
        self.chat_tab_page: tk.Frame | None = None
        self.help_tab: tk.Frame | None = None
        self.help_textbox: scrolledtext.ScrolledText | None = None
        self.chat_entry: tk.Entry | None = None
        self.overlay_entry: tk.Entry | None = None
        self.stage_status_frame: tk.Frame | None = None
        self.chat_preview_host: tk.Frame | None = None
        self.chat_preview: tk.Label | None = None
        self.voice_canvas: tk.Canvas | None = None
        self.hero_art_label: tk.Label | None = None
        self.rail_art_label: tk.Label | None = None
        self.shell_art_label: tk.Label | None = None
        self.work_art_label: tk.Label | None = None
        self.preview_art_label: tk.Label | None = None
        self.workbench_frame: tk.Frame | None = None
        self.preview_panel: tk.Frame | None = None
        self.preview_header: tk.Frame | None = None
        self.deck_stats_frame: tk.Frame | None = None
        self.deck_overlay_chip: tk.Frame | None = None
        self.deck_chat_chip: tk.Frame | None = None
        self.bottom_cards_frame: tk.Frame | None = None
        self.overlay_route_card: tk.Frame | None = None
        self.chat_route_card: tk.Frame | None = None
        self.preview_host: tk.Frame | None = None
        self.preview: tk.Label | None = None
        self.hero_scene_var = tk.StringVar(value=self.scene_style_var.get())
        self.hero_chat_var = tk.StringVar(value="Чат не подключен")
        self.hero_signal_var = tk.StringVar(value="МИК ВЫКЛ")
        self.deck_overlay_var = tk.StringVar(value="сцена недоступна")
        self.deck_chat_var = tk.StringVar(value="чат недоступен")
        self.section_title_var = tk.StringVar(value="Студия персонажа")
        self.section_subtitle_var = tk.StringVar(value="Собери кадры, подключи микрофон и проверь анимацию персонажа.")
        self.preview_kicker_var = tk.StringVar(value="Панель просмотра")
        self.preview_title_var = tk.StringVar(value="Предпросмотр проекта")
        self.section_subtitle_label: tk.Label | None = None
        self.preview_title_label: tk.Label | None = None
        self.capture_hint_label: tk.Label | None = None
        self.scene_meta_label: tk.Label | None = None
        self.colors = dict(DEFAULT_COLORS)
        self.fonts = {
            "body": ("Segoe UI Variable Small", 10),
            "body_small": ("Segoe UI Variable Small", 9),
            "section": ("Bahnschrift SemiBold", 14),
            "section_large": ("Bahnschrift SemiBold", 18),
            "display": ("Bahnschrift SemiBold", 22),
            "display_large": ("Bahnschrift SemiBold", 26),
            "label": ("Bahnschrift SemiBold", 10),
            "button": ("Bahnschrift SemiBold", 10),
            "button_small": ("Bahnschrift SemiBold", 9),
            "eyebrow": ("Bahnschrift SemiBold", 9),
            "chip_label": ("Bahnschrift SemiBold", 8),
            "chip_value": ("Bahnschrift SemiBold", 13),
            "mono": ("Consolas", 10),
        }

        self._theme()
        self._load_brand_assets()
        self._load_ui_textures()
        self._build()

        self.chat_url_var.trace_add("write", self._on_chat_url_change)
        for variable in (
            self.width_var,
            self.height_var,
            self.bg_color_var,
            self.bg_mode_var,
            self.anchor_var,
            self.scene_style_var,
            self.chat_style_var,
            self.chat_side_var,
            self.chat_width_var,
            self.chat_auth_user_var,
            self.chat_auth_token_var,
        ):
            variable.trace_add("write", self._on_setting_changed)

        self._update_preset_note()
        self._apply_stream_preset()
        self._refresh_chat_overlay_cache()
        self._start_overlay_server()
        self._update_guidance()
        self._refresh_devices()
        self._reload_media(False)
        self._render()

        self.after(90, self._apply_window_chrome)
        self.after(450, self._autostart)
        self.after(POLL_MS, self._tick)
        self.bind("<Configure>", self._on_window_configure)
        self.protocol("WM_DELETE_WINDOW", self._close)

    def _theme(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")

        style.configure(".", font=self.fonts["body"])
        style.configure("TFrame", background=self.colors["bg"])
        style.configure("Card.TFrame", background=self.colors["card"])
        style.configure("Alt.TFrame", background=self.colors["card2"])
        style.configure("HeroCard.TFrame", background=self.colors["card3"])

        style.configure("TLabel", background=self.colors["card"], foreground=self.colors["text"])
        style.configure("Muted.TLabel", background=self.colors["card"], foreground=self.colors["muted"])
        style.configure("Success.TLabel", background=self.colors["card"], foreground=self.colors["mint"])
        style.configure(
            "Head.TLabel",
            background=self.colors["card"],
            foreground=self.colors["gold"],
            font=self.fonts["section"],
        )
        style.configure(
            "CardTitle.TLabel",
            background=self.colors["card"],
            foreground=self.colors["text"],
            font=self.fonts["section"],
        )
        style.configure(
            "HeroCardTitle.TLabel",
            background=self.colors["card3"],
            foreground=self.colors["text"],
            font=self.fonts["section_large"],
        )
        style.configure(
            "HeroCardSub.TLabel",
            background=self.colors["card3"],
            foreground=self.colors["muted"],
            font=self.fonts["body"],
        )

        style.configure(
            "Accent.TButton",
            background=self.colors["accent"],
            foreground="#061019",
            padding=(18, 11),
            font=self.fonts["button"],
            borderwidth=0,
            focusthickness=0,
        )
        style.map(
            "Accent.TButton",
            background=[("active", self.colors["accent2"])],
            foreground=[("active", "#081019")],
        )

        style.configure(
            "TButton",
            background=self.colors["card2"],
            foreground=self.colors["text"],
            padding=(12, 9),
            bordercolor=self.colors["border"],
            lightcolor=self.colors["card2"],
            darkcolor=self.colors["card2"],
        )
        style.map("TButton", background=[("active", self.colors["border"])])

        style.configure(
            "TEntry",
            fieldbackground=self.colors["input"],
            background=self.colors["input"],
            foreground=self.colors["text"],
            insertcolor=self.colors["text"],
            padding=7,
        )
        style.configure(
            "TCombobox",
            fieldbackground=self.colors["input"],
            background=self.colors["input"],
            foreground=self.colors["text"],
            arrowcolor=self.colors["text"],
            bordercolor=self.colors["border"],
            lightcolor=self.colors["input"],
            darkcolor=self.colors["input"],
            padding=6,
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", self.colors["input"])],
            selectforeground=[("readonly", self.colors["text"])],
            selectbackground=[("readonly", self.colors["input"])],
        )
        self.option_add("*Listbox.background", self.colors["card2"])
        self.option_add("*Listbox.foreground", self.colors["text"])
        self.option_add("*Listbox.selectBackground", self.colors["accent"])
        self.option_add("*Listbox.selectForeground", "#081019")
        self.option_add("*Listbox.highlightThickness", 0)
        self.option_add("*Listbox.borderWidth", 0)
        self.option_add("*Listbox.font", "{Segoe UI} 10")

        style.configure("TRadiobutton", background=self.colors["card"], foreground=self.colors["text"])
        style.configure("TCheckbutton", background=self.colors["card"], foreground=self.colors["text"])
        style.configure("Horizontal.TProgressbar", troughcolor=self.colors["input"], background=self.colors["accent"])

        style.configure("TLabelframe", background=self.colors["card"], foreground=self.colors["gold"])
        style.configure(
            "TLabelframe.Label",
            background=self.colors["card"],
            foreground=self.colors["gold"],
            font=self.fonts["section"],
        )

        style.configure("Studio.TNotebook", background=self.colors["card"], borderwidth=0)
        style.configure(
            "Studio.TNotebook.Tab",
            background=self.colors["card2"],
            foreground=self.colors["muted"],
            padding=(16, 10),
            borderwidth=0,
            font=self.fonts["button_small"],
        )
        style.map(
            "Studio.TNotebook.Tab",
            background=[("selected", self.colors["card3"])],
            foreground=[("selected", self.colors["text"])],
        )

        style.configure(
            "Dark.Vertical.TScrollbar",
            background=self.colors["card3"],
            troughcolor=self.colors["card"],
            bordercolor=self.colors["border"],
            arrowcolor=self.colors["muted"],
            lightcolor=self.colors["card3"],
            darkcolor=self.colors["card3"],
            gripcount=0,
            relief="flat",
            width=15,
        )
        style.map(
            "Dark.Vertical.TScrollbar",
            background=[("active", self.colors["accent"])],
            arrowcolor=[("active", "#081019")],
        )

    def _set_initial_geometry(self) -> None:
        screen_w = max(1280, int(self.winfo_screenwidth()))
        screen_h = max(760, int(self.winfo_screenheight()))
        width = min(int(screen_w * 0.94), screen_w - 28)
        height = min(int(screen_h * 0.90), screen_h - 64)
        width = max(1320, width)
        height = max(760, height)
        x = max(0, (screen_w - width) // 2)
        y = max(0, (screen_h - height) // 2 - 12)
        self.geometry(f"{width}x{height}+{x}+{max(0, y)}")

    def _windows_colorref(self, color: str) -> int:
        red, green, blue = ImageColor.getrgb(color)
        return (blue << 16) | (green << 8) | red

    def _apply_window_chrome(self) -> None:
        if os.name != "nt":
            return

        try:
            self.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id()) or self.winfo_id()
            dwmapi = ctypes.windll.dwmapi
        except Exception:
            return

        dark_flag = ctypes.c_int(1)
        for attribute in (20, 19):
            try:
                if dwmapi.DwmSetWindowAttribute(hwnd, attribute, ctypes.byref(dark_flag), ctypes.sizeof(dark_flag)) == 0:
                    break
            except Exception:
                break

        for attribute, color in (
            (35, self.colors["card3"]),
            (36, self.colors["text"]),
            (34, self.colors["card3"]),
        ):
            try:
                color_ref = ctypes.c_int(self._windows_colorref(color))
                dwmapi.DwmSetWindowAttribute(hwnd, attribute, ctypes.byref(color_ref), ctypes.sizeof(color_ref))
            except Exception:
                continue

    def _apply_responsive_layout(self) -> None:
        self._layout_after_id = None
        width = max(1180, int(self.winfo_width()))
        height = max(720, int(self.winfo_height()))

        preview_height = 178 if height < 820 else 232 if height < 900 else 290
        chat_preview_height = 154 if height < 820 else 205 if height < 900 else 250
        compact_width = width < 1540

        changed = False
        if self.preview_host is not None:
            current_preview_height = int(float(self.preview_host.cget("height")))
            if current_preview_height != preview_height:
                self.preview_host.configure(height=preview_height)
                changed = True

        if self.chat_preview_host is not None:
            current_chat_height = int(float(self.chat_preview_host.cget("height")))
            if current_chat_height != chat_preview_height:
                self.chat_preview_host.configure(height=chat_preview_height)
                changed = True

        compact_banner = width < 1500 and height < 820
        banner_height = 64 if compact_banner else 86
        rail_art_height = 42 if compact_banner else 98
        hero_art_height = 98 if compact_banner else 124

        if self.work_art_label is not None:
            current_height = int(float(self.work_art_label.master.cget("height")))
            if current_height != banner_height:
                self.work_art_label.master.configure(height=banner_height)
                changed = True

        if self.preview_art_label is not None:
            current_height = int(float(self.preview_art_label.master.cget("height")))
            if current_height != banner_height:
                self.preview_art_label.master.configure(height=banner_height)
                changed = True

        if self.rail_art_label is not None:
            current_height = int(float(self.rail_art_label.master.cget("height")))
            if current_height != rail_art_height:
                self.rail_art_label.master.configure(height=rail_art_height)
                changed = True

        if self.hero_art_label is not None:
            current_height = int(float(self.hero_art_label.master.cget("height")))
            if current_height != hero_art_height:
                self.hero_art_label.master.configure(height=hero_art_height)
                changed = True

        if self.stage_status_frame is not None:
            should_show_status = height >= 820
            status_visible = self.stage_status_frame.winfo_manager() == "grid"
            if should_show_status and not status_visible:
                self.stage_status_frame.grid()
            elif not should_show_status and status_visible:
                self.stage_status_frame.grid_remove()
            changed = changed or (should_show_status != status_visible)

        if self.section_subtitle_label is not None and self.workbench_frame is not None:
            wraplength = max(320, int(self.workbench_frame.winfo_width()) - 64)
            if int(self.section_subtitle_label.cget("wraplength")) != wraplength:
                self.section_subtitle_label.configure(wraplength=wraplength)
                changed = True
            show_subtitle = width >= 1500 and height >= 820
            subtitle_visible = self.section_subtitle_label.winfo_manager() == "grid"
            if show_subtitle and not subtitle_visible:
                self.section_subtitle_label.grid()
                changed = True
            elif not show_subtitle and subtitle_visible:
                self.section_subtitle_label.grid_remove()
                changed = True

        if self.preview_header is not None and self.deck_stats_frame is not None:
            stats_below_header = compact_width and height < 900
            current_stats_row = int(self.deck_stats_frame.grid_info().get("row", 0))
            if stats_below_header and current_stats_row != 4:
                self.deck_stats_frame.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(14, 0))
                changed = True
            elif not stats_below_header and current_stats_row != 0:
                self.deck_stats_frame.grid(row=0, column=1, rowspan=4, sticky="e")
                changed = True

        if self.deck_overlay_chip is not None and self.deck_chat_chip is not None:
            stacked_stats = compact_width and height < 900
            overlay_row = int(self.deck_overlay_chip.grid_info().get("row", 0))
            overlay_column = int(self.deck_overlay_chip.grid_info().get("column", 0))
            chat_row = int(self.deck_chat_chip.grid_info().get("row", 0))
            if stacked_stats and (overlay_row != 0 or overlay_column != 0 or chat_row != 1):
                self.deck_overlay_chip.grid(row=0, column=0, sticky="ew", padx=0, pady=(0, 8))
                self.deck_chat_chip.grid(row=1, column=0, sticky="ew")
                changed = True
            elif not stacked_stats and (overlay_row != 0 or overlay_column != 0 or chat_row != 0):
                self.deck_overlay_chip.grid(row=0, column=0, sticky="ew", padx=(0, 10), pady=0)
                self.deck_chat_chip.grid(row=0, column=1, sticky="ew")
                changed = True

        if self.bottom_cards_frame is not None and self.overlay_route_card is not None and self.chat_route_card is not None:
            stacked_cards = compact_width
            overlay_row = int(self.overlay_route_card.grid_info().get("row", 0))
            overlay_column = int(self.overlay_route_card.grid_info().get("column", 0))
            chat_row = int(self.chat_route_card.grid_info().get("row", 0))
            if stacked_cards and (overlay_row != 0 or overlay_column != 0 or chat_row != 1):
                self.overlay_route_card.grid(row=0, column=0, sticky="ew", padx=0, pady=(0, 12))
                self.chat_route_card.grid(row=1, column=0, sticky="ew", padx=0)
                changed = True
            elif not stacked_cards and (overlay_row != 0 or overlay_column != 0 or chat_row != 0):
                self.overlay_route_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=0)
                self.chat_route_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=0)
                changed = True

        if self.preview_title_label is not None:
            self.preview_title_label.configure(font=("Bahnschrift SemiBold", 18 if compact_width else 22))

        if self.capture_hint_label is not None and self.scene_meta_label is not None and self.preview_panel is not None:
            wraplength = max(300, int(self.preview_panel.winfo_width()) - 46)
            if int(self.capture_hint_label.cget("wraplength")) != wraplength:
                self.capture_hint_label.configure(wraplength=wraplength)
                self.scene_meta_label.configure(wraplength=wraplength)
                changed = True

        self._refresh_ui_textures()

        if changed:
            self._schedule_render(20)

    def _load_brand_assets(self) -> None:
        if not self.icon_path.exists():
            return

        try:
            with Image.open(self.icon_path) as icon_image:
                icon_rgba = icon_image.convert("RGBA")
                brand_tile = ImageOps.contain(icon_rgba, (72, 72), Image.LANCZOS)
                self.brand_icon_photo = ImageTk.PhotoImage(brand_tile)
                self.window_icon_photo = ImageTk.PhotoImage(icon_rgba)
        except Exception:
            return

        try:
            if self.window_icon_photo is not None:
                self.iconphoto(True, self.window_icon_photo)
        except tk.TclError:
            pass

        try:
            if self.icon_ico_path.exists():
                self.iconbitmap(default=str(self.icon_ico_path))
        except tk.TclError:
            pass

    def _load_ui_textures(self) -> None:
        header_path = self.ui_assets_dir / "desktop_header_texture.png"
        sidebar_path = self.ui_assets_dir / "desktop_sidebar_texture.png"
        wallpaper_path = self.ui_assets_dir / "desktop_app_wallpaper.png"

        try:
            if header_path.exists():
                with Image.open(header_path) as source:
                    self.ui_header_source = source.convert("RGBA")
        except Exception:
            self.ui_header_source = None

        try:
            if sidebar_path.exists():
                with Image.open(sidebar_path) as source:
                    self.ui_sidebar_source = source.convert("RGBA")
        except Exception:
            self.ui_sidebar_source = None

        try:
            if wallpaper_path.exists():
                with Image.open(wallpaper_path) as source:
                    self.ui_wallpaper_source = source.convert("RGBA")
        except Exception:
            self.ui_wallpaper_source = None

    def _refresh_ui_textures(self) -> None:
        if self.shell_art_label is not None and self.ui_wallpaper_source is not None:
            width = max(1180, self.shell_art_label.winfo_width())
            height = max(720, self.shell_art_label.winfo_height())
            shell_size = (width, height)
            if self._ui_texture_sizes.get("shell") != shell_size or self.ui_wallpaper_photo is None:
                shell_image = ImageOps.fit(self.ui_wallpaper_source, shell_size, Image.LANCZOS)
                self.ui_wallpaper_photo = ImageTk.PhotoImage(shell_image)
                self._ui_texture_sizes["shell"] = shell_size
            self.shell_art_label.configure(image=self.ui_wallpaper_photo)
            self.shell_art_label.image = self.ui_wallpaper_photo

        if self.hero_art_label is not None and self.ui_header_source is not None:
            width = max(300, self.hero_art_label.winfo_width())
            height = max(92, self.hero_art_label.winfo_height())
            hero_size = (width, height)
            if self._ui_texture_sizes.get("hero") != hero_size or self.ui_header_photo is None:
                header_image = ImageOps.fit(self.ui_header_source, hero_size, Image.LANCZOS)
                self.ui_header_photo = ImageTk.PhotoImage(header_image)
                self._ui_texture_sizes["hero"] = hero_size
            self.hero_art_label.configure(image=self.ui_header_photo)
            self.hero_art_label.image = self.ui_header_photo

        if self.rail_art_label is not None and self.ui_sidebar_source is not None:
            width = max(150, self.rail_art_label.winfo_width())
            height = max(120, self.rail_art_label.winfo_height())
            rail_size = (width, height)
            if self._ui_texture_sizes.get("rail") != rail_size or self.ui_sidebar_photo is None:
                rail_image = ImageOps.fit(self.ui_sidebar_source, rail_size, Image.LANCZOS)
                self.ui_sidebar_photo = ImageTk.PhotoImage(rail_image)
                self._ui_texture_sizes["rail"] = rail_size
            self.rail_art_label.configure(image=self.ui_sidebar_photo)
            self.rail_art_label.image = self.ui_sidebar_photo

        if self.work_art_label is not None and self.ui_header_source is not None:
            width = max(320, self.work_art_label.winfo_width())
            height = max(72, self.work_art_label.winfo_height())
            work_size = (width, height)
            if self._ui_texture_sizes.get("work") != work_size:
                work_image = ImageOps.fit(self.ui_header_source, work_size, Image.LANCZOS)
                self.work_art_photo = ImageTk.PhotoImage(work_image)
                self._ui_texture_sizes["work"] = work_size
            self.work_art_label.configure(image=self.work_art_photo)
            self.work_art_label.image = self.work_art_photo

        if self.preview_art_label is not None and self.ui_header_source is not None:
            width = max(320, self.preview_art_label.winfo_width())
            height = max(72, self.preview_art_label.winfo_height())
            preview_size = (width, height)
            if self._ui_texture_sizes.get("preview") != preview_size:
                preview_image = ImageOps.fit(self.ui_header_source, preview_size, Image.LANCZOS)
                self.preview_art_photo = ImageTk.PhotoImage(preview_image)
                self._ui_texture_sizes["preview"] = preview_size
            self.preview_art_label.configure(image=self.preview_art_photo)
            self.preview_art_label.image = self.preview_art_photo

    def _action_button(self, parent, text: str, command, *, accent: bool = False, compact: bool = False) -> tk.Button:
        padx = 14 if compact else 18
        pady = 8 if compact else 11
        font = self.fonts["button_small"] if compact else self.fonts["button"]
        return tk.Button(
            parent,
            text=text,
            command=command,
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=padx,
            pady=pady,
            font=font,
            bg=self.colors["accent"] if accent else self.colors["card2"],
            fg="#061019" if accent else self.colors["text"],
            activebackground=self.colors["accent2"] if accent else self.colors["card3"],
            activeforeground="#081019" if accent else self.colors["text"],
            highlightthickness=1,
            highlightbackground=self.colors["border"],
        )

    def _section_card(self, parent, title: str, subtitle: str, accent: str) -> tuple[tk.Frame, tk.Frame]:
        outer = tk.Frame(
            parent,
            bg=self.colors["card2"],
            highlightthickness=1,
            highlightbackground=self.colors["border"],
            bd=0,
        )
        outer.columnconfigure(0, weight=1)
        tk.Frame(outer, bg=accent, height=3).grid(row=0, column=0, sticky="ew")

        body = tk.Frame(outer, bg=self.colors["card2"], padx=16, pady=14)
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)

        tk.Label(
            body,
            text=title,
            bg=self.colors["card2"],
            fg=self.colors["gold"],
            font=self.fonts["section"],
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        if subtitle:
            tk.Label(
                body,
                text=subtitle,
                bg=self.colors["card2"],
                fg=self.colors["muted"],
                font=self.fonts["body"],
                justify="left",
                wraplength=320,
                anchor="w",
            ).grid(row=1, column=0, sticky="w", pady=(6, 0))

        content = tk.Frame(body, bg=self.colors["card2"])
        content.grid(row=2, column=0, sticky="nsew", pady=(14, 0))
        content.columnconfigure(0, weight=1)
        return outer, content

    def _entry_widget(
        self,
        parent,
        variable: tk.StringVar,
        *,
        readonly: bool = False,
        show: str | None = None,
        justify: str = "left",
    ) -> tk.Entry:
        entry = tk.Entry(
            parent,
            textvariable=variable,
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground=self.colors["border"],
            highlightcolor=self.colors["accent"],
            bg=self.colors["card2"],
            fg=self.colors["text"],
            insertbackground=self.colors["text"],
            readonlybackground=self.colors["input"],
            font=self.fonts["body"],
            justify=justify,
        )
        if show is not None:
            entry.configure(show=show)
        if readonly:
            entry.configure(state="readonly")
        return entry

    def _register_combobox(self, combo: ttk.Combobox) -> ttk.Combobox:
        combo.configure(postcommand=lambda widget=combo: self._style_combobox_popup(widget))
        combo.bind("<Button-1>", self._refresh_combobox_theme, add="+")
        combo.bind("<FocusIn>", self._refresh_combobox_theme, add="+")
        combo.bind("<Map>", self._refresh_combobox_theme, add="+")
        self.combo_widgets.append(combo)
        self.after_idle(lambda widget=combo: self._style_combobox_popup(widget))
        return combo

    def _combo_widget(
        self,
        parent,
        variable: tk.StringVar,
        *,
        values=(),
        state: str = "readonly",
    ) -> ttk.Combobox:
        combo = ttk.Combobox(parent, textvariable=variable, state=state, values=tuple(values))
        return self._register_combobox(combo)

    def _refresh_combobox_theme(self, event=None) -> None:
        if event is not None and isinstance(event.widget, ttk.Combobox):
            self._style_combobox_popup(event.widget)
            return
        for combo in self.combo_widgets:
            self._style_combobox_popup(combo)

    def _style_combobox_popup(self, combo: ttk.Combobox) -> None:
        try:
            popdown = combo.tk.eval(f"ttk::combobox::PopdownWindow {combo}")
        except tk.TclError:
            return

        for widget_path, options in (
            (
                f"{popdown}.f.l",
                (
                    ("-background", self.colors["card2"]),
                    ("-foreground", self.colors["text"]),
                    ("-selectbackground", self.colors["accent"]),
                    ("-selectforeground", "#081019"),
                    ("-highlightthickness", 0),
                    ("-borderwidth", 0),
                    ("-font", "{Segoe UI Variable Small} 10"),
                ),
            ),
            (
                f"{popdown}.f.sb",
                (
                    ("-background", self.colors["card3"]),
                    ("-activebackground", self.colors["accent"]),
                    ("-troughcolor", self.colors["card"]),
                    ("-highlightthickness", 0),
                    ("-borderwidth", 0),
                ),
            ),
        ):
            try:
                if int(combo.tk.call("winfo", "exists", widget_path)):
                    combo.tk.call(widget_path, "configure", *[item for pair in options for item in pair])
            except tk.TclError:
                continue

    def _nav_button(self, parent, key: str, text: str) -> tk.Button:
        button = tk.Button(
            parent,
            text=text,
            command=lambda name=key: self._select_control_page(name),
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=22,
            pady=10,
            font=("Bahnschrift SemiBold", 11),
            bg=self.colors["card2"],
            fg=self.colors["muted"],
            activebackground=self.colors["card2"],
            activeforeground=self.colors["text"],
            highlightthickness=1,
            highlightbackground=self.colors["border"],
            anchor="w",
            justify="left",
        )
        self.control_nav_buttons[key] = button
        return button

    def _stat_chip(self, parent, title: str, variable: tk.StringVar, accent_color: str) -> tk.Frame:
        outer = tk.Frame(parent, bg=self.colors["card2"], highlightthickness=1, highlightbackground=self.colors["border"])
        outer.columnconfigure(0, weight=1)
        tk.Frame(outer, bg=accent_color, height=3).grid(row=0, column=0, sticky="ew")
        body = tk.Frame(outer, bg=self.colors["card2"], padx=14, pady=12)
        body.grid(row=1, column=0, sticky="nsew")
        tk.Label(
            body,
            text=title.upper(),
            bg=self.colors["card2"],
            fg=self.colors["muted"],
            font=self.fonts["chip_label"],
            anchor="w",
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            body,
            textvariable=variable,
            bg=self.colors["card2"],
            fg=self.colors["text"],
            font=self.fonts["chip_value"],
            anchor="w",
        ).grid(row=1, column=0, sticky="w", pady=(6, 0))
        return outer

    def _micro_chip(self, parent, title: str, variable: tk.StringVar, accent_color: str) -> tk.Frame:
        outer = tk.Frame(parent, bg=self.colors["card2"], highlightthickness=1, highlightbackground=self.colors["border"], bd=0)
        outer.columnconfigure(0, weight=1)
        tk.Frame(outer, bg=accent_color, height=2).grid(row=0, column=0, sticky="ew")
        body = tk.Frame(outer, bg=self.colors["card2"], padx=10, pady=8)
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)
        tk.Label(
            body,
            text=title.upper(),
            bg=self.colors["card2"],
            fg=self.colors["muted"],
            font=self.fonts["chip_label"],
            anchor="w",
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            body,
            textvariable=variable,
            bg=self.colors["card2"],
            fg=self.colors["text"],
            font=self.fonts["button_small"],
            anchor="w",
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))
        return outer

    def _select_control_page(self, key: str) -> None:
        if key not in self.control_pages:
            return

        page_meta = {
            "studio": (
                "Студия персонажа",
                "Собери кадры, подключи микрофон и сразу проверь, как персонаж держится в эфире.",
            ),
            "output": (
                "Сцена и вывод",
                "Здесь настраиваются композиция сцены, фон, локальный адрес и поведение окна для OBS.",
            ),
            "chat": (
                "Чат Twitch",
                "Подключи канал, включи авторизацию и подбери стиль карточек, чтобы чат выглядел цельно и дорого.",
            ),
            "help": (
                "Помощь и маршруты",
                "Быстрый старт по OBS, локальной сцене и кастомному чату Twitch без лишней возни.",
            ),
        }
        title, subtitle = page_meta.get(key, ("Панель управления", ""))
        self.section_title_var.set(title)
        self.section_subtitle_var.set(subtitle)

        for page_key, page in self.control_pages.items():
            if page_key == key:
                page.grid()
            else:
                page.grid_remove()

        for page_key, button in self.control_nav_buttons.items():
            active = page_key == key
            button.configure(
                bg=self.colors["accent"] if active else self.colors["card2"],
                fg="#081019" if active else self.colors["muted"],
                activebackground=self.colors["accent2"] if active else self.colors["card2"],
                activeforeground="#081019" if active else self.colors["text"],
                highlightbackground=self.colors["accent"] if active else self.colors["border"],
            )

        self.active_control_page = key
        self._on_control_tab_changed()

    def _control_contains_widget(self, widget) -> bool:
        current = widget
        targets = [self.control_scroll_canvas, self.workbench_frame, self.preview_panel]
        while current is not None:
            if current in targets:
                return True
            try:
                current = current.master
            except AttributeError:
                current = None
        return False

    def _sync_control_scrollregion(self) -> None:
        if self.control_scroll_canvas is None or self.control_scroll_inner is None:
            return
        bbox = self.control_scroll_canvas.bbox("all")
        if bbox is None:
            return
        x1, y1, x2, y2 = bbox
        self.control_scroll_canvas.configure(scrollregion=(x1, y1, x2, y2 + 32))

    def _on_control_canvas_configure(self, event) -> None:
        if self.control_scroll_canvas is None or self.control_scroll_window_id is None:
            return
        self.control_scroll_canvas.itemconfigure(self.control_scroll_window_id, width=event.width)
        self._sync_control_scrollregion()

    def _on_control_inner_configure(self, event) -> None:
        del event
        self._sync_control_scrollregion()

    def _on_global_mousewheel(self, event) -> None:
        if self.control_scroll_canvas is None:
            return

        hovered = self.winfo_containing(event.x_root, event.y_root)
        if hovered is None or not self._control_contains_widget(hovered):
            return

        delta = event.delta
        if delta == 0:
            return
        step = int(-delta / 120) if abs(delta) >= 120 else (-1 if delta > 0 else 1)
        if step == 0:
            step = -1 if delta > 0 else 1
        self.control_scroll_canvas.yview_scroll(step * 3, "units")

    def _on_window_configure(self, event) -> None:
        if event.widget is not self or self.state() == "iconic":
            return
        self._resize_cooldown_until = time.monotonic() + 0.18
        if self._layout_after_id is not None:
            self.after_cancel(self._layout_after_id)
        self._layout_after_id = self.after(42, self._apply_responsive_layout)

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.configure(bg=self.colors["card"])

        shell = tk.Frame(self, bg="#060A12", padx=14, pady=14)
        shell.grid(row=0, column=0, sticky="nsew")
        shell.columnconfigure(0, weight=1)
        shell.rowconfigure(1, weight=1)

        shell_art = tk.Label(shell, bg="#060A12", bd=0, highlightthickness=0)
        shell_art.place(relx=0, rely=0, relwidth=1, relheight=1)
        shell_art.lower()
        self.shell_art_label = shell_art

        hero = tk.Frame(
            shell,
            bg="#101827",
            highlightthickness=1,
            highlightbackground="#28415F",
            bd=0,
        )
        hero.grid(row=0, column=0, sticky="ew")
        hero.columnconfigure(0, weight=1)

        tk.Frame(hero, bg=self.colors["accent"], height=4).grid(row=0, column=0, sticky="ew")

        hero_inner = tk.Frame(hero, bg="#101827", padx=24, pady=22)
        hero_inner.grid(row=1, column=0, sticky="nsew")
        hero_inner.columnconfigure(0, weight=1)
        hero_inner.columnconfigure(1, weight=0)

        brand_block = tk.Frame(hero_inner, bg="#101827")
        brand_block.grid(row=0, column=0, sticky="nw")

        if self.brand_icon_photo is not None:
            brand = tk.Label(brand_block, image=self.brand_icon_photo, bg="#101827", bd=0, highlightthickness=0)
        else:
            brand = tk.Label(
                brand_block,
                text="Z",
                bg="#101827",
                fg=self.colors["gold"],
                font=("Segoe UI Black", 28),
                width=3,
                height=2,
                bd=0,
                highlightthickness=0,
            )
        brand.grid(row=0, column=0, rowspan=2, sticky="nw", padx=(0, 14))

        title_stack = tk.Frame(brand_block, bg="#101827")
        title_stack.grid(row=0, column=1, sticky="w")
        tk.Label(
            title_stack,
            text="РЕЖИССЕРСКИЙ ПУЛЬТ",
            bg="#101827",
            fg=self.colors["gold"],
            font=self.fonts["eyebrow"],
            anchor="w",
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            title_stack,
            text=APP_TITLE,
            bg="#101827",
            fg=self.colors["text"],
            font=self.fonts["display_large"],
            anchor="w",
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))
        tk.Label(
            title_stack,
            text="Режиссерский пульт для OBS: персонаж, киношная сцена, прозрачная сцена и кастомный чат Twitch.",
            bg="#101827",
            fg=self.colors["muted"],
            font=("Segoe UI Variable Small", 11),
            justify="left",
            anchor="w",
        ).grid(row=2, column=0, sticky="w", pady=(8, 0))

        hero_buttons = tk.Frame(hero_inner, bg="#101827")
        hero_buttons.grid(row=0, column=1, sticky="ne")
        hero_buttons.columnconfigure(0, weight=1)
        hero_buttons.columnconfigure(1, weight=1)
        self._action_button(hero_buttons, "Открыть сцену", self._open_obs, accent=True).grid(
            row=0, column=0, sticky="ew", padx=(0, 8), pady=(0, 8)
        )
        self._action_button(hero_buttons, "Копировать адрес", self._copy_overlay_url).grid(
            row=0, column=1, sticky="ew", pady=(0, 8)
        )
        self._action_button(hero_buttons, "Старт микрофона", self._start_audio).grid(
            row=1, column=0, sticky="ew", padx=(0, 8)
        )
        self._action_button(hero_buttons, "Помощь", self._show_help_tab).grid(row=1, column=1, sticky="ew")

        hero_art_shell = tk.Frame(
            hero_inner,
            bg=self.colors["card2"],
            highlightthickness=1,
            highlightbackground="#325070",
            bd=0,
            height=124,
        )
        hero_art_shell.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(18, 0))
        hero_art_shell.grid_propagate(False)
        hero_art_shell.columnconfigure(0, weight=1)
        hero_art_shell.rowconfigure(0, weight=1)
        self.hero_art_label = tk.Label(hero_art_shell, bg=self.colors["card2"], bd=0, highlightthickness=0)
        self.hero_art_label.grid(row=0, column=0, sticky="nsew")

        hero_stats = tk.Frame(hero_inner, bg="#101827")
        hero_stats.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(18, 0))
        hero_stats.columnconfigure(0, weight=1)
        hero_stats.columnconfigure(1, weight=1)
        hero_stats.columnconfigure(2, weight=1)
        hero_stats.columnconfigure(3, weight=1)
        self._stat_chip(hero_stats, "Сцена", self.hero_scene_var, self.colors["accent"]).grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self._stat_chip(hero_stats, "Чат Twitch", self.hero_chat_var, self.colors["accent2"]).grid(row=0, column=1, sticky="ew", padx=5)
        self._stat_chip(hero_stats, "Сигнал", self.hero_signal_var, self.colors["gold"]).grid(row=0, column=2, sticky="ew", padx=5)
        self._stat_chip(hero_stats, "Локальный узел", self.deck_overlay_var, self.colors["mint"]).grid(row=0, column=3, sticky="ew", padx=(10, 0))

        body = tk.Frame(shell, bg="#060A12")
        body.grid(row=1, column=0, sticky="nsew", pady=(18, 0))
        body.columnconfigure(0, weight=0)
        body.columnconfigure(1, weight=7, minsize=460)
        body.columnconfigure(2, weight=5, minsize=420)
        body.rowconfigure(0, weight=1)

        rail = tk.Frame(body, bg="#101827", highlightthickness=1, highlightbackground="#28415F", bd=0)
        rail.grid(row=0, column=0, sticky="ns", padx=(0, 16))
        rail.configure(width=232)
        rail.grid_propagate(False)
        rail.columnconfigure(0, weight=1)
        rail.rowconfigure(0, weight=1)

        rail_inner = tk.Frame(rail, bg="#101827", padx=18, pady=18)
        rail_inner.grid(row=0, column=0, sticky="nsew")
        rail_inner.columnconfigure(0, weight=1)
        rail_inner.rowconfigure(5, weight=1)

        tk.Label(
            rail_inner,
            text="ПУЛЬТ",
            bg="#101827",
            fg=self.colors["gold"],
            font=self.fonts["eyebrow"],
            anchor="w",
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            rail_inner,
            text="Навигация",
            bg="#101827",
            fg=self.colors["text"],
            font=self.fonts["section_large"],
            anchor="w",
        ).grid(row=1, column=0, sticky="w", pady=(6, 0))
        tk.Label(
            rail_inner,
            text="Быстрый переход между студией, сценой, чатом Twitch и справкой.",
            bg="#101827",
            fg=self.colors["muted"],
            font=self.fonts["body"],
            justify="left",
            wraplength=188,
            anchor="w",
        ).grid(row=2, column=0, sticky="w", pady=(8, 0))

        rail_art_shell = tk.Frame(
            rail_inner,
            bg=self.colors["card2"],
            highlightthickness=1,
            highlightbackground=self.colors["border"],
            bd=0,
            height=98,
        )
        rail_art_shell.grid(row=4, column=0, sticky="ew", pady=(14, 0))
        rail_art_shell.grid_propagate(False)
        rail_art_shell.columnconfigure(0, weight=1)
        rail_art_shell.rowconfigure(0, weight=1)
        self.rail_art_label = tk.Label(rail_art_shell, bg=self.colors["card2"], bd=0, highlightthickness=0)
        self.rail_art_label.grid(row=0, column=0, sticky="nsew")

        nav = tk.Frame(rail_inner, bg="#101827")
        nav.grid(row=3, column=0, sticky="ew", pady=(18, 0))
        nav.columnconfigure(0, weight=1)
        for index, (key, text) in enumerate((
            ("studio", "Студия"),
            ("output", "Сцена"),
            ("chat", "Чат Twitch"),
            ("help", "Маршруты"),
        )):
            self._nav_button(nav, key, text).grid(row=index, column=0, sticky="ew", pady=(0, 10))

        tk.Frame(rail_inner, bg="#101827").grid(row=5, column=0, sticky="nsew")

        rail_info = tk.Frame(
            rail_inner,
            bg=self.colors["card2"],
            highlightthickness=1,
            highlightbackground=self.colors["border"],
            bd=0,
            padx=12,
            pady=12,
        )
        rail_info.grid(row=6, column=0, sticky="sew")
        rail_info.columnconfigure(0, weight=1)
        tk.Frame(rail_info, bg=self.colors["accent2"], height=3).grid(row=0, column=0, sticky="ew")
        tk.Label(
            rail_info,
            text="ЭФИР",
            bg=self.colors["card2"],
            fg=self.colors["muted"],
            font=self.fonts["chip_label"],
            anchor="w",
        ).grid(row=1, column=0, sticky="w", pady=(10, 0))
        tk.Label(
            rail_info,
            textvariable=self.hero_signal_var,
            bg=self.colors["card2"],
            fg=self.colors["text"],
            font=self.fonts["section"],
            anchor="w",
        ).grid(row=2, column=0, sticky="w", pady=(4, 0))
        tk.Label(
            rail_info,
            textvariable=self.hero_chat_var,
            bg=self.colors["card2"],
            fg=self.colors["muted"],
            font=self.fonts["body"],
            justify="left",
            wraplength=184,
            anchor="w",
        ).grid(row=3, column=0, sticky="w", pady=(6, 0))

        workbench = tk.Frame(body, bg="#101827", highlightthickness=1, highlightbackground="#28415F", bd=0)
        workbench.grid(row=0, column=1, sticky="nsew", padx=(0, 16))
        workbench.columnconfigure(0, weight=1)
        workbench.rowconfigure(1, weight=1)
        self.workbench_frame = workbench

        tk.Frame(workbench, bg=self.colors["accent2"], height=3).grid(row=0, column=0, sticky="ew")

        work_inner = tk.Frame(workbench, bg="#101827", padx=20, pady=20)
        work_inner.grid(row=1, column=0, sticky="nsew")
        work_inner.columnconfigure(0, weight=1)
        work_inner.rowconfigure(3, weight=1)

        work_banner = tk.Frame(
            work_inner,
            bg=self.colors["card2"],
            highlightthickness=1,
            highlightbackground="#2D4A68",
            bd=0,
            height=86,
        )
        work_banner.grid(row=0, column=0, sticky="ew")
        work_banner.grid_propagate(False)
        work_banner.columnconfigure(0, weight=1)
        work_banner.rowconfigure(0, weight=1)
        self.work_art_label = tk.Label(work_banner, bg=self.colors["card2"], bd=0, highlightthickness=0)
        self.work_art_label.grid(row=0, column=0, sticky="nsew")
        tk.Label(
            work_banner,
            text="КОНТУР СТУДИИ",
            bg="#0F1827",
            fg=self.colors["accent"],
            font=self.fonts["eyebrow"],
            padx=10,
            pady=5,
        ).place(x=14, y=12)

        work_header = tk.Frame(work_inner, bg="#101827")
        work_header.grid(row=1, column=0, sticky="ew", pady=(14, 0))
        work_header.columnconfigure(0, weight=1)
        tk.Label(
            work_header,
            text="РАБОЧАЯ ЗОНА",
            bg="#101827",
            fg=self.colors["gold"],
            font=self.fonts["eyebrow"],
            anchor="w",
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            work_header,
            textvariable=self.section_title_var,
            bg="#101827",
            fg=self.colors["text"],
            font=self.fonts["display"],
            anchor="w",
        ).grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.section_subtitle_label = tk.Label(
            work_header,
            textvariable=self.section_subtitle_var,
            bg="#101827",
            fg=self.colors["muted"],
            font=self.fonts["body"],
            justify="left",
            wraplength=420,
            anchor="w",
        )
        self.section_subtitle_label.grid(row=2, column=0, sticky="w", pady=(8, 0))

        work_console = tk.Frame(work_inner, bg="#101827")
        work_console.grid(row=2, column=0, sticky="ew", pady=(16, 0))
        work_console.columnconfigure(0, weight=1)
        work_console.columnconfigure(1, weight=1)
        work_console.columnconfigure(2, weight=1)
        self._micro_chip(work_console, "Пак", self.internet_pack_var, self.colors["accent"]).grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self._micro_chip(work_console, "Арт", self.scene_style_var, self.colors["accent2"]).grid(row=0, column=1, sticky="ew", padx=4)
        self._micro_chip(work_console, "Момент", self.stream_moment_var, self.colors["gold"]).grid(row=0, column=2, sticky="ew", padx=(8, 0))

        scroll_shell = tk.Frame(work_inner, bg="#101827")
        scroll_shell.grid(row=3, column=0, sticky="nsew", pady=(18, 0))
        scroll_shell.columnconfigure(0, weight=1)
        scroll_shell.rowconfigure(0, weight=1)

        self.control_scroll_canvas = tk.Canvas(
            scroll_shell,
            bg="#101827",
            bd=0,
            relief="flat",
            highlightthickness=0,
            yscrollincrement=18,
        )
        self.control_scroll_canvas.grid(row=0, column=0, sticky="nsew")

        self.control_scrollbar = ttk.Scrollbar(
            scroll_shell,
            orient="vertical",
            command=self.control_scroll_canvas.yview,
            style="Dark.Vertical.TScrollbar",
        )
        self.control_scrollbar.grid(row=0, column=1, sticky="ns", padx=(8, 0))
        self.control_scroll_canvas.configure(yscrollcommand=self.control_scrollbar.set)

        pages_host = tk.Frame(self.control_scroll_canvas, bg="#101827")
        pages_host.columnconfigure(0, weight=1)
        self.control_scroll_window_id = self.control_scroll_canvas.create_window((0, 0), window=pages_host, anchor="nw")
        self.control_scroll_inner = pages_host
        self.control_scroll_canvas.bind("<Configure>", self._on_control_canvas_configure)
        pages_host.bind("<Configure>", self._on_control_inner_configure)
        self.bind_all("<MouseWheel>", self._on_global_mousewheel)

        studio_page = tk.Frame(pages_host, bg="#101827")
        output_page = tk.Frame(pages_host, bg="#101827")
        chat_page = tk.Frame(pages_host, bg="#101827")
        help_page = tk.Frame(pages_host, bg="#101827")

        for key, page in (
            ("studio", studio_page),
            ("output", output_page),
            ("chat", chat_page),
            ("help", help_page),
        ):
            page.grid(row=0, column=0, sticky="nsew")
            self.control_pages[key] = page

        self.chat_tab_page = chat_page
        self.help_tab = help_page

        self._build_studio_tab(studio_page)
        self._build_output_tab(output_page)
        self._build_chat_tab(chat_page)
        self._build_help_tab(help_page)
        self._select_control_page("studio")

        right = tk.Frame(body, bg="#101827", highlightthickness=1, highlightbackground="#28415F", bd=0)
        right.grid(row=0, column=2, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)
        self.preview_panel = right

        tk.Frame(right, bg=self.colors["mint"], height=3).grid(row=0, column=0, sticky="ew")

        right_inner = tk.Frame(right, bg="#101827", padx=20, pady=20)
        right_inner.grid(row=1, column=0, sticky="nsew")
        right_inner.columnconfigure(0, weight=1)
        right_inner.rowconfigure(3, weight=1)

        preview_banner = tk.Frame(
            right_inner,
            bg=self.colors["card2"],
            highlightthickness=1,
            highlightbackground="#2D4A68",
            bd=0,
            height=86,
        )
        preview_banner.grid(row=0, column=0, sticky="ew")
        preview_banner.grid_propagate(False)
        preview_banner.columnconfigure(0, weight=1)
        preview_banner.rowconfigure(0, weight=1)
        self.preview_art_label = tk.Label(preview_banner, bg=self.colors["card2"], bd=0, highlightthickness=0)
        self.preview_art_label.grid(row=0, column=0, sticky="nsew")
        tk.Label(
            preview_banner,
            text="ВИЗУАЛЬНЫЙ МОНИТОР",
            bg="#0F1827",
            fg=self.colors["mint"],
            font=self.fonts["eyebrow"],
            padx=10,
            pady=5,
        ).place(x=14, y=12)

        header = tk.Frame(right_inner, bg="#101827")
        header.grid(row=1, column=0, sticky="ew", pady=(14, 0))
        header.columnconfigure(0, weight=1)
        self.preview_header = header

        tk.Label(
            header,
            textvariable=self.preview_kicker_var,
            bg="#101827",
            fg=self.colors["gold"],
            font=self.fonts["eyebrow"],
            anchor="w",
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            header,
            textvariable=self.preview_title_var,
            bg="#101827",
            fg=self.colors["text"],
            font=self.fonts["display"],
            anchor="w",
        ).grid(row=1, column=0, sticky="w", pady=(6, 0))
        tk.Label(
            header,
            textvariable=self.capture_hint_var,
            bg="#101827",
            fg=self.colors["mint"],
            font=self.fonts["body"],
            justify="left",
            anchor="w",
        ).grid(row=2, column=0, sticky="w", pady=(8, 0))
        tk.Label(
            header,
            textvariable=self.scene_meta_var,
            bg="#101827",
            fg=self.colors["muted"],
            font=self.fonts["body"],
            justify="left",
            anchor="w",
        ).grid(row=3, column=0, sticky="w", pady=(4, 0))
        self.preview_title_label = header.grid_slaves(row=1, column=0)[0]
        self.capture_hint_label = header.grid_slaves(row=2, column=0)[0]
        self.scene_meta_label = header.grid_slaves(row=3, column=0)[0]

        deck_stats = tk.Frame(header, bg="#101827")
        deck_stats.grid(row=0, column=1, rowspan=4, sticky="e")
        self.deck_stats_frame = deck_stats
        self.deck_overlay_chip = self._stat_chip(deck_stats, "Сцена", self.deck_overlay_var, self.colors["accent"])
        self.deck_overlay_chip.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.deck_chat_chip = self._stat_chip(deck_stats, "Чат", self.deck_chat_var, self.colors["accent2"])
        self.deck_chat_chip.grid(row=0, column=1, sticky="ew")

        preview_console = tk.Frame(right_inner, bg="#101827")
        preview_console.grid(row=2, column=0, sticky="ew", pady=(16, 0))
        preview_console.columnconfigure(0, weight=1)
        preview_console.columnconfigure(1, weight=1)
        preview_console.columnconfigure(2, weight=1)
        self._micro_chip(preview_console, "Стиль", self.scene_style_var, self.colors["accent"]).grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self._micro_chip(preview_console, "Чат", self.chat_style_var, self.colors["accent2"]).grid(row=0, column=1, sticky="ew", padx=4)
        self._micro_chip(preview_console, "Режим", self.hero_signal_var, self.colors["gold"]).grid(row=0, column=2, sticky="ew", padx=(8, 0))

        self.preview_host = tk.Frame(
            right_inner,
            bg=self.colors["card2"],
            highlightthickness=1,
            highlightbackground="#2D4A68",
            bd=0,
            height=290,
        )
        self.preview_host.grid(row=3, column=0, sticky="nsew", pady=(18, 16))
        self.preview_host.grid_propagate(False)
        self.preview_host.grid_rowconfigure(0, weight=1)
        self.preview_host.grid_columnconfigure(0, weight=1)

        self.preview = tk.Label(
            self.preview_host,
            bg=self.colors["card2"],
            fg="#FFFFFF",
            font=self.fonts["section"],
            text="Сцена готовится...",
        )
        self.preview.grid(row=0, column=0, sticky="nsew")

        bottom_cards = tk.Frame(right_inner, bg="#101827")
        bottom_cards.grid(row=4, column=0, sticky="ew")
        bottom_cards.columnconfigure(0, weight=1)
        bottom_cards.columnconfigure(1, weight=1)
        self.bottom_cards_frame = bottom_cards

        overlay_card = tk.Frame(bottom_cards, bg=self.colors["card2"], highlightthickness=1, highlightbackground=self.colors["border"], padx=14, pady=14)
        overlay_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        overlay_card.columnconfigure(0, weight=1)
        self.overlay_route_card = overlay_card
        tk.Frame(overlay_card, bg=self.colors["accent"], height=3).grid(row=0, column=0, sticky="ew")
        tk.Label(overlay_card, text="Адрес сцены", bg=self.colors["card2"], fg=self.colors["gold"], font=self.fonts["section"]).grid(row=1, column=0, sticky="w", pady=(12, 0))
        tk.Label(
            overlay_card,
            text="Локальный адрес для прозрачной сцены без захвата окна.",
            bg=self.colors["card2"],
            fg=self.colors["muted"],
            font=self.fonts["body"],
            wraplength=360,
            justify="left",
        ).grid(row=2, column=0, sticky="w", pady=(8, 0))
        self._entry_widget(overlay_card, self.overlay_url_var, readonly=True).grid(row=3, column=0, sticky="ew", pady=(12, 0))

        overlay_actions = tk.Frame(overlay_card, bg=self.colors["card2"])
        overlay_actions.grid(row=4, column=0, sticky="ew", pady=(14, 0))
        overlay_actions.columnconfigure(0, weight=1)
        overlay_actions.columnconfigure(1, weight=1)

        self._action_button(overlay_actions, "Копировать адрес", self._copy_overlay_url, accent=True).grid(
            row=0, column=0, sticky="ew", padx=(0, 6)
        )
        self._action_button(overlay_actions, "Открыть сцену", self._open_obs).grid(
            row=0, column=1, sticky="ew", padx=(6, 0)
        )

        chat_card = tk.Frame(bottom_cards, bg=self.colors["card2"], highlightthickness=1, highlightbackground=self.colors["border"], padx=14, pady=14)
        chat_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        chat_card.columnconfigure(0, weight=1)
        self.chat_route_card = chat_card
        tk.Frame(chat_card, bg=self.colors["accent2"], height=3).grid(row=0, column=0, sticky="ew")
        tk.Label(chat_card, text="Адрес чата", bg=self.colors["card2"], fg=self.colors["gold"], font=self.fonts["section"]).grid(row=1, column=0, sticky="w", pady=(12, 0))
        tk.Label(
            chat_card,
            text="Кастомный чат Twitch с отдельными карточками сообщений и собственным адресом.",
            bg=self.colors["card2"],
            fg=self.colors["muted"],
            font=self.fonts["body"],
            wraplength=360,
            justify="left",
        ).grid(row=2, column=0, sticky="w", pady=(8, 0))
        self._entry_widget(chat_card, self.chat_browser_url_var, readonly=True).grid(row=3, column=0, sticky="ew", pady=(12, 0))

        chat_actions = tk.Frame(chat_card, bg=self.colors["card2"])
        chat_actions.grid(row=4, column=0, sticky="ew", pady=(14, 0))
        chat_actions.columnconfigure(0, weight=1)
        chat_actions.columnconfigure(1, weight=1)

        self._action_button(chat_actions, "Копировать адрес", self._copy_chat_browser_url).grid(
            row=0, column=0, sticky="ew", padx=(0, 6)
        )
        self._action_button(chat_actions, "Помощь", self._show_help_tab).grid(
            row=0, column=1, sticky="ew", padx=(6, 0)
        )

        status = tk.Frame(right_inner, bg=self.colors["card2"], highlightthickness=1, highlightbackground=self.colors["border"], padx=12, pady=8)
        status.grid(row=5, column=0, sticky="ew", pady=(16, 0))
        status.columnconfigure(1, weight=1)
        self.stage_status_frame = status

        tk.Label(status, text="МИК", bg=self.colors["card2"], fg=self.colors["gold"], font=self.fonts["chip_label"], anchor="w").grid(row=0, column=0, sticky="w")
        tk.Label(status, textvariable=self.status_var, bg=self.colors["card2"], fg=self.colors["text"], font=self.fonts["body_small"], anchor="w").grid(row=0, column=1, sticky="w")
        tk.Label(status, text="OBS", bg=self.colors["card2"], fg=self.colors["muted"], font=self.fonts["chip_label"], anchor="w").grid(row=1, column=0, sticky="w", pady=(6, 0))
        tk.Label(status, textvariable=self.obs_text, bg=self.colors["card2"], fg=self.colors["muted"], font=self.fonts["body_small"], anchor="w").grid(row=1, column=1, sticky="w", pady=(6, 0))

    def _build_studio_tab(self, parent: ttk.Frame) -> None:
        parent.configure(bg="#101827")
        parent.columnconfigure(0, weight=1)

        frames_card, frames = self._section_card(
            parent,
            "Кадры персонажа",
            "Idle и два talking-кадра формируют характер персонажа. Тут лучше всего заметно качество образа.",
            self.colors["gold"],
        )
        frames_card.grid(row=0, column=0, sticky="ew")
        frames.columnconfigure(1, weight=1)

        self._add_path(frames, 0, "idle", "Фото 1 — тишина")
        self._add_path(frames, 1, "talk_a", "Фото 2 — речь")
        self._add_path(frames, 2, "talk_b", "Фото 3 — речь")

        self._action_button(frames, "Обновить картинки", self._reload_media, compact=True).grid(
            row=3, column=0, columnspan=3, sticky="ew", pady=(14, 0)
        )

        audio_card, audio = self._section_card(
            parent,
            "Микрофон и чувствительность",
            "Управляй порогом и сразу смотри, как звук оживляет персонажа и сцену.",
            self.colors["accent"],
        )
        audio_card.grid(row=1, column=0, sticky="ew", pady=(16, 0))
        audio.columnconfigure(1, weight=1)

        tk.Label(audio, text="Устройство", bg=self.colors["card2"], fg=self.colors["text"], font=self.fonts["label"]).grid(row=0, column=0, sticky="w")
        self.device_combo = self._combo_widget(audio, self.device_var)
        self.device_combo.grid(row=0, column=1, sticky="ew", padx=(12, 10))
        self._action_button(audio, "Обновить", self._refresh_devices, compact=True).grid(row=0, column=2)

        tk.Label(audio, text="Порог речи", bg=self.colors["card2"], fg=self.colors["text"], font=self.fonts["label"]).grid(row=1, column=0, sticky="w", pady=(14, 0))
        ttk.Scale(audio, from_=1, to=50, variable=self.threshold_var, command=self._set_threshold_text).grid(
            row=1, column=1, columnspan=2, sticky="ew", pady=(14, 0)
        )
        tk.Label(audio, textvariable=self.threshold_text, bg=self.colors["card2"], fg=self.colors["muted"], font=self.fonts["body"]).grid(
            row=2, column=2, sticky="e", pady=(6, 0)
        )

        tk.Label(audio, text="Уровень", bg=self.colors["card2"], fg=self.colors["text"], font=self.fonts["label"]).grid(row=3, column=0, sticky="w", pady=(14, 0))
        self.level_bar = ttk.Progressbar(audio, orient="horizontal", mode="determinate", maximum=100)
        self.level_bar.grid(row=3, column=1, sticky="ew", pady=(14, 0))
        tk.Label(audio, textvariable=self.level_text, bg=self.colors["card2"], fg=self.colors["text"], font=self.fonts["label"]).grid(
            row=3, column=2, sticky="e", pady=(14, 0)
        )

        tk.Label(audio, text="Визуализация", bg=self.colors["card2"], fg=self.colors["text"], font=self.fonts["label"]).grid(row=4, column=0, sticky="w", pady=(16, 0))
        self.voice_canvas = tk.Canvas(
            audio,
            width=290,
            height=52,
            bg=self.colors["input"],
            bd=0,
            highlightthickness=1,
            highlightbackground=self.colors["border"],
        )
        self.voice_canvas.grid(row=4, column=1, columnspan=2, sticky="ew", pady=(16, 0))

    def _build_output_tab(self, parent: ttk.Frame) -> None:
        parent.configure(bg="#101827")
        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=1)

        overview_card, overview = self._section_card(
            parent,
            "Режиссура сцены",
            "Управляй визуалом через отдельные блоки: формат, фон, положение и локальный адрес сцены.",
            self.colors["accent2"],
        )
        overview_card.grid(row=0, column=0, columnspan=2, sticky="ew")
        overview.columnconfigure(0, weight=1)
        overview.columnconfigure(1, weight=1)
        overview.columnconfigure(2, weight=0)

        tk.Label(
            overview,
            text="Интернет-пак",
            bg=self.colors["card2"],
            fg=self.colors["text"],
            font=self.fonts["label"],
        ).grid(row=0, column=0, sticky="w")
        pack_combo = self._combo_widget(overview, self.internet_pack_var, values=INTERNET_PRESET_OPTIONS)
        pack_combo.grid(row=0, column=1, sticky="ew", padx=(12, 10))
        pack_combo.bind("<<ComboboxSelected>>", self._apply_stream_preset)

        self._action_button(overview, "Применить", self._apply_stream_preset, accent=True, compact=True).grid(row=0, column=2)

        tk.Label(
            overview,
            text="Момент эфира",
            bg=self.colors["card2"],
            fg=self.colors["text"],
            font=self.fonts["label"],
        ).grid(row=1, column=0, sticky="w", pady=(14, 0))
        moment_combo = self._combo_widget(overview, self.stream_moment_var, values=STREAM_MOMENT_OPTIONS)
        moment_combo.grid(row=1, column=1, sticky="ew", padx=(12, 10), pady=(14, 0))
        moment_combo.bind("<<ComboboxSelected>>", self._apply_stream_preset)

        tk.Label(
            overview,
            textvariable=self.preset_note_var,
            bg=self.colors["card2"],
            fg=self.colors["muted"],
            font=self.fonts["body"],
            justify="left",
            wraplength=520,
            anchor="w",
        ).grid(row=2, column=0, columnspan=3, sticky="w", pady=(14, 0))

        self._stat_chip(overview, "Формат", self.preset_var, self.colors["accent"]).grid(row=3, column=0, sticky="ew", padx=(0, 8), pady=(14, 0))
        self._stat_chip(overview, "Арт-режим", self.scene_style_var, self.colors["accent2"]).grid(row=3, column=1, sticky="ew", padx=(8, 8), pady=(14, 0))
        self._stat_chip(overview, "Момент", self.stream_moment_var, self.colors["gold"]).grid(row=3, column=2, sticky="ew", pady=(14, 0))
        self._stat_chip(overview, "Позиция", self.anchor_var, self.colors["gold"]).grid(row=4, column=0, sticky="ew", padx=(0, 8), pady=(12, 0))
        self._stat_chip(overview, "Масштаб", self.scale_text, self.colors["mint"]).grid(row=4, column=1, sticky="ew", padx=(8, 8), pady=(12, 0))
        self._stat_chip(overview, "Чат", self.chat_style_var, self.colors["accent"]).grid(row=4, column=2, sticky="ew", pady=(12, 0))

        quick_actions = tk.Frame(overview, bg=self.colors["card2"])
        quick_actions.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(16, 0))
        quick_actions.columnconfigure(0, weight=1)
        quick_actions.columnconfigure(1, weight=1)
        quick_actions.columnconfigure(2, weight=1)
        self._action_button(quick_actions, "Открыть сцену", self._open_obs, accent=True, compact=True).grid(
            row=0, column=0, sticky="ew", padx=(0, 6)
        )
        self._action_button(quick_actions, "Копировать адрес", self._copy_overlay_url, compact=True).grid(
            row=0, column=1, sticky="ew", padx=6
        )
        self._action_button(quick_actions, "Закрыть OBS", self._close_obs, compact=True).grid(
            row=0, column=2, sticky="ew", padx=(6, 0)
        )

        format_card, format_body = self._section_card(parent, "Формат сцены", "", self.colors["accent"])
        format_card.grid(row=1, column=0, sticky="nsew", pady=(16, 0), padx=(0, 8))
        format_body.columnconfigure(1, weight=1)

        tk.Label(format_body, text="Пресет", bg=self.colors["card2"], fg=self.colors["text"], font=self.fonts["label"]).grid(row=0, column=0, sticky="w")
        preset = self._combo_widget(format_body, self.preset_var, values=list(SCENE_PRESETS.keys()))
        preset.grid(row=0, column=1, sticky="ew", padx=(12, 0))
        preset.bind("<<ComboboxSelected>>", self._apply_preset)

        tk.Label(format_body, text="Арт-режим", bg=self.colors["card2"], fg=self.colors["text"], font=self.fonts["label"]).grid(row=1, column=0, sticky="w", pady=(14, 0))
        self._combo_widget(format_body, self.scene_style_var, values=SCENE_STYLE_OPTIONS).grid(
            row=1, column=1, sticky="ew", padx=(12, 0), pady=(14, 0)
        )

        tk.Label(format_body, text="Ширина", bg=self.colors["card2"], fg=self.colors["text"], font=self.fonts["label"]).grid(row=2, column=0, sticky="w", pady=(14, 0))
        self._entry_widget(format_body, self.width_var).grid(row=2, column=1, sticky="ew", padx=(12, 0), pady=(14, 0))

        tk.Label(format_body, text="Высота", bg=self.colors["card2"], fg=self.colors["text"], font=self.fonts["label"]).grid(row=3, column=0, sticky="w", pady=(14, 0))
        self._entry_widget(format_body, self.height_var).grid(row=3, column=1, sticky="ew", padx=(12, 0), pady=(14, 0))

        background_card, background = self._section_card(parent, "Фон сцены", "", self.colors["gold"])
        background_card.grid(row=1, column=1, sticky="nsew", pady=(16, 0), padx=(8, 0))
        background.columnconfigure(1, weight=1)

        tk.Label(
            background,
            text="Источник фона",
            bg=self.colors["card2"],
            fg=self.colors["text"],
            font=self.fonts["label"],
        ).grid(row=0, column=0, sticky="w")
        mode_stack = tk.Frame(background, bg=self.colors["card2"])
        mode_stack.grid(row=0, column=1, sticky="w", padx=(12, 0))
        ttk.Radiobutton(mode_stack, text="Прозрачный", variable=self.bg_mode_var, value="transparent", command=self._mark_dirty).grid(row=0, column=0, sticky="w")
        ttk.Radiobutton(mode_stack, text="Цвет / chroma", variable=self.bg_mode_var, value="color", command=self._mark_dirty).grid(row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Radiobutton(mode_stack, text="Картинка", variable=self.bg_mode_var, value="image", command=self._mark_dirty).grid(row=2, column=0, sticky="w", pady=(6, 0))

        tk.Label(background, text="Цвет", bg=self.colors["card2"], fg=self.colors["text"], font=self.fonts["label"]).grid(
            row=1, column=0, sticky="w", pady=(16, 0)
        )
        self._entry_widget(background, self.bg_color_var).grid(row=1, column=1, sticky="ew", padx=(12, 10), pady=(16, 0))
        self._action_button(background, "Палитра", self._pick_color, compact=True).grid(row=1, column=2, pady=(16, 0))

        tk.Label(background, text="Фон", bg=self.colors["card2"], fg=self.colors["text"], font=self.fonts["label"]).grid(
            row=2, column=0, sticky="w", pady=(14, 0)
        )
        self._entry_widget(background, self.bg_path_var).grid(row=2, column=1, sticky="ew", padx=(12, 10), pady=(14, 0))
        self._action_button(background, "Файл", self._pick_background, compact=True).grid(row=2, column=2, pady=(14, 0))

        placement_card, placement = self._section_card(
            parent,
            "Положение и окно",
            "Точная посадка персонажа в кадре, масштаб и поведение окна для OBS.",
            self.colors["mint"],
        )
        placement_card.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(16, 0))
        placement.columnconfigure(1, weight=1)

        tk.Label(placement, text="Позиция", bg=self.colors["card2"], fg=self.colors["text"], font=self.fonts["label"]).grid(row=0, column=0, sticky="w")
        anchor = self._combo_widget(placement, self.anchor_var, values=list(ANCHORS.keys()))
        anchor.grid(row=0, column=1, sticky="ew", padx=(12, 0))
        anchor.bind("<<ComboboxSelected>>", lambda event: self._mark_dirty())

        tk.Label(placement, text="Масштаб", bg=self.colors["card2"], fg=self.colors["text"], font=self.fonts["label"]).grid(row=1, column=0, sticky="w", pady=(14, 0))
        scale_row = tk.Frame(placement, bg=self.colors["card2"])
        scale_row.grid(row=1, column=1, sticky="ew", padx=(12, 0), pady=(14, 0))
        scale_row.columnconfigure(0, weight=1)
        ttk.Scale(scale_row, from_=18, to=90, variable=self.scale_var, command=self._set_scale_text).grid(row=0, column=0, sticky="ew")
        tk.Label(scale_row, textvariable=self.scale_text, bg=self.colors["card2"], fg=self.colors["text"], font=self.fonts["label"]).grid(row=0, column=1, sticky="e", padx=(12, 0))

        tk.Label(placement, text="Сдвиг X", bg=self.colors["card2"], fg=self.colors["text"], font=self.fonts["label"]).grid(row=2, column=0, sticky="w", pady=(14, 0))
        margin_x_row = tk.Frame(placement, bg=self.colors["card2"])
        margin_x_row.grid(row=2, column=1, sticky="ew", padx=(12, 0), pady=(14, 0))
        margin_x_row.columnconfigure(0, weight=1)
        ttk.Scale(margin_x_row, from_=0, to=280, variable=self.margin_x_var, command=self._set_margin_x_text).grid(row=0, column=0, sticky="ew")
        tk.Label(margin_x_row, textvariable=self.margin_x_text, bg=self.colors["card2"], fg=self.colors["text"], font=self.fonts["label"]).grid(row=0, column=1, sticky="e", padx=(12, 0))

        tk.Label(placement, text="Сдвиг Y", bg=self.colors["card2"], fg=self.colors["text"], font=self.fonts["label"]).grid(row=3, column=0, sticky="w", pady=(14, 0))
        margin_y_row = tk.Frame(placement, bg=self.colors["card2"])
        margin_y_row.grid(row=3, column=1, sticky="ew", padx=(12, 0), pady=(14, 0))
        margin_y_row.columnconfigure(0, weight=1)
        ttk.Scale(margin_y_row, from_=0, to=220, variable=self.margin_y_var, command=self._set_margin_y_text).grid(row=0, column=0, sticky="ew")
        tk.Label(margin_y_row, textvariable=self.margin_y_text, bg=self.colors["card2"], fg=self.colors["text"], font=self.fonts["label"]).grid(row=0, column=1, sticky="e", padx=(12, 0))

        window_flags = tk.Frame(placement, bg=self.colors["card2"])
        window_flags.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(16, 0))
        window_flags.columnconfigure(0, weight=1)
        window_flags.columnconfigure(1, weight=1)
        ttk.Checkbutton(window_flags, text="Без рамки окна", variable=self.borderless_var, command=self._sync_obs).grid(row=0, column=0, sticky="w")
        ttk.Checkbutton(window_flags, text="Поверх всех окон", variable=self.topmost_var, command=self._sync_obs).grid(row=0, column=1, sticky="w")

        source_card, source = self._section_card(
            parent,
            "Локальный адрес сцены",
            "Локальный адрес всегда отдает актуальный кадр. Это лучший режим для прозрачной сцены в OBS.",
            self.colors["accent"],
        )
        source_card.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(16, 0))
        source.columnconfigure(1, weight=1)

        tk.Label(source, text="Адрес сцены", bg=self.colors["card2"], fg=self.colors["text"], font=self.fonts["button"]).grid(row=0, column=0, sticky="w")
        self.overlay_entry = self._entry_widget(source, self.overlay_url_var)
        self.overlay_entry.grid(row=0, column=1, sticky="ew", padx=(12, 10))
        self._attach_entry_shortcuts(self.overlay_entry, self.overlay_url_var)
        self._action_button(source, "Копировать", self._copy_overlay_url, accent=True, compact=True).grid(row=0, column=2)

    def _build_chat_tab(self, parent: ttk.Frame) -> None:
        parent.configure(bg="#101827")
        parent.columnconfigure(0, weight=1)

        preview_card, preview_content = self._section_card(
            parent,
            "Предпросмотр чата",
            "Живой макет чата внутри приложения: карточки сообщений, акценты и спокойный ритм без лишнего шума.",
            self.colors["accent2"],
        )
        preview_card.grid(row=0, column=0, sticky="ew")
        preview_content.columnconfigure(0, weight=1)

        self.chat_preview_host = tk.Frame(
            preview_content,
            bg="#05070B",
            highlightthickness=0,
            bd=0,
            height=250,
        )
        self.chat_preview_host.grid(row=0, column=0, sticky="ew")
        self.chat_preview_host.grid_propagate(False)
        self.chat_preview_host.grid_columnconfigure(0, weight=1)
        self.chat_preview_host.grid_rowconfigure(0, weight=1)

        self.chat_preview = tk.Label(
            self.chat_preview_host,
            bg="#05070B",
            fg="#FFFFFF",
            font=self.fonts["button"],
            text="Превью чата готовится...",
            bd=0,
            highlightthickness=0,
        )
        self.chat_preview.grid(row=0, column=0, sticky="nsew")

        connect_card, connect = self._section_card(
            parent,
            "Подключение Twitch",
            "Можно вставить ссылку на канал, popout-chat или просто имя канала. Для стабильности лучше включать авторизацию.",
            self.colors["accent"],
        )
        connect_card.grid(row=1, column=0, sticky="ew", pady=(16, 0))
        connect.columnconfigure(0, weight=1)

        tk.Label(connect, text="Канал или ссылка Twitch", bg=self.colors["card2"], fg=self.colors["text"], font=self.fonts["label"]).grid(row=0, column=0, sticky="w")
        channel_row = tk.Frame(connect, bg=self.colors["card2"])
        channel_row.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        channel_row.columnconfigure(0, weight=1)
        self.chat_entry = self._entry_widget(channel_row, self.chat_url_var)
        self.chat_entry.grid(row=0, column=0, sticky="ew")
        self._attach_entry_shortcuts(self.chat_entry, self.chat_url_var)
        self._action_button(channel_row, "Открыть", self._open_chat_url, compact=True).grid(row=0, column=1, padx=(10, 0))

        tk.Label(connect, text="Логин Twitch", bg=self.colors["card2"], fg=self.colors["text"], font=self.fonts["label"]).grid(row=2, column=0, sticky="w", pady=(16, 0))
        auth_user_entry = self._entry_widget(connect, self.chat_auth_user_var)
        auth_user_entry.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        self._attach_entry_shortcuts(auth_user_entry, self.chat_auth_user_var)
        tk.Label(connect, text="Необязательно, но лучше для авторизации.", bg=self.colors["card2"], fg=self.colors["muted"], font=self.fonts["body"]).grid(
            row=4, column=0, sticky="w", pady=(6, 0)
        )

        tk.Label(connect, text="Токен доступа", bg=self.colors["card2"], fg=self.colors["text"], font=self.fonts["label"]).grid(row=5, column=0, sticky="w", pady=(16, 0))
        auth_token_entry = self._entry_widget(connect, self.chat_auth_token_var, show="•")
        auth_token_entry.grid(row=6, column=0, sticky="ew", pady=(8, 0))
        self._attach_entry_shortcuts(auth_token_entry, self.chat_auth_token_var)
        tk.Label(connect, text="Можно вставлять токен и с префиксом oauth:, и без него.", bg=self.colors["card2"], fg=self.colors["muted"], font=self.fonts["body"]).grid(
            row=7, column=0, sticky="w", pady=(6, 0)
        )

        tk.Label(connect, text="Адрес источника чата", bg=self.colors["card2"], fg=self.colors["text"], font=self.fonts["label"]).grid(row=8, column=0, sticky="w", pady=(16, 0))
        chat_url_row = tk.Frame(connect, bg=self.colors["card2"])
        chat_url_row.grid(row=9, column=0, sticky="ew", pady=(8, 0))
        chat_url_row.columnconfigure(0, weight=1)
        chat_url_entry = self._entry_widget(chat_url_row, self.chat_browser_url_var, readonly=True)
        chat_url_entry.grid(row=0, column=0, sticky="ew")
        self._action_button(chat_url_row, "Копировать", self._copy_chat_browser_url, accent=True, compact=True).grid(row=0, column=1, padx=(10, 0))

        tk.Label(
            connect,
            textvariable=self.chat_text,
            bg=self.colors["card2"],
            fg=self.colors["muted"],
            font=self.fonts["body"],
            wraplength=520,
            justify="left",
        ).grid(row=10, column=0, sticky="w", pady=(14, 0))

        look_card, look = self._section_card(
            parent,
            "Вид чата",
            "Подбери стиль, сторону и ширину панели. Здесь решается, насколько чат выглядит премиально в кадре.",
            self.colors["gold"],
        )
        look_card.grid(row=2, column=0, sticky="ew", pady=(16, 0))
        look.columnconfigure(1, weight=1)

        tk.Label(look, text="Стиль", bg=self.colors["card2"], fg=self.colors["text"], font=self.fonts["label"]).grid(row=0, column=0, sticky="w")
        self._combo_widget(look, self.chat_style_var, values=CHAT_STYLE_OPTIONS).grid(
            row=0, column=1, sticky="ew", padx=(12, 0)
        )

        tk.Label(look, text="Сторона", bg=self.colors["card2"], fg=self.colors["text"], font=self.fonts["label"]).grid(row=1, column=0, sticky="w", pady=(14, 0))
        self._combo_widget(look, self.chat_side_var, values=CHAT_SIDE_OPTIONS).grid(
            row=1, column=1, sticky="ew", padx=(12, 0), pady=(14, 0)
        )

        tk.Label(look, text="Ширина", bg=self.colors["card2"], fg=self.colors["text"], font=self.fonts["label"]).grid(row=2, column=0, sticky="w", pady=(14, 0))
        ttk.Scale(look, from_=24, to=42, variable=self.chat_width_var, command=self._set_chat_width_text).grid(
            row=2, column=1, sticky="ew", padx=(12, 0), pady=(14, 0)
        )
        tk.Label(look, textvariable=self.chat_width_text, bg=self.colors["card2"], fg=self.colors["text"], font=self.fonts["label"]).grid(
            row=3, column=1, sticky="e", pady=(6, 0)
        )

    def _build_help_tab(self, parent: ttk.Frame) -> None:
        parent.configure(bg="#101827")
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)

        help_card, help_body = self._section_card(
            parent,
            "Пошаговая помощь по OBS",
            "Здесь собрана рабочая инструкция по локальной сцене, прозрачности и кастомному чату Twitch.",
            self.colors["gold"],
        )
        help_card.grid(row=0, column=0, sticky="nsew")
        help_body.columnconfigure(0, weight=1)
        help_body.rowconfigure(0, weight=1)

        self.help_textbox = scrolledtext.ScrolledText(
            help_body,
            wrap="word",
            height=18,
            bg=self.colors["input"],
            fg=self.colors["text"],
            insertbackground=self.colors["text"],
            relief="flat",
            font=("Segoe UI Variable Small", 10),
            padx=14,
            pady=14,
            highlightthickness=1,
            highlightbackground=self.colors["border"],
        )
        self.help_textbox.grid(row=0, column=0, sticky="nsew")
        self.help_textbox.configure(state="disabled")
        self._update_help_textbox()

    def _attach_entry_shortcuts(self, entry: ttk.Entry, variable: tk.StringVar | None = None) -> None:
        entry.bind("<Control-v>", lambda event, var=variable: self._paste_into_entry(event.widget, var))
        entry.bind("<Control-V>", lambda event, var=variable: self._paste_into_entry(event.widget, var))
        entry.bind("<Shift-Insert>", lambda event, var=variable: self._paste_into_entry(event.widget, var))
        entry.bind("<Button-3>", lambda event, var=variable: self._show_entry_menu(event, var))

    def _paste_into_entry(self, widget, variable: tk.StringVar | None = None):
        try:
            clip = self.clipboard_get().strip()
        except tk.TclError:
            return "break"

        if variable is not None:
            variable.set(clip)
        else:
            try:
                widget.delete(0, "end")
                widget.insert(0, clip)
            except tk.TclError:
                pass
        return "break"

    def _show_entry_menu(self, event, variable: tk.StringVar | None = None):
        menu = tk.Menu(
            self,
            tearoff=0,
            bg=self.colors["card2"],
            fg=self.colors["text"],
            activebackground=self.colors["accent"],
            activeforeground="#FFFFFF",
        )
        menu.add_command(label="Вставить", command=lambda: self._paste_into_entry(event.widget, variable))
        menu.add_command(
            label="Очистить",
            command=lambda: variable.set("") if variable is not None else event.widget.delete(0, "end"),
        )
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _add_path(self, parent: ttk.LabelFrame, row: int, key: str, label: str) -> None:
        tk.Label(parent, text=label, bg=self.colors["card2"], fg=self.colors["text"], font=self.fonts["label"]).grid(
            row=row, column=0, sticky="w", pady=4
        )
        entry = self._entry_widget(parent, self.image_vars[key])
        entry.grid(row=row, column=1, sticky="ew", padx=(12, 10), pady=4)
        self._attach_entry_shortcuts(entry, self.image_vars[key])
        self._action_button(parent, "Выбрать", lambda slot=key: self._pick_image(slot), compact=True).grid(row=row, column=2, pady=4)

    def _set_threshold_text(self, value: str) -> None:
        self.threshold_text.set(f"{float(value):.0f}")

    def _set_scale_text(self, value: str) -> None:
        self.scale_text.set(f"{float(value):.0f}%")
        self._mark_dirty()

    def _set_margin_x_text(self, value: str) -> None:
        self.margin_x_text.set(f"{float(value):.0f} px")
        self._mark_dirty()

    def _set_margin_y_text(self, value: str) -> None:
        self.margin_y_text.set(f"{float(value):.0f} px")
        self._mark_dirty()

    def _set_chat_width_text(self, value: str) -> None:
        self.chat_width_text.set(f"{float(value):.0f}%")
        self._refresh_chat_overlay_cache()
        self.chat_preview_dirty = True
        self._schedule_render(30)

    def _pick_image(self, key: str) -> None:
        start = Path(self.image_vars[key].get()).parent if self.image_vars[key].get() else self.base_dir
        path = filedialog.askopenfilename(title="Выберите изображение", initialdir=str(start), filetypes=FILE_TYPES)
        if path:
            self.image_vars[key].set(path)
            self._reload_media()

    def _pick_background(self) -> None:
        start = Path(self.bg_path_var.get()).parent if self.bg_path_var.get() else self.base_dir
        path = filedialog.askopenfilename(title="Выберите фон", initialdir=str(start), filetypes=FILE_TYPES)
        if path:
            self.bg_path_var.set(path)
            self.bg_mode_var.set("image")
            self._reload_media()

    def _pick_color(self) -> None:
        chosen = colorchooser.askcolor(color=self.bg_color_var.get(), parent=self)
        if chosen and chosen[1]:
            self.bg_color_var.set(chosen[1].upper())
            self.bg_mode_var.set("color")
            self._mark_dirty()

    def _refresh_devices(self) -> None:
        try:
            self.device_map, labels, default_label = list_input_devices()
        except Exception as error:
            messagebox.showerror(APP_TITLE, f"Не удалось получить список микрофонов:\n{error}")
            return

        self.device_combo["values"] = labels
        if labels and self.device_var.get() not in self.device_map:
            self.device_var.set(default_label or labels[0])
        if not labels:
            self.status_var.set("Микрофоны не найдены.")

    def _selected_device(self) -> InputDevice:
        if self.device_var.get() not in self.device_map:
            raise RuntimeError("Сначала выбери микрофон.")
        return self.device_map[self.device_var.get()]

    def _start_audio(self) -> None:
        try:
            device = self._selected_device()
            self.monitor.start(device)
        except Exception as error:
            messagebox.showerror(APP_TITLE, f"Не удалось запустить микрофон:\n{error}")
            self.status_var.set("Ошибка запуска микрофона.")
            return
        self.last_voice = time.monotonic()
        self.status_var.set(f"Микрофон активен: {device.name}")
        self.hero_signal_var.set("МИК АКТИВЕН")

    def _stop_audio(self) -> None:
        self.monitor.stop()
        self.level_bar["value"] = 0
        self.level_text.set("0 / 100")
        self.status_var.set("Микрофон остановлен.")
        self.hero_signal_var.set("МИК ВЫКЛ")
        if self.current_frame != "idle":
            self.current_frame = "idle"
            self.talk_frame = "talk_a"
            self._render()

    def _autostart(self) -> None:
        if self.device_var.get() and not self.monitor.running:
            self._start_audio()

    def scene_size(self) -> tuple[int, int]:
        width = parse_int(self.width_var.get(), 1280, 320, 4096)
        height = parse_int(self.height_var.get(), 720, 240, 4096)
        self.scene_size_cache = (width, height)
        return width, height

    def _safe_scene_size(self) -> tuple[int, int]:
        return self.scene_size()

    def _apply_preset(self, event=None) -> None:
        del event
        width, height = SCENE_PRESETS[self.preset_var.get()]
        self.width_var.set(str(width))
        self.height_var.set(str(height))
        self._mark_dirty()

    def _open_obs(self) -> None:
        width, height = self.scene_size()
        if self.obs_win is None or not self.obs_win.winfo_exists():
            self.obs_win = OBSWindow(self)
        else:
            self.obs_win.sync()
            self.obs_win.deiconify()
            self.obs_win.lift()
        self.obs_text.set(f"OBS-окно открыто: {width} x {height}. Используй захват окна в OBS.")

    def _close_obs(self) -> None:
        if self.obs_win is not None and self.obs_win.winfo_exists():
            self.obs_win.destroy()
        self.obs_win = None
        self.obs_text.set("OBS-окно закрыто.")

    def _sync_obs(self) -> None:
        if self.obs_win is not None and self.obs_win.winfo_exists():
            self.obs_win.sync()

    def _copy_overlay_url(self) -> None:
        url = self.overlay_url_var.get().strip()
        if not url:
            return
        self.clipboard_clear()
        self.clipboard_append(url)
        self.obs_text.set("Ссылка сцены скопирована.")

    def _copy_chat_browser_url(self) -> None:
        url = self.chat_browser_url_var.get().strip()
        if not url:
            self.chat_text.set("Адрес источника чата пока недоступен.")
            return
        self.clipboard_clear()
        self.clipboard_append(url)
        self.chat_text.set("Адрес кастомного чата скопирован.")

    def _open_chat_url(self) -> None:
        raw = self.chat_url_var.get().strip()
        if not raw:
            return
        channel = extract_twitch_channel(raw)
        if channel and "twitch.tv" not in raw.lower():
            webbrowser.open_new(f"https://www.twitch.tv/popout/{channel}/chat?popout=")
            return
        try:
            url = normalize_url(raw)
        except Exception as error:
            messagebox.showerror(APP_TITLE, str(error))
            return
        webbrowser.open_new(url)

    def _obs_help_text(self) -> str:
        width, height = self._safe_scene_size()
        return (
            "БЫСТРЫЙ СТАРТ\n"
            f"1. Адрес локальной сцены: {self.overlay_url_var.get()}\n"
            f"2. Размер сцены: {width} x {height}\n"
            f"3. Отдельный адрес чата: {self.chat_browser_url_var.get()}\n"
            "4. Для чистой прозрачности используй режим 'Прозрачный'.\n"
            "5. Для чата можно вставить ссылку Twitch или просто имя канала.\n"
            "6. В OBS используй локальный /chat, а не прямую страницу Twitch.\n"
            "7. Если хочешь более стабильное подключение, укажи логин Twitch и токен доступа во вкладке 'Чат'.\n"
            "8. Если видишь consent Twitch — значит открылся не кастомный рендер.\n"
        )

    def _update_help_textbox(self) -> None:
        if self.help_textbox is None:
            return
        self.help_textbox.configure(state="normal")
        self.help_textbox.delete("1.0", "end")
        self.help_textbox.insert("1.0", self._obs_help_text())
        self.help_textbox.configure(state="disabled")

    def _show_help_tab(self) -> None:
        self._select_control_page("help")

    def _update_preset_note(self, event=None) -> None:
        del event
        pack = INTERNET_PRESET_PACKS.get(self.internet_pack_var.get(), INTERNET_PRESET_PACKS["Ночной грид"])
        self.preset_note_var.set(str(pack.get("note", "")))

    def _apply_stream_preset(self, event=None) -> None:
        del event
        pack = INTERNET_PRESET_PACKS.get(self.internet_pack_var.get(), INTERNET_PRESET_PACKS["Ночной грид"])
        moment = self.stream_moment_var.get()
        settings = pack["moments"].get(moment, pack["moments"]["Геймплей"])

        self.scene_style_var.set(str(pack["scene_style"]))
        self.chat_style_var.set(str(pack["chat_style"]))
        self.anchor_var.set(str(settings["anchor"]))
        self.scale_var.set(float(settings["scale"]))
        self.margin_x_var.set(float(settings["margin_x"]))
        self.margin_y_var.set(float(settings["margin_y"]))
        self.bg_mode_var.set(str(settings["bg_mode"]))
        self.bg_color_var.set(str(settings["bg_color"]))
        self.chat_side_var.set(str(settings["chat_side"]))
        self.chat_width_var.set(float(settings["chat_width"]))

        self._set_scale_text(str(self.scale_var.get()))
        self._set_margin_x_text(str(self.margin_x_var.get()))
        self._set_margin_y_text(str(self.margin_y_var.get()))
        self._set_chat_width_text(str(self.chat_width_var.get()))
        self._update_preset_note()
        self._refresh_chat_overlay_cache()
        self._mark_dirty()

    def _refresh_chat_overlay_cache(self) -> None:
        raw = self.chat_url_var.get().strip()
        twitch_channel = extract_twitch_channel(raw) or ""

        self.chat_twitch_channel = twitch_channel
        width_percent = clamp(float(self.chat_width_var.get()), 24.0, 42.0)
        auth_username = self.chat_auth_user_var.get().strip()
        auth_token = self.chat_auth_token_var.get().strip()

        self.chat_overlay_config_cache = build_chat_config(
            style_name=self.chat_style_var.get().strip() or "Аврора",
            side_name=self.chat_side_var.get().strip() or "Справа",
            width_percent=width_percent,
            twitch_channel=twitch_channel,
            irc_username=auth_username,
            irc_token=auth_token,
        )

        if twitch_channel:
            if auth_username and auth_token:
                self.chat_text.set(
                    f"Канал Twitch распознан: {twitch_channel}. Чат пойдет через авторизацию пользователя {auth_username}. "
                    "Используй локальный адрес источника чата в OBS."
                )
                self.hero_chat_var.set(f"{twitch_channel} · АВТОР")
            else:
                self.chat_text.set(
                    f"Канал Twitch распознан: {twitch_channel}. Чат сможет подключиться анонимно, "
                    "но для максимальной стабильности лучше добавить логин и токен доступа."
                )
                self.hero_chat_var.set(f"{twitch_channel} · АНОН")
        elif raw:
            self.chat_text.set("Пока поддерживается канал Twitch, ссылка на канал или ссылка на чат.")
            self.hero_chat_var.set("Адрес Twitch")
        else:
            self.chat_text.set("Вставь канал Twitch, ссылку на канал или чат Twitch.")
            self.hero_chat_var.set("Чат не подключен")

    def chat_overlay_config_json(self) -> str:
        return json.dumps(self.chat_overlay_config_cache, ensure_ascii=False)

    def _start_overlay_server(self) -> None:
        port = OVERLAY_PORT_START
        while port < OVERLAY_PORT_START + 25:
            try:
                self.overlay_server = OverlayHTTPServer(("127.0.0.1", port), self)
                self.overlay_port = port
                break
            except OSError:
                port += 1

        if self.overlay_server is None:
            self.overlay_url_var.set("Не удалось поднять локальный сервер")
            self.deck_overlay_var.set("ошибка сцены")
            self.deck_chat_var.set("ошибка чата")
            return

        self.overlay_url_var.set(f"http://127.0.0.1:{self.overlay_port}/overlay")
        self.chat_browser_url_var.set(f"http://127.0.0.1:{self.overlay_port}/chat")
        self.deck_overlay_var.set(f"127.0.0.1:{self.overlay_port}")
        self.deck_chat_var.set(f"127.0.0.1:{self.overlay_port}/chat")

        self.overlay_thread = threading.Thread(
            target=self.overlay_server.serve_forever,
            name="mopsyan-overlay-server",
            daemon=True,
        )
        self.overlay_thread.start()

    def _stop_overlay_server(self) -> None:
        if self.overlay_server is not None:
            self.overlay_server.shutdown()
            self.overlay_server.server_close()
            self.overlay_server = None
        if self.overlay_thread is not None and self.overlay_thread.is_alive():
            self.overlay_thread.join(timeout=1.0)
            self.overlay_thread = None

    def _reload_media(self, show_errors: bool = True) -> None:
        errors = self.renderer.load_assets(
            {key: self.image_vars[key].get() for key in self.image_vars},
            self.bg_path_var.get(),
        )
        if errors and show_errors:
            messagebox.showerror(APP_TITLE, "Проблемы при загрузке файлов:\n\n" + "\n".join(errors))
        self._mark_dirty()

    def _scene_params(self) -> SceneRenderParams:
        return SceneRenderParams(
            bg_mode=self.bg_mode_var.get(),
            bg_color=self.bg_color_var.get(),
            anchor_label=self.anchor_var.get(),
            scale_percent=float(self.scale_var.get()),
            margin_x=float(self.margin_x_var.get()),
            margin_y=float(self.margin_y_var.get()),
            current_frame=self.current_frame,
            speaking_energy=self._speaking_energy(),
            scene_style=self.scene_style_var.get(),
            preset_label=self.internet_pack_var.get(),
            moment_label=self.stream_moment_var.get(),
            show_scene_frame=False,
            show_scene_label=False,
            show_scene_ribbon=False,
        )

    def build_scene(self, size: tuple[int, int]):
        return self.renderer.build_scene(size, self._scene_params())

    def _preview_size(self) -> tuple[int, int]:
        if self.preview_host is None:
            return PREVIEW_FALLBACK
        width = self.preview_host.winfo_width()
        height = self.preview_host.winfo_height()
        if width < 80 or height < 80:
            return PREVIEW_FALLBACK
        return width, height

    def _chat_preview_size(self) -> tuple[int, int]:
        if self.chat_preview_host is None:
            return CHAT_PREVIEW_FALLBACK
        width = self.chat_preview_host.winfo_width()
        height = self.chat_preview_host.winfo_height()
        if width < 120 or height < 120:
            return CHAT_PREVIEW_FALLBACK
        return width, height

    def _speaking_energy(self) -> float:
        if not self.monitor.running:
            return 0.0
        return max(0.0, min(1.0, self.last_level_value / 100.0))

    def _preview_font(self, size: int, bold: bool = False) -> ImageFont.ImageFont:
        key = (max(10, int(size)), bool(bold))
        if key in self._font_cache:
            return self._font_cache[key]

        fonts_dir = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
        preferred = ["seguisb.ttf", "arialbd.ttf"] if bold else ["segoeui.ttf", "arial.ttf"]
        candidates = [fonts_dir / name for name in preferred] + preferred

        font = None
        for candidate in candidates:
            try:
                font = ImageFont.truetype(str(candidate), key[0])
                break
            except OSError:
                continue

        if font is None:
            font = ImageFont.load_default()

        self._font_cache[key] = font
        return font

    def _compose_scene_preview(self, full_scene, size: tuple[int, int]):
        from PIL import Image, ImageFilter

        width, height = size
        width = max(80, int(width))
        height = max(80, int(height))

        if self.bg_mode_var.get() == "transparent":
            preview_bg = self.renderer.preview_checker((width, height))
            glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            glow_draw = ImageDraw.Draw(glow)
            glow_draw.ellipse((-90, -40, int(width * 0.54), int(height * 1.08)), fill=(52, 88, 150, 52))
            glow_draw.ellipse((int(width * 0.48), -20, width + 70, int(height * 0.78)), fill=(95, 233, 255, 34))
            preview_bg.alpha_composite(glow.filter(ImageFilter.GaussianBlur(36)))
        else:
            preview_bg = ImageOps.fit(full_scene, (width, height), Image.LANCZOS)
            preview_bg = preview_bg.filter(ImageFilter.GaussianBlur(18))
            preview_bg.alpha_composite(Image.new("RGBA", (width, height), (7, 11, 19, 124)))

        scene_layer = ImageOps.contain(full_scene, (width, height), Image.LANCZOS)
        offset = ((width - scene_layer.width) // 2, (height - scene_layer.height) // 2)
        preview_bg.alpha_composite(scene_layer, offset)

        return preview_bg

    def _render_chat_preview(self) -> None:
        if self.chat_preview is None:
            return

        from PIL import Image, ImageDraw, ImageFilter

        width, height = self._chat_preview_size()
        image = self.renderer.vertical_gradient((width, height), (7, 11, 19), (17, 26, 39))
        overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)

        accent = self.chat_overlay_config_cache.get("accent", "#8EF7D4")
        accent2 = self.chat_overlay_config_cache.get("accent2", "#8EA8FF")
        accent3 = self.chat_overlay_config_cache.get("accent3", "#E28EFF")
        try:
            acc = ImageColor.getrgb(str(accent))
            acc2 = ImageColor.getrgb(str(accent2))
            acc3 = ImageColor.getrgb(str(accent3))
        except ValueError:
            acc = (142, 247, 212)
            acc2 = (142, 168, 255)
            acc3 = (226, 142, 255)

        overlay_draw.ellipse((-60, -40, int(width * 0.55), int(height * 0.95)), fill=acc + (54,))
        overlay_draw.ellipse((int(width * 0.42), -20, width + 60, int(height * 0.64)), fill=acc2 + (48,))
        overlay_draw.ellipse((int(width * 0.34), int(height * 0.52), width + 40, height + 40), fill=acc3 + (30,))
        image.alpha_composite(overlay.filter(ImageFilter.GaussianBlur(46)))

        panel_box = (14, 14, width - 14, height - 14)
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle(panel_box, radius=28, fill=(11, 18, 28, 232), outline=acc, width=2)
        draw.rounded_rectangle((14, 14, width - 14, 20), radius=6, fill=acc)

        title_font = self._preview_font(13, True)
        body_font = self._preview_font(12, False)
        chip_font = self._preview_font(10, True)

        draw.rounded_rectangle((24, 28, 60, 64), radius=14, fill=(255, 255, 255, 18))
        draw.ellipse((35, 39, 49, 53), fill=acc)
        draw.text((72, 28), "ЧАТ TWITCH // СТУДИЯ", font=title_font, fill=(245, 248, 255, 255))
        draw.text(
            (72, 48),
            str(self.chat_overlay_config_cache.get("subtitle", "Twitch • демо")),
            font=body_font,
            fill=(185, 199, 219, 255),
        )

        auth_mode = "АВТОР" if self.chat_overlay_config_cache.get("auth_mode") == "token" else "АНОН"
        chip_w = 72 if auth_mode == "АВТОР" else 70
        draw.rounded_rectangle((width - chip_w - 26, 30, width - 26, 58), radius=14, fill=acc2 + (220,))
        draw.text((width - chip_w - 10, 38), auth_mode, font=chip_font, fill=(7, 12, 18, 255))

        samples = [
            ("alex", "caster", "Это уже выглядит как дорогой чат.", acc),
            ("mira", "mod", "Карточки и анимация стали живее.", acc2),
            ("fox", "", "И больше не похоже на iframe.", acc3),
        ]

        y = 84
        for name, badge, text, color in samples:
            draw.rounded_rectangle((24, y, width - 24, y + 48), radius=18, fill=(255, 255, 255, 16))
            draw.rounded_rectangle((34, y + 8, 70, y + 40), radius=12, fill=color)
            draw.text((81, y + 7), name, font=title_font, fill=color)
            if badge:
                badge_x = min(width - 110, 142)
                draw.rounded_rectangle((badge_x, y + 7, badge_x + 52, y + 24), radius=8, fill=(255, 255, 255, 24))
                draw.text((badge_x + 8, y + 10), badge.upper(), font=chip_font, fill=(245, 248, 255, 255))
            draw.text((81, y + 24), text, font=body_font, fill=(245, 248, 255, 255))
            y += 56

        self.chat_preview_photo = ImageTk.PhotoImage(image)
        self.chat_preview.configure(image=self.chat_preview_photo, text="")
        self.chat_preview.image = self.chat_preview_photo
        self.last_chat_preview_refresh = time.monotonic()
        self.chat_preview_dirty = False

    def _draw_voice_visualizer(self, level: float) -> None:
        if self.voice_canvas is None:
            return

        import math

        canvas = self.voice_canvas
        width = max(20, canvas.winfo_width())
        height = max(20, canvas.winfo_height())
        canvas.delete("all")
        canvas.configure(bg=self.colors["input"], highlightbackground=self.colors["border"])

        bars = 18
        gap = 4
        bar_width = max(6, (width - (bars + 1) * gap) // bars)
        phase = time.monotonic() * 4.5
        normalized = max(0.02, min(1.0, level / 100.0))

        for index in range(bars):
            wave = (math.sin(phase + index * 0.55) + 1.0) * 0.5
            intensity = min(1.0, normalized * 1.45 + wave * 0.35)
            bar_height = int(8 + intensity * (height - 14))
            x0 = gap + index * (bar_width + gap)
            y0 = height - bar_height - 4
            x1 = x0 + bar_width
            y1 = height - 4
            color = self.colors["accent"] if intensity > 0.52 else self.colors["mint"]
            canvas.create_rectangle(x0, y0, x1, y1, fill=color, outline="")

    def _schedule_render(self, delay_ms: int = 16) -> None:
        self.scene_dirty = True
        if self._render_after_id is not None:
            self.after_cancel(self._render_after_id)
        self._render_after_id = self.after(delay_ms, self._flush_render)

    def _flush_render(self) -> None:
        self._render_after_id = None
        self._update_guidance()
        self._render()

    def _mark_dirty(self) -> None:
        self.scene_dirty = True
        self.chat_preview_dirty = True
        if self.obs_win is not None and self.obs_win.winfo_exists():
            self.obs_win.sync()
        self._schedule_render()

    def _render(self) -> None:
        render_started = time.monotonic()
        window_visible = self.state() != "iconic" and bool(self.winfo_viewable())

        scene_size = self._safe_scene_size()
        full_scene = self.build_scene(scene_size)
        self._overlay_png = self.renderer.image_to_png_bytes(full_scene)

        if window_visible:
            preview = self._compose_scene_preview(full_scene, self._preview_size())
            self.preview_photo = ImageTk.PhotoImage(preview)
            if self.preview is not None:
                self.preview.configure(image=self.preview_photo, text="")
                self.preview.image = self.preview_photo
        self.overlay_state.update(
            overlay_html=build_overlay_html("/frame-styled.png"),
            clean_overlay_html=build_overlay_html("/frame.png"),
            chat_html=build_chat_overlay_html(self.chat_overlay_config_cache),
            chat_config_json=self.chat_overlay_config_json(),
            overlay_png=self._overlay_png,
            clean_overlay_png=self._overlay_png,
        )

        if window_visible and self.chat_preview is not None:
            if self.chat_preview_dirty or (render_started - self.last_chat_preview_refresh >= 0.4):
                self._render_chat_preview()
        if window_visible:
            self._draw_voice_visualizer(self.last_level_value)

        if self.obs_win is not None and self.obs_win.winfo_exists():
            self.obs_win.refresh()

        self.last_render_level = self.last_level_value
        self.last_visual_refresh = render_started
        self.scene_dirty = False

    def _update_guidance(self) -> None:
        width, height = self._safe_scene_size()
        mode = self.bg_mode_var.get()
        mode_label = {
            "transparent": "прозрачный фон",
            "image": "фоновая картинка",
            "color": "chroma-цвет",
        }.get(mode, "сцена")

        if mode == "transparent":
            capture_text = "Сейчас лучший режим для OBS: локальный адрес сцены с настоящей прозрачностью."
        elif mode == "image":
            capture_text = "Сейчас сцена с картинкой-фоном. Можно использовать локальный адрес сцены или захват окна."
        else:
            capture_text = "Сейчас сцена под хромакей. Подойдет захват окна с фильтром хромакея."

        self.capture_hint_var.set(f"{capture_text} Активный момент: {self.stream_moment_var.get()} · Пак: {self.internet_pack_var.get()}.")
        self.hero_scene_var.set(f"{self.internet_pack_var.get()} · {self.stream_moment_var.get()}")
        self.scene_meta_var.set(
            f"Стиль: {self.scene_style_var.get()} · Чат: {self.chat_style_var.get()} · Режим: {mode_label} · Сцена: {width} x {height}"
        )
        self._update_help_textbox()

    def _is_speaking(self, level: float) -> bool:
        now = time.monotonic()
        if level >= float(self.threshold_var.get()):
            self.last_voice = now
            return True
        return (now - self.last_voice) <= HANG_SECONDS

    def _tick(self) -> None:
        level, monitor_status = self.monitor.snapshot()
        self.last_level_value = level
        self.level_bar["value"] = level
        self.level_text.set(f"{level:.0f} / 100")
        if self.monitor.running:
            self.hero_signal_var.set(f"МИК {level:.0f}%")
        elif self.hero_signal_var.get() != "МИК ВЫКЛ":
            self.hero_signal_var.set("МИК ВЫКЛ")

        if monitor_status:
            self.status_var.set(f"Статус микрофона: {monitor_status}")

        changed = False
        if not self.monitor.running:
            if self.current_frame != "idle":
                self.current_frame = "idle"
                changed = True
        else:
            if self._is_speaking(level):
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

        needs_visual_refresh = changed or self.scene_dirty or self.chat_preview_dirty
        if not needs_visual_refresh and self.monitor.running:
            level_delta = abs(level - self.last_render_level)
            if (time.monotonic() - self.last_visual_refresh) >= 0.09 and (level_delta >= 2.2 or self.current_frame != "idle"):
                needs_visual_refresh = True

        if needs_visual_refresh:
            if time.monotonic() < self._resize_cooldown_until:
                self._schedule_render(72)
            else:
                self._render()

        self.after(POLL_MS, self._tick)

    def _on_control_tab_changed(self, event=None) -> None:
        del event
        self.chat_preview_dirty = True
        self.after_idle(self._sync_control_scrollregion)
        if self.control_scroll_canvas is not None:
            self.control_scroll_canvas.yview_moveto(0.0)

    def _on_chat_url_change(self, *args) -> None:
        del args
        self._refresh_chat_overlay_cache()
        self.chat_preview_dirty = True
        self._schedule_render(30)

    def _on_setting_changed(self, *args) -> None:
        del args
        self._refresh_chat_overlay_cache()
        self._schedule_render(40)

    def _close(self) -> None:
        self.monitor.stop()
        self.unbind_all("<MouseWheel>")
        self.unbind("<Configure>")

        if self._render_after_id is not None:
            self.after_cancel(self._render_after_id)
            self._render_after_id = None
        if self._layout_after_id is not None:
            self.after_cancel(self._layout_after_id)
            self._layout_after_id = None

        if self.obs_win is not None and self.obs_win.winfo_exists():
            self.obs_win.destroy()

        self._stop_overlay_server()
        self.destroy()
