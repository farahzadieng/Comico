#!/usr/bin/env python3
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "02-OCR-REBDER"))
from comic_pipeline.cli import render_main

if __name__ == "__main__":
    raise SystemExit(render_main())
