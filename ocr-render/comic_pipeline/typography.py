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
            raw_name = axis.get("name", b"")
            name = raw_name.decode(errors="ignore").lower() if isinstance(raw_name, bytes) else str(raw_name).lower()
            values.append(
                max(
                    axis["minimum"],
                    min(axis["maximum"], 800 if "weight" in name else axis["default"]),
                )
            )
        if axes:
            font.set_variation_by_axes(values)
    except (AttributeError, OSError):
        pass

    return font


def _contains_arabic_script(text: str) -> bool:
    """
    True for Persian/Arabic-script text.

    `direction` stored in the OCR JSON describes the SOURCE text.  Stage 2 renders
    translated text, so using source direction here is incorrect for English -> Persian.
    """
    for ch in text:
        cp = ord(ch)
        if (
            0x0600 <= cp <= 0x06FF
            or 0x0750 <= cp <= 0x077F
            or 0x0870 <= cp <= 0x089F
            or 0x08A0 <= cp <= 0x08FF
            or 0xFB50 <= cp <= 0xFDFF
            or 0xFE70 <= cp <= 0xFEFF
        ):
            return True
    return False


def _render_direction(block: dict) -> str:
    """
    Resolve direction from the TRANSLATED string, not OCR/source metadata.

    Persian + mixed Persian/Latin => RTL base direction.
    Pure Latin/numeric text      => LTR.

    This intentionally ignores a source value such as "vertical": a Japanese/English
    source may be vertical, but the Persian translation is rendered horizontally.
    """
    translated = str(block.get("translated") or "")
    return "rtl" if _contains_arabic_script(translated) else "ltr"



def _render_orientation(block: dict) -> str:
    """
    Resolve physical text orientation independently from BiDi direction.

    Priority:
      1) explicit render_orientation override: horizontal / vertical
      2) legacy OCR metadata: direction == vertical
      3) horizontal

    `direction` from Stage 1 describes the SOURCE layout. We reuse only its
    vertical/horizontal layout hint, never its LTR/RTL value for Persian BiDi.
    """
    explicit = str(block.get("render_orientation") or "").strip().lower()

    if explicit in {"vertical", "v"}:
        return "vertical"
    if explicit in {"horizontal", "h"}:
        return "horizontal"

    source_direction = str(block.get("direction") or "").strip().lower()
    if source_direction in {"vertical", "ttb"}:
        return "vertical"

    return "horizontal"


def _vertical_rotation(block: dict) -> str:
    """
    Persian vertical text is rendered as a normal shaped RTL text block first,
    then the complete block is rotated.

    ccw (default): the logical beginning of Persian text appears toward the top.
    cw:            opposite orientation.

    JSON override:
        "vertical_rotation": "ccw"
        "vertical_rotation": "cw"
    """
    value = str(block.get("vertical_rotation") or "ccw").strip().lower()
    return "cw" if value in {"cw", "clockwise", "-90"} else "ccw"


def _visual(text: str, direction: str) -> str:
    """
    With RAQM, Pillow expects logical-order Unicode and performs BiDi + shaping itself.
    Without RAQM, prepare a visual-order string exactly once.
    """
    if direction == "rtl" and not features.check_feature("raqm"):
        import arabic_reshaper
        from bidi.algorithm import get_display

        return "\n".join(
            get_display(arabic_reshaper.reshape(line))
            for line in text.splitlines()
        )
    return text


def _layout_kwargs(direction: str) -> dict:
    """
    kwargs shared by Pillow measuring/drawing when complex layout is available.
    """
    if features.check_feature("raqm") and direction == "rtl":
        return {
            "direction": "rtl",
            "language": "fa",
        }
    if features.check_feature("raqm") and direction == "ttb":
        return {
            "direction": "ttb",
        }
    return {}


def _measure(draw, text, font, spacing, direction, stroke_width):
    kwargs = {
        "font": font,
        "spacing": spacing,
        "stroke_width": stroke_width,
        **_layout_kwargs(direction),
    }
    return draw.multiline_textbbox(
        (0, 0),
        _visual(text, direction) or " ",
        **kwargs,
    )


def _wrap(
    draw,
    text: str,
    font,
    width: int,
    spacing: int,
    direction: str,
    stroke_width: int,
) -> str:
    if direction == "ttb":
        return text

    words = text.split()
    if not words:
        return text

    lines: list[str] = []
    current = ""

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


def fit_text(
    text: str,
    font_path: Path,
    width: int,
    height: int,
    minimum: int,
    requested: int | None,
    direction: str,
    stroke_width: int,
) -> FittedText:
    canvas = Image.new("L", (max(1, width), max(1, height)))
    draw = ImageDraw.Draw(canvas)

    start = requested or max(
        minimum,
        min(int(height * 0.72), int(width * 0.24), 120),
    )

    last = None

    for size in range(start, minimum - 1, -1):
        font = _font(font_path, size)
        spacing = max(1, round(size * 0.18))
        wrapped = _wrap(draw, text, font, width, spacing, direction, stroke_width)
        box = _measure(draw, wrapped, font, spacing, direction, stroke_width)

        # IMPORTANT:
        # Keep logical-order text when RAQM is active.
        # Convert to visual order only in the BASIC-layout fallback.
        rendered = _visual(wrapped, direction)

        fitted = FittedText(
            rendered,
            font,
            spacing,
            box,
            (box[2] - box[0] <= width and box[3] - box[1] <= height),
        )
        last = fitted

        if fitted.fits:
            return fitted

    return last


