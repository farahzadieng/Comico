from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _device(value: str) -> str:
    value = value.lower()
    if value == "auto":
        try:
            import onnxruntime as ort
            return "cuda" if "CUDAExecutionProvider" in ort.get_available_providers() else "cpu"
        except ImportError:
            return "cpu"
    if value not in {"cpu", "cuda"}:
        raise argparse.ArgumentTypeError("device must be auto, cpu, or cuda")
    return value


def ocr_main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Detect and OCR comic text into one JSON file.")
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", "-o", type=Path, default=Path("output.json"))
    parser.add_argument("--language", default="auto", help="auto, en, ja, ko, zh, ru, or a Latin language code")
    parser.add_argument("--device", type=_device, default="auto")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args(argv)
    print(f"Device: {args.device}")
    try:
        from .ocr_pipeline import run_ocr
        run_ocr(args.input, args.output, args.language, args.device, args.debug)
        return 0
    except Exception as exc:
        parser.exit(2, f"error: {exc}\n")


def render_main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Inpaint and render translated comic JSON.")
    parser.add_argument("json", type=Path)
    parser.add_argument("--output", "-o", type=Path)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--device", type=_device, default="auto")
    parser.add_argument("--quality", type=int, default=95)
    parser.add_argument("--min-font-size", type=int, default=12)
    parser.add_argument("--default-color", default="#111111")
    parser.add_argument("--outline", action="store_true")
    parser.add_argument("--outline-width", type=int, default=2)
    parser.add_argument("--outline-color", default="#ffffff")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args(argv)
    if not 1 <= args.quality <= 100:
        parser.error("--quality must be between 1 and 100")
    if args.min_font_size < 1:
        parser.error("--min-font-size must be positive")
    print(f"Device: {args.device}")
    try:
        from .render_pipeline import run_render
        summary = run_render(args.json, args.output, args.source, args.device, args.quality, args.min_font_size, args.debug, args.outline, args.outline_width, args.outline_color, args.default_color)
        return 1 if summary["failed"] else 0
    except Exception as exc:
        parser.exit(2, f"error: {exc}\n")
