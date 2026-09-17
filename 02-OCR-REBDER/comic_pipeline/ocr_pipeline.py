from __future__ import annotations

import traceback
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from .bootstrap import enable_upstream
from .detection import Detector, text_type
from .ocr import OCRManager
from .schema import SCHEMA_VERSION, bbox_dict, encode_mask, save_json

EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def discover_images(root: Path) -> list[Path]:
    return sorted((p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in EXTENSIONS), key=lambda p: p.relative_to(root).as_posix().lower())


def _color(value):
    if isinstance(value, (tuple, list)) and len(value) >= 3:
        return "#%02x%02x%02x" % tuple(max(0, min(255, int(x))) for x in value[:3])
    return None


def _polygon(block) -> list[list[int]]:
    points = getattr(block, "segm_pts", None)
    if points is None or not np.asarray(points).size:
        return []
    arr = np.asarray(points).reshape(-1, 2)
    return [[int(round(x)), int(round(y))] for x, y in arr]


def _block_mask(image: np.ndarray, block):
    enable_upstream()
    from modules.utils.image_utils import build_block_mask_data
    return build_block_mask_data(image, block, require_text_or_translation=False, clip_to_bubble=True)


def _serialize_block(image: np.ndarray, block, number: int, ocr_error: str | None = None) -> dict:
    kind, translate = text_type(block)
    crop_mask, bounds = _block_mask(image, block)
    mask = None
    if crop_mask is not None and bounds is not None:
        mask = encode_mask(crop_mask, (bounds[0], bounds[1]))
    direction = getattr(block, "direction", None)
    direction = "rtl" if direction == "vertical" and getattr(block, "source_lang", None) in {"ar", "fa"} else ("vertical" if direction == "vertical" else "ltr")
    result = {
        "id": number,
        "text": getattr(block, "text", None) or None,
        "source_text": getattr(block, "text", None) or None,
        "translated": None,
        "translate": translate,
        "text_type": kind,
        "bbox": bbox_dict(block.xyxy),
        "bubble_bbox": bbox_dict(block.bubble_xyxy) if getattr(block, "bubble_xyxy", None) is not None else None,
        "polygon": _polygon(block),
        "mask": mask,
        "language": getattr(block, "source_lang", None) or None,
        "direction": direction,
        "alignment": "center" if kind == "dialogue" else None,
        "text_color": _color(getattr(block, "font_color", None)),
        "font_size": None,
        "detection_confidence": None,
        "ocr_confidence": None,
    }
    if ocr_error:
        result["error"] = ocr_error
    return result


def _debug_image(image: np.ndarray, blocks: list, target: Path) -> None:
    canvas = Image.fromarray(image).convert("RGB")
    draw = ImageDraw.Draw(canvas)
    for i, block in enumerate(blocks, 1):
        box = tuple(map(int, block.xyxy))
        draw.rectangle(box, outline="#00ff66", width=max(2, canvas.width // 800))
        draw.text((box[0] + 2, box[1] + 2), str(i), fill="#ff0055")
    target.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(target.with_suffix(".png"))


def run_ocr(root: Path, output: Path, language: str, device: str, debug: bool = False) -> dict:
    root = root.resolve()
    if not root.is_dir():
        raise ValueError(f"Input directory does not exist: {root}")
    images = discover_images(root)
    detector = Detector(device)
    ocr = OCRManager(language, device)
    records, ok, failed = [], 0, 0
    debug_root = output.parent / f"{output.stem}-debug"
    for index, path in enumerate(images, 1):
        rel = path.relative_to(root).as_posix()
        print(f"[{index}/{len(images)}] {rel}")
        record = {"id": rel, "path": rel, "width": None, "height": None, "status": "ok", "text_blocks": []}
        try:
            with Image.open(path) as loaded:
                rgb = loaded.convert("RGB")
            image = np.asarray(rgb)
            record["width"], record["height"] = rgb.size
            blocks = detector.detect(image)
            try:
                blocks = ocr.process(image, blocks)
                record["text_blocks"] = [_serialize_block(image, block, n) for n, block in enumerate(blocks, 1)]
            except Exception as exc:
                message = f"OCR failed: {exc}"
                record["errors"] = [message]
                record["text_blocks"] = [_serialize_block(image, block, n, message) for n, block in enumerate(blocks, 1)]
            if debug:
                _debug_image(image, blocks, debug_root / rel)
            ok += 1
        except Exception as exc:
            record["status"] = "error"
            record["errors"] = [str(exc)]
            if debug:
                record["traceback"] = traceback.format_exc()
            failed += 1
        records.append(record)
    project = {
        "version": SCHEMA_VERSION,
        "generator": {"name": "comic-ocr-render", "comic_translate_commit": "8977b91a4f7a40c3917c5a268e9e7d78e1d818da"},
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_directory": str(root),
        "images": records,
    }
    save_json(output.resolve(), project)
    print(f"Wrote {output.resolve()} ({ok} ok, {failed} failed, {len(images)} total)")
    return project
