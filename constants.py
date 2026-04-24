from __future__ import annotations

APP_TITLE = "mopsyan_sysan"

POLL_MS = 50
ANIM_MS = 140
HANG_SECONDS = 0.18

CHROMA_DEFAULT = "#00FF66"
TRANSPARENT_KEY = "#FF00FF"

CHAT_FILE = "obs_chat_overlay.html"

PREVIEW_FALLBACK = (900, 520)
CHAT_PREVIEW_FALLBACK = (420, 220)

OVERLAY_PORT_START = 8765
OVERLAY_REFRESH_MS = 90

FILE_TYPES = [
    ("Image files", "*.png *.jpg *.jpeg *.bmp *.gif *.webp"),
    ("All files", "*.*"),
]

SCENE_PRESETS = {
    "1280 x 720 (HD)": (1280, 720),
    "1920 x 1080 (Full HD)": (1920, 1080),
    "1080 x 1920 (Vertical)": (1080, 1920),
    "1600 x 900": (1600, 900),
}

SCENE_STYLE_OPTIONS = (
    "Кибер-пульс",
    "Аврора",
    "Нуар",
    "Сансет",
    "Найт-грид",
    "Арена-core",
    "Лаунж",
    "Пейпер",
)

ANCHORS = {
    "Справа снизу": "right",
    "Слева снизу": "left",
    "По центру": "center",
}

CHAT_STYLE_OPTIONS = ("Аврора", "Неон", "Стекло", "Эмбер", "Нуар", "Найт-грид", "Лаунж", "Пейпер", "Арена")
CHAT_SIDE_OPTIONS = ("Справа", "Слева")

INTERNET_PRESET_OPTIONS = ("Ночной грид", "Студийный лаунж", "Арена", "Уютный коллаж")
STREAM_MOMENT_OPTIONS = ("Старт", "Геймплей", "Общение", "Перерыв", "Хайп", "Финал")

