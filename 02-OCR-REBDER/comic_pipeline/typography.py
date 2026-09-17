from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, features


@dataclass
class FittedText:
    text: str
    font: ImageFont.FreeTypeFont
    spacing: int
    bbox: tuple[int, int, int, int]
    fits: bool


def _font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    layout = ImageFont.Layout.RAQM if features.check_feature("raqm") else ImageFont.Layout.BASIC
    font = ImageFont.truetype(str(path), size=size, layout_engine=layout)
    try:
        axes = font.get_variation_axes()
        values = []
        for axis in axes:
            name = axis.get("name", b"").decode(errors="ignore").lower() if isinstance(axis.get("name"), bytes) else str(axis.get("name", "")).lower()
            values.append(max(axis["minimum"], min(axis["maximum"], 800 if "weight" in name else axis["default"])))
        if axes:
            font.set_variation_by_axes(values)
    except (AttributeError, OSError):
        pass
    return font


def _visual(text: str, direction: str) -> str:
    if direction == "rtl" and not features.check_feature("raqm"):
        import arabic_reshaper
        from bidi.algorithm import get_display
        return "\n".join(get_display(arabic_reshaper.reshape(line)) for line in text.splitlines())
    return text


def _measure(draw, text, font, spacing, direction, stroke_width):
    kwargs = {"font": font, "spacing": spacing, "stroke_width": stroke_width}
    if features.check_feature("raqm") and direction in {"rtl", "ttb"}:
        kwargs["direction"] = direction
    return draw.multiline_textbbox((0, 0), _visual(text, direction) or " ", **kwargs)


def _wrap(draw, text: str, font, width: int, spacing: int, direction: str, stroke_width: int) -> str:
    if direction == "ttb":
        return text
    words = text.split()
    if not words:
        return text
    lines, current = [], ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        box = _measure(draw, candidate, font, spacing, direction, stroke_width)
        if box[2] - box[0] <= width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return "\n".join(lines)


def fit_text(text: str, font_path: Path, width: int, height: int, minimum: int, requested: int | None, direction: str, stroke_width: int) -> FittedText:
    if direction == "ttb" and not features.check_feature("raqm"):
        text = "\n".join(text)
        direction = "ltr"
    canvas = Image.new("L", (max(1, width), max(1, height)))
    draw = ImageDraw.Draw(canvas)
    start = requested or max(minimum, min(int(height * 0.72), int(width * 0.24), 120))
    last = None
    for size in range(start, minimum - 1, -1):
        font = _font(font_path, size)
        spacing = max(1, round(size * 0.18))
        wrapped = _wrap(draw, text, font, width, spacing, direction, stroke_width)
        box = _measure(draw, wrapped, font, spacing, direction, stroke_width)
        rendered = _visual(wrapped, direction)
        fitted = FittedText(rendered, font, spacing, box, (box[2] - box[0] <= width and box[3] - box[1] <= height))
        last = fitted
        if fitted.fits:
            return fitted
    return last


def render_block(image: Image.Image, block: dict, font_path: Path, min_size: int, default_color: str, outline_enabled: bool, outline_width: int, outline_color: str) -> bool:
    from .schema import bbox_xyxy
    x1, y1, x2, y2 = bbox_xyxy(block["bbox"])
    margin = max(2, round(min(x2 - x1, y2 - y1) * 0.05))
    width, height = max(1, x2 - x1 - 2 * margin), max(1, y2 - y1 - 2 * margin)
    direction = str(block.get("direction") or "ltr").lower()
    pil_direction = "ttb" if direction == "vertical" else ("rtl" if direction == "rtl" else "ltr")
    stroke = outline_width if outline_enabled else 0
    fitted = fit_text(block["translated"], font_path, width, height, min_size, block.get("font_size"), pil_direction, stroke)
    alignment = str(block.get("alignment") or ("center" if block.get("text_type") == "dialogue" else "left")).lower()
    draw = ImageDraw.Draw(image)
    tw, th = fitted.bbox[2] - fitted.bbox[0], fitted.bbox[3] - fitted.bbox[1]
    if alignment == "right":
        px = x2 - margin - tw
    elif alignment == "center":
        px = x1 + margin + (width - tw) / 2
    else:
        px = x1 + margin
    py = y1 + margin + max(0, (height - th) / 2) - fitted.bbox[1]
    render_direction = pil_direction if features.check_feature("raqm") and pil_direction in {"rtl", "ttb"} else None
    kwargs = {}
    if render_direction:
        kwargs["direction"] = render_direction
    draw.multiline_text(
        (px, py), fitted.text, font=fitted.font, fill=block.get("text_color") or default_color,
        spacing=fitted.spacing, align=alignment if alignment in {"left", "center", "right"} else "left",
        stroke_width=stroke, stroke_fill=outline_color, **kwargs,
    )
    return fitted.fits
