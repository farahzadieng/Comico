from __future__ import annotations

import base64
import json
import zlib
from pathlib import Path
from typing import Any

import numpy as np

SCHEMA_VERSION = "1.0"


def bbox_dict(xyxy) -> dict[str, int]:
    x1, y1, x2, y2 = (int(round(float(v))) for v in xyxy)
    return {"x": x1, "y": y1, "width": max(0, x2 - x1), "height": max(0, y2 - y1)}


def bbox_xyxy(value: dict[str, Any]) -> tuple[int, int, int, int]:
    x, y, w, h = (int(value[k]) for k in ("x", "y", "width", "height"))
    return x, y, x + w, y + h


def encode_mask(mask: np.ndarray, origin: tuple[int, int]) -> dict[str, Any]:
    """Compact, lossless mask storage: cropped 1-bit raster + zlib/base64."""
    binary = np.asarray(mask > 0, dtype=np.uint8)
    packed = np.packbits(binary, axis=None)
    return {
        "encoding": "packbits-zlib-base64",
        "origin": [int(origin[0]), int(origin[1])],
        "width": int(binary.shape[1]),
        "height": int(binary.shape[0]),
        "data": base64.b64encode(zlib.compress(packed.tobytes(), 9)).decode("ascii"),
    }


def decode_mask(spec: dict[str, Any]) -> tuple[np.ndarray, tuple[int, int]]:
    if spec.get("encoding") != "packbits-zlib-base64":
        raise ValueError(f"Unsupported mask encoding: {spec.get('encoding')!r}")
    width, height = int(spec["width"]), int(spec["height"])
    raw = zlib.decompress(base64.b64decode(spec["data"], validate=True))
    bits = np.unpackbits(np.frombuffer(raw, dtype=np.uint8))[: width * height]
    return (bits.reshape(height, width) * 255).astype(np.uint8), tuple(map(int, spec["origin"]))


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("JSON root must be an object")
    return value


def save_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
