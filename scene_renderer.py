from __future__ import annotations

import io
import math
import os
import time
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageColor, ImageDraw, ImageFilter, ImageFont, ImageOps

from constants import ANCHORS, CHROMA_DEFAULT


SCENE_STYLE_PALETTES: dict[str, dict[str, tuple[int, int, int]]] = {
    "Кибер-пульс": {
        "accent": (99, 231, 255),
        "accent2": (255, 102, 169),
        "accent3": (255, 210, 120),
        "line": (88, 156, 255),
        "shadow": (7, 10, 18),
        "top": (7, 15, 32),
        "bottom": (16, 28, 54),
    },
    "Аврора": {
        "accent": (125, 255, 230),
        "accent2": (127, 165, 255),
        "accent3": (219, 126, 255),
        "line": (127, 215, 255),
        "shadow": (5, 16, 20),
        "top": (6, 24, 28),
        "bottom": (17, 39, 50),
    },
    "Нуар": {
        "accent": (240, 203, 133),
        "accent2": (123, 176, 255),
        "accent3": (255, 120, 120),
        "line": (153, 170, 194),
        "shadow": (8, 10, 14),
        "top": (18, 20, 28),
        "bottom": (10, 12, 18),
    },
    "Сансет": {
        "accent": (255, 142, 107),
        "accent2": (255, 204, 110),
        "accent3": (255, 117, 171),
        "line": (255, 185, 110),
        "shadow": (22, 10, 14),
        "top": (54, 22, 34),
        "bottom": (20, 10, 18),
    },
    "Найт-грид": {
        "accent": (95, 241, 255),
        "accent2": (255, 92, 196),
        "accent3": (146, 116, 255),
        "line": (67, 196, 255),
        "shadow": (7, 10, 19),
        "top": (4, 10, 30),
        "bottom": (13, 20, 46),
    },
    "Арена-core": {
        "accent": (255, 92, 92),
        "accent2": (85, 220, 255),
        "accent3": (255, 211, 92),
        "line": (164, 196, 255),
        "shadow": (8, 10, 17),
        "top": (15, 18, 30),
        "bottom": (10, 12, 22),
    },
    "Лаунж": {
        "accent": (126, 239, 214),
        "accent2": (255, 197, 124),
        "accent3": (126, 179, 255),
        "line": (104, 230, 255),
        "shadow": (8, 15, 24),
        "top": (7, 28, 38),
        "bottom": (11, 21, 33),
    },
    "Пейпер": {
        "accent": (194, 111, 83),
        "accent2": (80, 133, 121),
        "accent3": (227, 173, 105),
        "line": (120, 98, 89),
        "shadow": (47, 35, 28),
        "top": (214, 198, 178),
        "bottom": (188, 170, 150),
    },
}


def mix_rgb(left: tuple[int, int, int], right: tuple[int, int, int], ratio: float) -> tuple[int, int, int]:
    ratio = max(0.0, min(1.0, ratio))
    return tuple(int(a + (b - a) * ratio) for a, b in zip(left, right))


@dataclass
class SceneRenderParams:
    bg_mode: str
    bg_color: str
    anchor_label: str
    scale_percent: float
    margin_x: float
    margin_y: float
    current_frame: str
    speaking_energy: float
    scene_style: str
    preset_label: str
    moment_label: str
    show_scene_frame: bool
    show_scene_label: bool
    show_scene_ribbon: bool