def _draw_fitted_text(
    target: Image.Image,
    text: str,
    font_path: Path,
    width: int,
    height: int,
    min_size: int,
    requested_size: int | None,
    direction: str,
    alignment: str,
    fill: str,
    stroke: int,
    outline_color: str,
    margin: int,
) -> bool:
    """
    Draw one already-oriented logical text block into `target`.
    `direction` is semantic BiDi direction (rtl/ltr), not physical orientation.
    """
    inner_w = max(1, width - 2 * margin)
    inner_h = max(1, height - 2 * margin)

    fitted = fit_text(
        text,
        font_path,
        inner_w,
        inner_h,
        min_size,
        requested_size,
        direction,
        stroke,
    )

    draw = ImageDraw.Draw(target)
    tw = fitted.bbox[2] - fitted.bbox[0]
    th = fitted.bbox[3] - fitted.bbox[1]

    if alignment == "right":
        px = width - margin - tw
    elif alignment == "center":
        px = margin + (inner_w - tw) / 2
    else:
        px = margin

    py = margin + max(0, (inner_h - th) / 2) - fitted.bbox[1]

    kwargs = _layout_kwargs(direction)

    draw.multiline_text(
        (px, py),
        fitted.text,
        font=fitted.font,
        fill=fill,
        spacing=fitted.spacing,
        align=alignment if alignment in {"left", "center", "right"} else "left",
        stroke_width=stroke,
        stroke_fill=outline_color,
        **kwargs,
    )

    return fitted.fits


def render_block(
    image: Image.Image,
    block: dict,
    font_path: Path,
    min_size: int,
    default_color: str,
    outline_enabled: bool,
    outline_width: int,
    outline_color: str,
) -> bool:
    from .schema import bbox_xyxy

    x1, y1, x2, y2 = bbox_xyxy(block["bbox"])
    region_w = max(1, x2 - x1)
    region_h = max(1, y2 - y1)

    margin = max(2, round(min(region_w, region_h) * 0.05))
    stroke = outline_width if outline_enabled else 0
    fill = block.get("text_color") or default_color

    # Semantic text direction comes from the TRANSLATION.
    direction = _render_direction(block)

    # Physical orientation comes from the source layout / explicit override.
    orientation = _render_orientation(block)

    if orientation == "vertical":
        # Render Persian normally on a swapped off-screen canvas:
        #
        # original bbox:      W x H    (tall/narrow)
        # temporary canvas:   H x W    (wide/short)
        #
        # This gives Persian its normal horizontal RTL shaping and lets it use
        # the long vertical dimension as line width. Then rotate the COMPLETE
        # shaped block back into the original tall bbox.
        virtual_w = region_h
        virtual_h = region_w

        layer = Image.new("RGBA", (virtual_w, virtual_h), (0, 0, 0, 0))

        # For vertical comic text centering is usually the safest default.
        alignment = str(block.get("alignment") or "center").lower()

        fits = _draw_fitted_text(
            target=layer,
            text=block["translated"],
            font_path=font_path,
            width=virtual_w,
            height=virtual_h,
            min_size=min_size,
            requested_size=block.get("font_size"),
            direction=direction,
            alignment=alignment,
            fill=fill,
            stroke=stroke,
            outline_color=outline_color,
            margin=margin,
        )

        if _vertical_rotation(block) == "cw":
            rotated = layer.transpose(Image.Transpose.ROTATE_270)
        else:
            # Counter-clockwise is the default for Persian:
            # the logical beginning (right side of RTL text) moves toward top.
            rotated = layer.transpose(Image.Transpose.ROTATE_90)

        # ROTATE_90/270 is exact; dimensions become region_w x region_h.
        if rotated.size != (region_w, region_h):
            rotated = rotated.resize((region_w, region_h), Image.Resampling.LANCZOS)

        if image.mode != "RGBA":
            rgba = image.convert("RGBA")
            rgba.alpha_composite(rotated, dest=(x1, y1))
            image.paste(rgba.convert(image.mode))
        else:
            image.alpha_composite(rotated, dest=(x1, y1))

        return fits

    # Normal horizontal Persian / Latin block.
    default_alignment = (
        "center"
        if block.get("text_type") == "dialogue"
        else ("right" if direction == "rtl" else "left")
    )
    alignment = str(block.get("alignment") or default_alignment).lower()

    # Draw into a region-sized transparent layer so horizontal and vertical
    # paths behave consistently.
    layer = Image.new("RGBA", (region_w, region_h), (0, 0, 0, 0))

    fits = _draw_fitted_text(
        target=layer,
        text=block["translated"],
        font_path=font_path,
        width=region_w,
        height=region_h,
        min_size=min_size,
        requested_size=block.get("font_size"),
        direction=direction,
        alignment=alignment,
        fill=fill,
        stroke=stroke,
        outline_color=outline_color,
        margin=margin,
    )

    if image.mode != "RGBA":
        rgba = image.convert("RGBA")
        rgba.alpha_composite(layer, dest=(x1, y1))
        image.paste(rgba.convert(image.mode))
    else:
        image.alpha_composite(layer, dest=(x1, y1))

    return fits
