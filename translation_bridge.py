#!/usr/bin/env python3
"""
Translation Bridge for comic-ocr-render.

Export:
    python translation_bridge.py export output.json translation-input.json

Import:
    python translation_bridge.py import output.json translation-output.json --output translated.json

The bridge never relies on array order. Each text block is matched by:
    <image path>::<block id>
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any


BRIDGE_VERSION = "1.0"


class BridgeError(Exception):
    pass


def load_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as f:
            value = json.load(f)
    except FileNotFoundError as exc:
        raise BridgeError(f"File not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise BridgeError(
            f"Invalid JSON in {path}: line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc

    if not isinstance(value, dict):
        raise BridgeError(f"Top-level JSON value must be an object: {path}")
    return value


def save_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write("\n")


def make_ref(image_path: str, block_id: Any) -> str:
    return f"{image_path}::{block_id}"


def source_text(block: dict[str, Any]) -> Any:
    # source_text is preferred when present because it is the immutable OCR source.
    if "source_text" in block:
        return block["source_text"]
    return block.get("text")


def iter_original_blocks(project: dict[str, Any]):
    images = project.get("images")
    if not isinstance(images, list):
        raise BridgeError("Original JSON must contain an 'images' array.")

    seen: set[str] = set()

    for image in images:
        if not isinstance(image, dict):
            raise BridgeError("Every item in 'images' must be an object.")

        image_path = image.get("path")
        if not isinstance(image_path, str) or not image_path:
            raise BridgeError("Every image must have a non-empty string 'path'.")

        blocks = image.get("text_blocks", [])
        if not isinstance(blocks, list):
            raise BridgeError(f"'text_blocks' must be an array for image: {image_path}")

        for block in blocks:
            if not isinstance(block, dict):
                raise BridgeError(f"Invalid text block in image: {image_path}")

            if "id" not in block:
                raise BridgeError(f"Text block without id in image: {image_path}")

            ref = make_ref(image_path, block["id"])
            if ref in seen:
                raise BridgeError(f"Duplicate block reference in original JSON: {ref}")
            seen.add(ref)

            yield image, block, ref


def export_bridge(original: dict[str, Any]) -> dict[str, Any]:
    pages: list[dict[str, Any]] = []
    total = 0

    images = original.get("images")
    if not isinstance(images, list):
        raise BridgeError("Original JSON must contain an 'images' array.")

    # Validate global uniqueness first.
    list(iter_original_blocks(original))

    for image in images:
        image_path = image["path"]
        texts: list[dict[str, Any]] = []

        for block in image.get("text_blocks", []):
            # Blocks explicitly excluded from translation should not be sent to the AI.
            if block.get("translate") is False:
                continue

            src = source_text(block)
            if src is None:
                continue
            if not isinstance(src, str):
                raise BridgeError(
                    f"Source text must be a string or null: "
                    f"{make_ref(image_path, block.get('id'))}"
                )

            ref = make_ref(image_path, block["id"])
            texts.append(
                {
                    "id": ref,
                    "source": src,
                    "translated": None,
                }
            )
            total += 1

        if texts:
            pages.append(
                {
                    "page": image_path,
                    "texts": texts,
                }
            )

    return {
        "version": BRIDGE_VERSION,
        "target_language": "fa",
        "pages": pages,
        "count": total,
    }


def bridge_items(bridge: dict[str, Any]) -> dict[str, dict[str, Any]]:
    pages = bridge.get("pages")
    if not isinstance(pages, list):
        raise BridgeError("Translation JSON must contain a 'pages' array.")

    items: dict[str, dict[str, Any]] = {}

    for page in pages:
        if not isinstance(page, dict):
            raise BridgeError("Every page in translation JSON must be an object.")

        texts = page.get("texts")
        if not isinstance(texts, list):
            raise BridgeError("Every translation page must contain a 'texts' array.")

        for item in texts:
            if not isinstance(item, dict):
                raise BridgeError("Every translation item must be an object.")

            ref = item.get("id")
            if not isinstance(ref, str) or not ref:
                raise BridgeError("Every translation item must have a non-empty string 'id'.")

            if ref in items:
                raise BridgeError(f"Duplicate translation id: {ref}")

            items[ref] = item

    return items


def import_bridge(
    original: dict[str, Any],
    bridge: dict[str, Any],
    *,
    allow_missing: bool = False,
) -> tuple[dict[str, Any], int]:
    result = copy.deepcopy(original)
    translated_items = bridge_items(bridge)

    expected: dict[str, tuple[dict[str, Any], str]] = {}

    for _image, block, ref in iter_original_blocks(result):
        if block.get("translate") is False:
            continue

        src = source_text(block)
        if src is None:
            continue
        if not isinstance(src, str):
            raise BridgeError(f"Invalid original source text for {ref}")

        expected[ref] = (block, src)

    unexpected = sorted(set(translated_items) - set(expected))
    if unexpected:
        preview = ", ".join(unexpected[:5])
        suffix = " ..." if len(unexpected) > 5 else ""
        raise BridgeError(
            f"Translation JSON contains {len(unexpected)} unknown id(s): {preview}{suffix}"
        )

    missing = sorted(set(expected) - set(translated_items))
    if missing and not allow_missing:
        preview = ", ".join(missing[:5])
        suffix = " ..." if len(missing) > 5 else ""
        raise BridgeError(
            f"Translation JSON is missing {len(missing)} expected id(s): {preview}{suffix}"
        )

    merged = 0

    for ref, item in translated_items.items():
        block, original_source = expected[ref]

        item_source = item.get("source")
        if item_source != original_source:
            raise BridgeError(
                f"Source text was changed for {ref}. "
                "The AI must modify only the 'translated' field."
            )

        translated = item.get("translated")
        if translated is None:
            if allow_missing:
                continue
            raise BridgeError(f"'translated' is still null for {ref}")

        if not isinstance(translated, str):
            raise BridgeError(f"'translated' must be a string for {ref}")

        translated = translated.strip()
        if not translated:
            if allow_missing:
                continue
            raise BridgeError(f"'translated' is empty for {ref}")

        # This is the ONLY field copied back from the AI-facing JSON.
        block["translated"] = translated
        merged += 1

    return result, merged


def split_bridge_by_pages(
    bridge: dict[str, Any],
    chunk_size: int,
) -> list[dict[str, Any]]:
    if chunk_size <= 0:
        return [bridge]

    parts: list[dict[str, Any]] = []
    current_pages: list[dict[str, Any]] = []
    current_count = 0

    def flush() -> None:
        nonlocal current_pages, current_count
        if not current_pages:
            return
        parts.append(
            {
                "version": bridge.get("version", BRIDGE_VERSION),
                "target_language": bridge.get("target_language", "fa"),
                "pages": current_pages,
                "count": current_count,
            }
        )
        current_pages = []
        current_count = 0

    for page in bridge.get("pages", []):
        page_count = len(page.get("texts", []))

        # Keep a page intact whenever possible so its local context stays together.
        if current_pages and current_count + page_count > chunk_size:
            flush()

        current_pages.append(page)
        current_count += page_count

    flush()
    return parts


def cmd_export(args: argparse.Namespace) -> None:
    original_path = Path(args.original)
    output_path = Path(args.output)

    original = load_json(original_path)
    bridge = export_bridge(original)

    if args.chunk_size and args.chunk_size > 0:
        parts = split_bridge_by_pages(bridge, args.chunk_size)
        stem = output_path.stem
        suffix = output_path.suffix or ".json"
        parent = output_path.parent
        parent.mkdir(parents=True, exist_ok=True)

        for i, part in enumerate(parts, start=1):
            part["part"] = i
            part["parts_total"] = len(parts)
            part_path = parent / f"{stem}.part{i:03d}{suffix}"
            save_json(part_path, part)
            print(f"Created: {part_path} ({part['count']} items)")

        print(f"Translation items total: {bridge['count']}")
        print(f"Chunks: {len(parts)}")
    else:
        save_json(output_path, bridge)
        print(f"Created translation bridge: {output_path}")
        print(f"Translation items: {bridge['count']}")


def combine_translation_files(paths: list[Path]) -> dict[str, Any]:
    combined = {
        "version": BRIDGE_VERSION,
        "target_language": "fa",
        "pages": [],
        "count": 0,
    }

    seen: set[str] = set()

    for path in paths:
        bridge = load_json(path)
        pages = bridge.get("pages")
        if not isinstance(pages, list):
            raise BridgeError(f"Translation JSON has no valid 'pages' array: {path}")

        for page in pages:
            if not isinstance(page, dict):
                raise BridgeError(f"Invalid page in translation JSON: {path}")

            new_page = {
                "page": page.get("page"),
                "texts": [],
            }

            texts = page.get("texts")
            if not isinstance(texts, list):
                raise BridgeError(f"Invalid 'texts' array in: {path}")

            for item in texts:
                if not isinstance(item, dict):
                    raise BridgeError(f"Invalid translation item in: {path}")

                ref = item.get("id")
                if not isinstance(ref, str) or not ref:
                    raise BridgeError(f"Translation item without valid id in: {path}")

                if ref in seen:
                    raise BridgeError(
                        f"Duplicate translation id across translation files: {ref}"
                    )
                seen.add(ref)
                new_page["texts"].append(item)
                combined["count"] += 1

            if new_page["texts"]:
                combined["pages"].append(new_page)

    return combined


def cmd_import(args: argparse.Namespace) -> None:
    original_path = Path(args.original)
    translation_paths = [Path(p) for p in args.translation]
    output_path = Path(args.output)

    original = load_json(original_path)
    bridge = combine_translation_files(translation_paths)

    result, merged = import_bridge(
        original,
        bridge,
        allow_missing=args.allow_missing,
    )
    save_json(output_path, result)

    print(f"Created merged render JSON: {output_path}")
    print(f"Merged translations: {merged}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export/import a minimal AI translation JSON without losing comic block mapping."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    export_parser = sub.add_parser(
        "export",
        help="Create a minimal AI-facing translation JSON.",
    )
    export_parser.add_argument("original", help="Full OCR JSON.")
    export_parser.add_argument("output", help="Minimal translation JSON to create.")
    export_parser.add_argument(
        "--chunk-size",
        type=int,
        default=0,
        help=(
            "Optional approximate maximum number of text items per output file. "
            "Pages are kept intact whenever possible."
        ),
    )
    export_parser.set_defaults(func=cmd_export)

    import_parser = sub.add_parser(
        "import",
        help="Merge translated fields back into the full OCR JSON.",
    )
    import_parser.add_argument("original", help="Original full OCR JSON.")
    import_parser.add_argument(
        "translation",
        nargs="+",
        help="One or more AI-translated bridge JSON files.",
    )
    import_parser.add_argument(
        "--output",
        required=True,
        help="Full JSON to create for the renderer.",
    )
    import_parser.add_argument(
        "--allow-missing",
        action="store_true",
        help="Allow null/empty/missing translations and merge only completed items.",
    )
    import_parser.set_defaults(func=cmd_import)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        args.func(args)
        return 0
    except BridgeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