class SceneRenderer:
    def __init__(self) -> None:
        self.images: dict[str, Image.Image | None] = {
            "idle": None,
            "talk_a": None,
            "talk_b": None,
        }
        self.background: Image.Image | None = None
        self._font_cache: dict[tuple[int, bool], ImageFont.ImageFont] = {}

    def ui_font(self, size: int, bold: bool = False) -> ImageFont.ImageFont:
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

    def defringe_alpha(self, image: Image.Image) -> Image.Image:
        rgba = image.convert("RGBA")
        pixels = rgba.load()
        width, height = rgba.size

        for y in range(height):
            for x in range(width):
                red, green, blue, alpha = pixels[x, y]
                if alpha <= 0 or alpha >= 255:
                    continue

                coverage = alpha / 255.0
                red = int(max(0, min(255, (red - 255 * (1.0 - coverage)) / coverage)))
                green = int(max(0, min(255, (green - 255 * (1.0 - coverage)) / coverage)))
                blue = int(max(0, min(255, (blue - 255 * (1.0 - coverage)) / coverage)))
                pixels[x, y] = (red, green, blue, alpha)

        alpha_channel = rgba.getchannel("A").filter(ImageFilter.MinFilter(5))
        rgba.putalpha(alpha_channel)
        return rgba

    def load_rgba(self, path_text: str) -> Image.Image | None:
        text = path_text.strip()
        if not text:
            return None
        path = Path(text)
        if not path.exists():
            raise FileNotFoundError(f"Файл не найден: {path}")
        with Image.open(path) as image:
            rgba = image.convert("RGBA").copy()
            return self.defringe_alpha(rgba)

    def load_assets(self, image_paths: dict[str, str], background_path: str) -> list[str]:
        errors: list[str] = []

        for key in self.images:
            try:
                self.images[key] = self.load_rgba(image_paths[key])
            except Exception as error:
                self.images[key] = None
                errors.append(f"{key}: {error}")

        try:
            self.background = self.load_rgba(background_path)
        except Exception as error:
            self.background = None
            if background_path.strip():
                errors.append(f"background: {error}")

        return errors

    def safe_rgb(self, value: str) -> tuple[int, int, int]:
        try:
            return ImageColor.getrgb(value.strip())
        except ValueError:
            return ImageColor.getrgb(CHROMA_DEFAULT)

    def style_palette(self, style_name: str) -> dict[str, tuple[int, int, int]]:
        return dict(SCENE_STYLE_PALETTES.get(style_name, SCENE_STYLE_PALETTES["Кибер-пульс"]))

    def avatar_pos(
        self,
        scene_size: tuple[int, int],
        avatar_size: tuple[int, int],
        anchor_label: str,
        margin_x: float,
        margin_y: float,
    ) -> tuple[int, int]:
        width, height = scene_size
        avatar_w, avatar_h = avatar_size
        mx = int(margin_x)
        my = int(margin_y)
        anchor = ANCHORS.get(anchor_label, "right")

        if anchor == "left":
            x, y = mx, height - avatar_h - my
        elif anchor == "center":
            x, y = (width - avatar_w) // 2, (height - avatar_h) // 2
        else:
            x, y = width - avatar_w - mx, height - avatar_h - my

        return max(0, x), max(0, y)

    def vertical_gradient(
        self,
        size: tuple[int, int],
        top: tuple[int, int, int],
        bottom: tuple[int, int, int],
    ) -> Image.Image:
        width, height = size
        mask = Image.new("L", (1, max(2, height)))
        mask.putdata([int(index * 255 / max(1, height - 1)) for index in range(height)])
        mask = mask.resize(size)
        base = Image.new("RGBA", size, top + (255,))
        overlay = Image.new("RGBA", size, bottom + (255,))
        return Image.composite(overlay, base, mask)

    def blurred_blob(
        self,
        size: tuple[int, int],
        bbox: tuple[int, int, int, int],
        color: tuple[int, int, int],
        alpha: int,
        blur_radius: int,
    ) -> Image.Image:
        layer = Image.new("RGBA", size, (0, 0, 0, 0))
        ImageDraw.Draw(layer).ellipse(bbox, fill=color + (max(0, min(255, alpha)),))
        return layer.filter(ImageFilter.GaussianBlur(max(1, blur_radius)))

    def atmospheric_overlay(
        self,
        size: tuple[int, int],
        palette: dict[str, tuple[int, int, int]],
        speaking: bool,
        energy: float,
    ) -> Image.Image:
        width, height = size
        phase = time.monotonic()
        overlay = Image.new("RGBA", size, (0, 0, 0, 0))

        overlay.alpha_composite(
            self.blurred_blob(
                size,
                (
                    int(width * 0.52),
                    int(height * 0.10),
                    int(width * 1.02),
                    int(height * 0.92),
                ),
                palette["accent2"],
                int(50 + energy * 34),
                95,
            )
        )
        overlay.alpha_composite(
            self.blurred_blob(
                size,
                (
                    int(width * -0.02),
                    int(height * (0.08 + 0.03 * math.sin(phase * 0.55))),
                    int(width * 0.55),
                    int(height * 0.82),
                ),
                palette["accent"],
                int(44 + energy * 36),
                88,
            )
        )
        overlay.alpha_composite(
            self.blurred_blob(
                size,
                (
                    int(width * 0.24),
                    int(height * 0.54),
                    int(width * 0.74),
                    int(height * 1.04),
                ),
                palette["accent3"],
                28 if speaking else 18,
                120,
            )
        )

        draw = ImageDraw.Draw(overlay)
        horizon = int(height * 0.62)
        for index in range(10):
            progress = index / 9 if index else 0
            y = horizon + int((progress**1.7) * (height - horizon))
            alpha = int(54 * (1.0 - progress))
            draw.line((0, y, width, y), fill=palette["line"] + (alpha,), width=1)

        for index in range(-6, 7):
            spread = width * 0.11 * index
            start_x = width // 2
            end_x = int(width // 2 + spread * 1.55)
            draw.line(
                (start_x, horizon, end_x, height),
                fill=palette["line"] + (20 if index else 34,),
                width=1,
            )

        sweep_y = int(height * (0.18 + 0.04 * math.sin(phase * 0.9)))
        draw.rounded_rectangle(
            (int(width * 0.08), sweep_y, int(width * 0.44), sweep_y + 2),
            radius=2,
            fill=palette["accent3"] + (58,),
        )
        draw.rounded_rectangle(
            (int(width * 0.58), sweep_y + 16, int(width * 0.92), sweep_y + 18),
            radius=2,
            fill=palette["accent"] + (44,),
        )

        vignette = Image.new("RGBA", size, palette["shadow"] + (0,))
        vignette_draw = ImageDraw.Draw(vignette)
        vignette_draw.rectangle((0, 0, width, height), fill=palette["shadow"] + (86,))
        vignette_draw.rounded_rectangle(
            (24, 18, width - 24, height - 24),
            radius=38,
            fill=(0, 0, 0, 0),
        )
        overlay.alpha_composite(vignette.filter(ImageFilter.GaussianBlur(30)))
        return overlay

    def avatar_halo(
        self,
        size: tuple[int, int],
        center: tuple[int, int],
        avatar_size: tuple[int, int],
        palette: dict[str, tuple[int, int, int]],
        energy: float,
        speaking: bool,
    ) -> Image.Image:
        width, height = size
        cx, cy = center
        avatar_w, avatar_h = avatar_size
        halo = Image.new("RGBA", size, (0, 0, 0, 0))

        radius_x = int(avatar_w * (0.58 + energy * 0.16))
        radius_y = int(avatar_h * (0.62 + energy * 0.20))
        halo.alpha_composite(
            self.blurred_blob(
                size,
                (cx - radius_x, cy - radius_y, cx + radius_x, cy + radius_y),
                palette["accent"],
                int(54 + energy * 60),
                36,
            )
        )
        halo.alpha_composite(
            self.blurred_blob(
                size,
                (
                    cx - int(radius_x * 0.76),
                    cy - int(radius_y * 0.68),
                    cx + int(radius_x * 0.96),
                    cy + int(radius_y * 0.82),
                ),
                palette["accent2"],
                int(34 + energy * 48),
                28,
            )
        )

        ring = Image.new("RGBA", size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(ring)
        pulse = 1.0 + math.sin(time.monotonic() * (3.4 if speaking else 1.8)) * (0.04 + energy * 0.06)
        outer_x = int(radius_x * pulse)
        outer_y = int(radius_y * pulse)
        draw.ellipse(
            (cx - outer_x, cy - outer_y, cx + outer_x, cy + outer_y),
            outline=palette["accent"] + (140,),
            width=max(2, int(min(width, height) * 0.0032)),
        )
        draw.ellipse(
            (
                cx - int(radius_x * 0.84),
                cy - int(radius_y * 0.84),
                cx + int(radius_x * 0.84),
                cy + int(radius_y * 0.84),
            ),
            outline=palette["accent3"] + (94,),
            width=2,
        )
        halo.alpha_composite(ring.filter(ImageFilter.GaussianBlur(1)))
        return halo

    def signal_ribbon(
        self,
        size: tuple[int, int],
        anchor_label: str,
        palette: dict[str, tuple[int, int, int]],
        energy: float,
        label: str,
    ) -> Image.Image:
        width, height = size
        ribbon = Image.new("RGBA", size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(ribbon)
        anchor = ANCHORS.get(anchor_label, "right")

        panel_width = max(180, int(width * 0.18))
        left = int(width * 0.05) if anchor == "right" else width - panel_width - int(width * 0.05)
        top = height - max(72, int(height * 0.13))
        right = left + panel_width
        bottom = top + 56

        draw.rounded_rectangle(
            (left, top, right, bottom),
            radius=20,
            fill=(9, 12, 18, 96),
            outline=palette["line"] + (54,),
            width=1,
        )
        bars = 14
        gap = 6
        usable_width = panel_width - 30
        bar_width = max(6, (usable_width - gap * (bars - 1)) // bars)
        base_y = bottom - 14
        phase = time.monotonic() * 4.6
        for index in range(bars):
            wave = (math.sin(phase + index * 0.55) + 1.0) * 0.5
            intensity = min(1.0, energy * 1.35 + wave * 0.42)
            bar_height = int(8 + intensity * 24)
            x0 = left + 16 + index * (bar_width + gap)
            y0 = base_y - bar_height
            x1 = x0 + bar_width
            color = palette["accent"] if intensity > 0.54 else palette["accent3"]
            draw.rounded_rectangle((x0, y0, x1, base_y), radius=4, fill=color + (220,))

        ribbon_font = self.ui_font(max(11, int(min(width, height) * 0.015)), True)
        draw.text((left + 16, top + 8), (label or "LIVE").upper(), font=ribbon_font, fill=palette["accent2"] + (220,))
        return ribbon.filter(ImageFilter.GaussianBlur(0))

    def scene_chrome(
        self,
        size: tuple[int, int],
        palette: dict[str, tuple[int, int, int]],
        preset_label: str,
        moment_label: str,
        bg_mode: str,
        *,
        show_frame: bool,
        show_label: bool,
    ) -> Image.Image:
        width, height = size
        chrome = Image.new("RGBA", size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(chrome)

        margin = max(18, int(min(width, height) * 0.028))
        radius = max(18, int(min(width, height) * 0.032))
        outline_alpha = 110 if bg_mode == "transparent" else 76
        panel_alpha = 118 if bg_mode == "transparent" else 92

        if show_frame:
            draw.rounded_rectangle(
                (margin, margin, width - margin, height - margin),
                radius=radius,
                outline=palette["accent"] + (outline_alpha,),
                width=2,
            )
            draw.rounded_rectangle(
                (margin + 10, margin + 10, width - margin - 10, height - margin - 10),
                radius=max(14, radius - 8),
                outline=palette["line"] + (42,),
                width=1,
            )

        if show_label:
            panel_w = max(240, int(width * 0.24))
            panel_h = max(62, int(height * 0.12))
            panel_x0 = margin + 16
            panel_y0 = margin + 16
            panel_x1 = panel_x0 + panel_w
            panel_y1 = panel_y0 + panel_h
            draw.rounded_rectangle(
                (panel_x0, panel_y0, panel_x1, panel_y1),
                radius=18,
                fill=palette["shadow"] + (panel_alpha,),
                outline=palette["accent2"] + (138,),
                width=2,
            )
            draw.rounded_rectangle((panel_x0, panel_y0, panel_x1, panel_y0 + 4), radius=4, fill=palette["accent"] + (255,))

            meta_font = self.ui_font(max(12, int(height * 0.024)), True)
            title_font = self.ui_font(max(16, int(height * 0.037)), True)
            draw.text((panel_x0 + 18, panel_y0 + 12), preset_label.upper(), font=meta_font, fill=palette["accent3"] + (235,))
            draw.text((panel_x0 + 18, panel_y0 + 30), moment_label.upper(), font=title_font, fill=(245, 248, 255, 255))

        if show_frame:
            bar_y = height - margin - 26
            draw.rounded_rectangle(
                (margin + 24, bar_y, margin + max(110, int(width * 0.16)), bar_y + 4),
                radius=3,
                fill=palette["accent"] + (178,),
            )
            draw.rounded_rectangle(
                (width - margin - max(160, int(width * 0.22)), margin + 22, width - margin - 24, margin + 28),
                radius=3,
                fill=palette["accent2"] + (140,),
            )
        return chrome

    def build_scene(self, size: tuple[int, int], params: SceneRenderParams) -> Image.Image:
        width, height = max(320, size[0]), max(240, size[1])
        speaking = params.current_frame != "idle"
        energy = max(0.0, min(1.0, params.speaking_energy))
        palette = self.style_palette(params.scene_style)

        if params.bg_mode == "transparent":
            scene = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        elif params.bg_mode == "image" and self.background is not None:
            scene = ImageOps.fit(self.background, (width, height), method=Image.LANCZOS)
            tint = self.vertical_gradient(
                (width, height),
                mix_rgb(palette["top"], palette["accent"], 0.16),
                mix_rgb(palette["bottom"], palette["accent2"], 0.18),
            )
            tint.putalpha(96)
            scene.alpha_composite(tint)
            scene.alpha_composite(self.atmospheric_overlay((width, height), palette, speaking, energy))
        else:
            bg_rgb = self.safe_rgb(params.bg_color)
            scene = self.vertical_gradient(
                (width, height),
                mix_rgb(bg_rgb, palette["top"], 0.14),
                mix_rgb(bg_rgb, palette["bottom"], 0.22),
            )
            scene.alpha_composite(self.atmospheric_overlay((width, height), palette, speaking, energy))

        avatar = self.images.get(params.current_frame)
        if avatar is None:
            return scene

        phase = time.monotonic()
        idle_breath = math.sin(phase * 1.65) * 0.018
        talk_bounce = math.sin(phase * 9.4) * (0.026 + energy * 0.05) if speaking else 0.0
        scale_mul = 1.0 + idle_breath + talk_bounce

        avatar = ImageOps.contain(
            avatar,
            (
                max(100, int(width * 0.62 * scale_mul)),
                max(100, int(height * (params.scale_percent / 100.0) * scale_mul)),
            ),
            Image.LANCZOS,
        )

        tilt = math.sin(phase * 4.2) * (2.6 + energy * 4.6) if speaking else math.sin(phase * 1.15) * 0.9
        avatar = avatar.rotate(tilt, resample=Image.BICUBIC, expand=True)

        x, y = self.avatar_pos((width, height), avatar.size, params.anchor_label, params.margin_x, params.margin_y)
        y = max(0, y - int((4 + energy * 18) * abs(math.sin(phase * 3.15))))
        center = (x + avatar.size[0] // 2, y + avatar.size[1] // 2)

        floor = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        floor_draw = ImageDraw.Draw(floor)
        floor_w = int(avatar.size[0] * 0.88)
        floor_h = max(32, int(avatar.size[1] * 0.12))
        floor_box = (
            center[0] - floor_w // 2,
            y + avatar.size[1] - floor_h // 2,
            center[0] + floor_w // 2,
            y + avatar.size[1] + floor_h // 2,
        )
        floor_draw.ellipse(floor_box, fill=palette["shadow"] + (110 if params.bg_mode == "transparent" else 146,))
        floor_draw.ellipse(
            (
                floor_box[0] + 22,
                floor_box[1] + 8,
                floor_box[2] - 22,
                floor_box[3] - 4,
            ),
            fill=palette["accent"] + (28,),
        )
        scene.alpha_composite(floor.filter(ImageFilter.GaussianBlur(22)))

        alpha = avatar.getchannel("A").filter(ImageFilter.GaussianBlur(18))
        shadow = Image.new("RGBA", avatar.size, (0, 0, 0, 0))
        shadow.putalpha(alpha.point(lambda value: int(value * (0.18 if params.bg_mode == "transparent" else 0.34))))
        scene.alpha_composite(shadow, (x + 16, y + 18))

        if params.show_scene_ribbon and params.bg_mode != "color":
            scene.alpha_composite(
                self.signal_ribbon((width, height), params.anchor_label, palette, energy, params.moment_label)
            )

        scene.alpha_composite(avatar, (x, y))

        if params.bg_mode == "image":
            flare = self.blurred_blob(
                (width, height),
                (
                    int(width * 0.72),
                    int(height * -0.12),
                    int(width * 1.08),
                    int(height * 0.32),
                ),
                palette["accent3"],
                18,
                52,
            )
            scene.alpha_composite(flare)

        if params.show_scene_frame or params.show_scene_label:
            scene.alpha_composite(
                self.scene_chrome(
                    (width, height),
                    palette,
                    params.preset_label,
                    params.moment_label,
                    params.bg_mode,
                    show_frame=params.show_scene_frame,
                    show_label=params.show_scene_label,
                )
            )

        return scene

    def preview_checker(self, size: tuple[int, int]) -> Image.Image:
        width, height = size
        image = Image.new("RGBA", size, (0, 0, 0, 0))
        tile = 28
        light = (36, 43, 56, 255)
        dark = (22, 28, 38, 255)
        for top in range(0, height, tile):
            for left in range(0, width, tile):
                color = light if ((left // tile) + (top // tile)) % 2 == 0 else dark
                block = Image.new("RGBA", (min(tile, width - left), min(tile, height - top)), color)
                image.alpha_composite(block, (left, top))
        return image

    def image_to_png_bytes(self, image: Image.Image) -> bytes:
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()
