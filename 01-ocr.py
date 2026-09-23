#!/usr/bin/env python3
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "ocr-render"))
from comic_pipeline.cli import ocr_main

if __name__ == "__main__":
    raise SystemExit(ocr_main())