INTERNET_PRESET_PACKS = {
    "Ночной грид": {
        "note": "Футуристичный пакет для стартов, геймплея и ярких моментов с холодным светом и технологичным настроением.",
        "scene_style": "Найт-грид",
        "chat_style": "Найт-грид",
        "moments": {
            "Старт": {"anchor": "По центру", "scale": 70.0, "margin_x": 0.0, "margin_y": 12.0, "bg_mode": "transparent", "bg_color": "#0B1022", "chat_side": "Справа", "chat_width": 30.0},
            "Геймплей": {"anchor": "Справа снизу", "scale": 52.0, "margin_x": 30.0, "margin_y": 16.0, "bg_mode": "transparent", "bg_color": "#0B1022", "chat_side": "Справа", "chat_width": 27.0},
            "Общение": {"anchor": "По центру", "scale": 68.0, "margin_x": 0.0, "margin_y": 8.0, "bg_mode": "transparent", "bg_color": "#0B1022", "chat_side": "Справа", "chat_width": 35.0},
            "Перерыв": {"anchor": "Слева снизу", "scale": 48.0, "margin_x": 30.0, "margin_y": 18.0, "bg_mode": "transparent", "bg_color": "#0B1022", "chat_side": "Слева", "chat_width": 30.0},
            "Хайп": {"anchor": "По центру", "scale": 74.0, "margin_x": 0.0, "margin_y": 0.0, "bg_mode": "transparent", "bg_color": "#09101D", "chat_side": "Слева", "chat_width": 26.0},
            "Финал": {"anchor": "По центру", "scale": 60.0, "margin_x": 0.0, "margin_y": 12.0, "bg_mode": "transparent", "bg_color": "#0A1220", "chat_side": "Справа", "chat_width": 29.0},
        },
    },
    "Студийный лаунж": {
        "note": "Спокойный студийный пакет для общения и мягких сцен с более теплым, камерным светом.",
        "scene_style": "Лаунж",
        "chat_style": "Лаунж",
        "moments": {
            "Старт": {"anchor": "По центру", "scale": 64.0, "margin_x": 0.0, "margin_y": 10.0, "bg_mode": "color", "bg_color": "#13263A", "chat_side": "Справа", "chat_width": 31.0},
            "Геймплей": {"anchor": "Справа снизу", "scale": 50.0, "margin_x": 28.0, "margin_y": 16.0, "bg_mode": "transparent", "bg_color": "#13263A", "chat_side": "Справа", "chat_width": 28.0},
            "Общение": {"anchor": "По центру", "scale": 72.0, "margin_x": 0.0, "margin_y": 4.0, "bg_mode": "color", "bg_color": "#10273B", "chat_side": "Справа", "chat_width": 38.0},
            "Перерыв": {"anchor": "По центру", "scale": 56.0, "margin_x": 0.0, "margin_y": 14.0, "bg_mode": "color", "bg_color": "#0F2233", "chat_side": "Слева", "chat_width": 30.0},
            "Хайп": {"anchor": "По центру", "scale": 69.0, "margin_x": 0.0, "margin_y": 6.0, "bg_mode": "transparent", "bg_color": "#12283D", "chat_side": "Справа", "chat_width": 33.0},
            "Финал": {"anchor": "По центру", "scale": 58.0, "margin_x": 0.0, "margin_y": 14.0, "bg_mode": "color", "bg_color": "#102135", "chat_side": "Справа", "chat_width": 32.0},
        },
    },
    "Арена": {
        "note": "Более агрессивный пакет под геймплей, клипы и соревновательные моменты.",
        "scene_style": "Арена-core",
        "chat_style": "Арена",
        "moments": {
            "Старт": {"anchor": "По центру", "scale": 68.0, "margin_x": 0.0, "margin_y": 12.0, "bg_mode": "color", "bg_color": "#101522", "chat_side": "Слева", "chat_width": 30.0},
            "Геймплей": {"anchor": "Справа снизу", "scale": 49.0, "margin_x": 34.0, "margin_y": 18.0, "bg_mode": "transparent", "bg_color": "#101522", "chat_side": "Слева", "chat_width": 26.0},
            "Общение": {"anchor": "По центру", "scale": 64.0, "margin_x": 0.0, "margin_y": 8.0, "bg_mode": "transparent", "bg_color": "#111827", "chat_side": "Справа", "chat_width": 34.0},
            "Перерыв": {"anchor": "Слева снизу", "scale": 46.0, "margin_x": 26.0, "margin_y": 18.0, "bg_mode": "color", "bg_color": "#0E1420", "chat_side": "Слева", "chat_width": 28.0},
            "Хайп": {"anchor": "По центру", "scale": 76.0, "margin_x": 0.0, "margin_y": 0.0, "bg_mode": "transparent", "bg_color": "#10131F", "chat_side": "Слева", "chat_width": 24.0},
            "Финал": {"anchor": "По центру", "scale": 58.0, "margin_x": 0.0, "margin_y": 12.0, "bg_mode": "color", "bg_color": "#0D1320", "chat_side": "Справа", "chat_width": 28.0},
        },
    },
    "Уютный коллаж": {
        "note": "Теплый уютный пакет под старт, паузы и спокойные промежуточные сцены.",
        "scene_style": "Пейпер",
        "chat_style": "Пейпер",
        "moments": {
            "Старт": {"anchor": "По центру", "scale": 66.0, "margin_x": 0.0, "margin_y": 12.0, "bg_mode": "color", "bg_color": "#D9C9B3", "chat_side": "Справа", "chat_width": 30.0},
            "Геймплей": {"anchor": "Справа снизу", "scale": 50.0, "margin_x": 24.0, "margin_y": 16.0, "bg_mode": "transparent", "bg_color": "#D9C9B3", "chat_side": "Справа", "chat_width": 27.0},
            "Общение": {"anchor": "По центру", "scale": 70.0, "margin_x": 0.0, "margin_y": 6.0, "bg_mode": "color", "bg_color": "#DCCDB7", "chat_side": "Слева", "chat_width": 37.0},
            "Перерыв": {"anchor": "По центру", "scale": 54.0, "margin_x": 0.0, "margin_y": 14.0, "bg_mode": "color", "bg_color": "#D5C2A7", "chat_side": "Слева", "chat_width": 29.0},
            "Хайп": {"anchor": "По центру", "scale": 67.0, "margin_x": 0.0, "margin_y": 8.0, "bg_mode": "color", "bg_color": "#D6C4AF", "chat_side": "Справа", "chat_width": 31.0},
            "Финал": {"anchor": "По центру", "scale": 57.0, "margin_x": 0.0, "margin_y": 12.0, "bg_mode": "color", "bg_color": "#CEB79D", "chat_side": "Справа", "chat_width": 30.0},
        },
    },
}

DEFAULT_COLORS = {
    "bg": "#070A11",
    "card": "#0F1623",
    "card2": "#141E30",
    "card3": "#172338",
    "input": "#121C2B",
    "border": "#23314A",
    "text": "#F4F8FF",
    "muted": "#90A4C3",
    "accent": "#69E6FF",
    "accent2": "#FF6EA7",
    "gold": "#FFD07D",
    "mint": "#7EF2C7",
}
