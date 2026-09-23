from __future__ import annotations

from pathlib import Path
from typing import Any

from .schema import bbox_xyxy


def resolve_source(project: dict[str, Any], json_path: Path, override: Path | None) -> Path:
    candidates = []
    if override:
        candidates.append(override)
    stored = project.get("source_directory")
    if stored:
        value = Path(stored)
        candidates.extend([value, json_path.parent / value])
    candidates.append(json_path.parent)
    for candidate in candidates:
        resolved = candidate.expanduser().resolve()
        if resolved.is_dir():
            return resolved
    raise ValueError("Cannot resolve source directory; pass --source /path/to/original/comic")


def validate_project(project: dict[str, Any], source: Path) -> list[str]:
    errors = []
    images = project.get("images")
    if not isinstance(images, list):
        return ["images must be an array"]
    seen_paths = set()
    for image_index, image in enumerate(images):
        prefix = f"images[{image_index}]"
        path = image.get("path") if isinstance(image, dict) else None
        if not isinstance(path, str) or not path or Path(path).is_absolute() or ".." in Path(path).parts:
            errors.append(f"{prefix}.path must be a safe relative path")
            continue
        if path in seen_paths:
            errors.append(f"{prefix}.path is duplicated: {path}")
        seen_paths.add(path)
        if not (source / path).is_file():
            errors.append(f"{prefix}: source image not found: {source / path}")
        seen_ids = set()
        for block_index, block in enumerate(image.get("text_blocks", [])):
            label = f"{prefix}.text_blocks[{block_index}]"
            block_id = block.get("id")
            if block_id is None or block_id in seen_ids:
                errors.append(f"{label}.id is missing or duplicated")
            seen_ids.add(block_id)
            try:
                x1, y1, x2, y2 = bbox_xyxy(block["bbox"])
                if x1 < 0 or y1 < 0 or x2 <= x1 or y2 <= y1:
                    raise ValueError
            except Exception:
                errors.append(f"{label}.bbox is invalid")
            if block.get("translate") is True and not isinstance(block.get("translated"), str):
                errors.append(f"{label}.translated must be a string when translate is true")
    return errors
