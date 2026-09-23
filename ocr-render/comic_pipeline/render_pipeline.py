from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from .inpaint import Inpainter
from .schema import decode_mask, load_json
from .typography import render_block
from .validation import resolve_source, validate_project


def _combined_mask(image_record: dict, size: tuple[int, int]) -> np.ndarray:
    width, height = size
    combined = np.zeros((height, width), dtype=np.uint8)
    for block in image_record.get("text_blocks", []):
        if block.get("translate") is not True:
            continue
        spec = block.get("mask")
        if spec:
            crop, (x, y) = decode_mask(spec)
            x2, y2 = min(width, x + crop.shape[1]), min(height, y + crop.shape[0])
            if x < 0 or y < 0 or x >= width or y >= height:
                raise ValueError(f"block {block.get('id')} mask origin is outside the image")
            combined[y:y2, x:x2] = np.maximum(combined[y:y2, x:x2], crop[: y2 - y, : x2 - x])
            continue
        polygon = block.get("polygon") or []
        if len(polygon) >= 3:
            layer = Image.new("L", size, 0)
            ImageDraw.Draw(layer).polygon([tuple(point) for point in polygon], fill=255)
            combined = np.maximum(combined, np.asarray(layer))
            continue
        raise ValueError(f"block {block.get('id')} has no mask or polygon; refusing to clean its whole bbox")
    return combined


def _save(image: Image.Image, target: Path, quality: int) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    suffix = target.suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        image.convert("RGB").save(target, quality=quality, subsampling=0, optimize=True)
    elif suffix == ".webp":
        image.save(target, quality=quality, method=6)
    else:
        image.save(target)


def run_render(json_path: Path, output: Path | None, source_override: Path | None, device: str, quality: int, min_font_size: int, debug: bool, outline_enabled: bool, outline_width: int, outline_color: str, default_color: str) -> dict:
    json_path = json_path.resolve()
    project = load_json(json_path)
    source = resolve_source(project, json_path, source_override)
    errors = validate_project(project, source)
    if errors:
        raise ValueError("JSON validation failed:\n  - " + "\n  - ".join(errors))
    font = Path(__file__).resolve().parents[1] / "font.ttf"
    if not font.is_file():
        raise FileNotFoundError(f"Required font not found: {font}")
    output = (output or source / "translated").resolve()
    inpainter = None
    summary = {"processed": 0, "failed": 0, "warnings": [], "errors": []}
    debug_root = output / "_debug"
    for index, record in enumerate(project["images"], 1):
        rel = Path(record["path"])
        print(f"[{index}/{len(project['images'])}] {rel.as_posix()}")
        try:
            with Image.open(source / rel) as loaded:
                original_format = loaded.format
                original = loaded.convert("RGB")
            active = [block for block in record.get("text_blocks", []) if block.get("translate") is True]
            if not active:
                _save(original, output / rel, quality)
                summary["processed"] += 1
                continue
            mask = _combined_mask(record, original.size)
            if inpainter is None:
                inpainter = Inpainter(device)
            cleaned_array = inpainter.inpaint(np.asarray(original), mask)
            cleaned = Image.fromarray(cleaned_array).convert("RGB")
            if debug:
                _save(Image.fromarray(mask), debug_root / rel.with_suffix(".mask.png"), quality)
                _save(cleaned, debug_root / rel.with_suffix(".cleaned.png"), quality)
            for block in active:
                fits = render_block(cleaned, block, font, min_font_size, default_color, outline_enabled, outline_width, outline_color)
                if not fits:
                    summary["warnings"].append(f"{rel}: block {block.get('id')} does not fit at minimum font size")
            _save(cleaned, output / rel, quality)
            summary["processed"] += 1
        except Exception as exc:
            summary["failed"] += 1
            summary["errors"].append(f"{rel}: {exc}")
            print(f"ERROR: {rel}: {exc}")
    print(f"Output: {output} ({summary['processed']} processed, {summary['failed']} failed, {len(summary['warnings'])} warnings)")
    return summary
