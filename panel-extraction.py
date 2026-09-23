#!/usr/bin/env python3
"""Extract panels from comic images based on a panels.json file.

Usage:
    python panel-extraction.py <directory>

The directory is searched recursively for every panels.json file.
For each panels.json found, every image referenced inside it is read,
its panels are cropped in the order declared in the JSON and saved as
lossless-quality JPEG files inside a new "cropped-panel" directory
created next to the images.

Files are named: 00001_1920x1212.jpg (index_resolution.ext)
Images without any detected panel are copied over as a full image.
"""

import json
import sys
from pathlib import Path

from PIL import Image

OUTPUT_DIR_NAME = "cropped-panel"
JPEG_QUALITY = 100
JPEG_SUBSAMPLING = 0  # 4:4:4 - no chroma subsampling


def find_panels_json(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("panels.json") if p.is_file())


def resolve_image(json_path: Path, filename: str) -> Path | None:
    candidate = json_path.parent / filename
    if candidate.is_file():
        return candidate
    matches = sorted(json_path.parent.rglob(Path(filename).name))
    for match in matches:
        if match.is_file():
            return match
    return None


def save_jpg(image: Image.Image, dest: Path) -> None:
    image = image.convert("RGB")
    image.save(dest, "JPEG", quality=JPEG_QUALITY, subsampling=JPEG_SUBSAMPLING)


def process_panels_json(json_path: Path) -> tuple[int, int]:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    pages = data.get("pages", [])
    if not pages:
        print(f"  no pages found in {json_path}")
        return 0, 0

    image_dir = json_path.parent
    output_dir = image_dir / OUTPUT_DIR_NAME
    output_dir.mkdir(parents=True, exist_ok=True)

    index = 0
    processed_pages = 0
    missing = 0

    for page in pages:
        filename = page.get("filename")
        if not filename:
            continue

        image_path = resolve_image(json_path, filename)
        if image_path is None:
            print(f"  missing image: {filename}")
            missing += 1
            continue

        try:
            with Image.open(image_path) as image:
                image.load()
                page_width, page_height = image.size

                crops = []
                for panel in page.get("panels", []):
                    bbox = panel.get("bbox") or {}
                    try:
                        x1 = int(round(float(bbox["x1"])))
                        y1 = int(round(float(bbox["y1"])))
                        x2 = int(round(float(bbox["x2"])))
                        y2 = int(round(float(bbox["y2"])))
                    except (KeyError, TypeError, ValueError):
                        continue

                    x1 = max(0, min(x1, page_width - 1))
                    y1 = max(0, min(y1, page_height - 1))
                    x2 = max(x1 + 1, min(x2, page_width))
                    y2 = max(y1 + 1, min(y2, page_height))
                    crops.append(image.crop((x1, y1, x2, y2)))

                if not crops:
                    crops = [image.copy()]

                for crop in crops:
                    index += 1
                    width, height = crop.size
                    dest = output_dir / f"{index:05d}_{width}x{height}.jpg"
                    save_jpg(crop, dest)

                processed_pages += 1
        except OSError as exc:
            print(f"  failed to read {filename}: {exc}")
            missing += 1

    print(
        f"  {json_path}: {processed_pages} page(s) -> "
        f"{index} image(s) in {output_dir}"
        + (f", {missing} skipped" if missing else "")
    )
    return index, missing


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage:\n  python panel-extraction.py <directory>")
        sys.exit(1)

    root = Path(sys.argv[1]).expanduser()
    if not root.is_dir():
        print(f"Error: not a directory: {root}")
        sys.exit(1)

    json_files = find_panels_json(root)
    if not json_files:
        print(f"No panels.json found under {root}")
        sys.exit(1)

    total_images = 0
    total_missing = 0
    for json_path in json_files:
        images, missing = process_panels_json(json_path)
        total_images += images
        total_missing += missing

    print(
        f"Done: {total_images} image(s) written from {len(json_files)} "
        f"panels.json file(s)"
        + (f", {total_missing} image(s) skipped" if total_missing else "")
    )


if __name__ == "__main__":
    main()
