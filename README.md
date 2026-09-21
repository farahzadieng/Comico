# COMICO

<div align="center">

This project is a preprocessing component for a larger digital comic-processing pipeline. Its purpose is to automatically detect comic panels from page images and generate structured metadata that can later be used by other stages such as panel extraction, OCR, translation, or typesetting.

</div>

---

# Comic Panel Detection

The detector is based on a YOLO comic-panel detection model and supports both single comic directories and recursive batch processing of multiple comic collections.

## Panel Detection Process

For each comic page, the pipeline:

1. Discovers supported image files and processes them in natural filename order.

2. Runs the YOLO panel-detection model on each page.

3. Extracts panel bounding boxes, confidence scores, and class information.

4. Validates and clips bounding boxes to the original image dimensions.

5. Analyzes detected-panel coverage to identify significant unexplained regions that may represent missed panels.

6. Determines panel reading order using geometric row grouping.

7. Supports both:
   - **LTR** — left-to-right comics
   - **RTL** — right-to-left comics and manga

8. Assigns stable panel IDs such as:

   `1-1`, `1-2`, `1-3`, ...

9. Generates a `panels.json` file containing page dimensions, panel coordinates, reading order, confidence values, coverage information, and detection source.

In recursive mode, every directory containing comic-page images is treated as an independent collection and receives its own `panels.json` file.

The original comic images are never modified.

# UV GUIDE FOR GROUPS

```bash
uv sync --group panel
uv sync --group ocr
```

# ENVIROMENTS

**Panel Detection** group name is `panel`

**OCR and Render** group name is `ocr`

# 01 - Panel Detection

you need `config.json`, and you may use `01-Panel-Detection/config.example.json` as the example. It locates the input directory.

Model is not downloaded , use backup version and save to `01-Panel-Detection/models/best.pt`

you may place `config.json` in the root directory of the project.

```bash
uv run --group panel python Panel-Detection.py config.json
```

**The output would be loaded inside the comic directory in:** `panels.json`

## Error Handling

In case of getting error with `best.pt` download it from huggingface with :

```bash
uv run hf download \
  mosesb/best-comic-panel-detection \
  best.pt \
  --repo-type space \
  --local-dir ./01-Panel-Detection/models
```

# 02 - OCR and Render

This is a separate, headless two-stage pipeline for comic text. It does not
translate text automatically and it does not require a GUI.

```text
Stage 1: comic images → detection → OCR → one JSON file
Stage 2: edited JSON + original images → text cleaning/inpainting → rendered images
```

The JSON file is the only contract between the stages. You translate or edit it
yourself before running Stage 2.

## Dependencies and first-time model downloads

Install the OCR/render dependency group once:

```bash
uv sync --group ocr
```

The required deep-learning models download automatically on first use and are
reused afterwards. They are stored outside this repository at:

```text
~/.cache/comic-ocr-render/
```

Depending on the selected language and stage, the pipeline downloads:

- RT-DETR-v2 comic text/bubble detector
- MangaOCR Mobile for Japanese
- PP-OCR recognition models for English, Korean, Chinese, Latin, and Cyrillic
- Manga-tuned LaMa ONNX model when rendering/cleaning images

The first run therefore needs an internet connection. Translation never uses an
online service.

## Stage 1 — extract OCR to JSON

The user-facing entry point is `01-ocr.py`. It recursively scans a source
directory for `.jpg`, `.jpeg`, `.png`, and `.webp` images. Source images are
never changed.

```bash
uv run --group ocr python 01-ocr.py /path/to/comic
```

By default this writes `output.json` in the current directory. Choose an output
file explicitly when processing more than one comic:

```bash
uv run --group ocr python 01-ocr.py /path/to/comic \
  --output /path/to/comic/ocr.json \
  --language auto
```

For a known source language, use an explicit OCR route. This avoids the extra
script-identification model and is normally preferable for a single-language
comic:

```bash
# English comic
uv run --group ocr python 01-ocr.py ./samples --output ./samples/ocr.json --language en

# Japanese, Korean, Chinese, or Russian
uv run --group ocr python 01-ocr.py ./comic --output ./ocr.json --language ja
uv run --group ocr python 01-ocr.py ./comic --output ./ocr.json --language ko
uv run --group ocr python 01-ocr.py ./comic --output ./ocr.json --language zh
uv run --group ocr python 01-ocr.py ./comic --output ./ocr.json --language ru
```

Optional useful flags:

```bash
--device cpu        # force CPU; use cuda when an ONNX CUDA provider is available
--debug             # write detection previews beside the JSON, not into the source directory
```

Stage 1 creates exactly one UTF-8 JSON file for the whole directory. Every
image entry contains its relative source path, dimensions, status, and text
blocks. Text-block coordinates always refer to the original image. A compact,
lossless glyph mask is included so Stage 2 removes only detected text pixels
rather than blindly clearing a bounding box.

## Translate or edit the JSON

Open the JSON with a UTF-8-capable editor. For every block that should be
replaced, change only `translated` and, for Persian/Arabic, `direction`:

```json
{
  "text": "WHERE ARE YOU GOING?",
  "translated": "داری کجا می‌ری؟",
  "translate": true,
  "text_type": "dialogue",
  "direction": "rtl",
  "alignment": "center"
}
```

Do not change `id`, `path`, `bbox`, `polygon`, or `mask` unless you understand
the coordinate/mask format. These fields locate the source image and define the
safe cleaning area.

You may edit the following fields:

- `translated`: required string for every block with `translate: true`
- `translate`: set to `false` to leave a block untouched
- `text_type`: `dialogue`, `narration`, `caption`, `sfx`, `decorative`, or `unknown`
- `direction`: `ltr`, `rtl`, or `vertical`
- `alignment`: `left`, `center`, or `right`
- `text_color`: CSS hex colour such as `#111111`
- `font_size`: `null` for automatic fitting, or an integer override

For sound effects, logos, page numbers, watermarks, or false detections, use:

```json
{
  "translate": false,
  "translated": null,
  "text_type": "sfx"
}
```

Blocks marked `translate: false` are excluded from both cleaning and rendering.
The original artwork/text remains unchanged. Before rendering, the program
validates that every `translate: true` block has a non-null string in
`translated`.

## Stage 2 — clean and render translations

The user-facing entry point is `02-render.py`. It reads the edited JSON,
locates the original source images, combines the stored text masks per page,
uses LaMa inpainting to reconstruct the masked areas, and fits the translated
text into the original regions.

```bash
uv run --group ocr python 02-render.py /path/to/comic/ocr.json
```

By default output is written to a `translated/` directory inside the source
comic directory. It preserves the input directory structure and source image
format where possible. Original images are never overwritten.

Choose another output root or override a moved source directory:

```bash
uv run --group ocr python 02-render.py ./samples/ocr.json \
  --output ./samples/translated \
  --source ./samples
```

Optional rendering flags:

```bash
--device cpu
--quality 95
--min-font-size 12
--outline --outline-width 2 --outline-color '#ffffff'
--default-color '#111111'
--debug
```

The renderer loads `02-OCR-REBDER/font.ttf` directly; it does not require a
system-installed font and does not silently substitute a different one. The
included variable font is requested at weight 800 when supported. Replace that
file with your preferred comic font if necessary, while ensuring it has glyphs
for every target language. Persian and Arabic are shaped using proper RTL/BiDi
handling; do not manually reverse translated strings.

## Expected output layout

```text
comic/
├── chapter-01/page001.jpg
├── chapter-01/page002.jpg
├── ocr.json
└── translated/
    ├── chapter-01/page001.jpg
    └── chapter-01/page002.jpg
```

## Limitations and review workflow

Detection/OCR quality varies with lettering, resolution, and artwork. Review
the JSON before rendering and set `translate: false` for false positives. The
detector can identify speech-bubble versus free text but cannot reliably assign
semantic SFX labels; free text is deliberately emitted as `unknown` rather than
being silently discarded. Inpainting preserves non-masked pixels at the source
resolution, but complex backgrounds or very large text areas can still need
manual review.
