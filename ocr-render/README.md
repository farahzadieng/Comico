# Headless Comic OCR + Rendering

This directory contains all implementation code used by the two root entry
points. Stage 1 never changes an image; stage 2 never performs detection, OCR,
or translation. Their only contract is UTF-8 JSON.

## Upstream provenance

The extracted code under `vendor/comic_translate` comes from
`ogkalu2/comic-translate` commit
`8977b91a4f7a40c3917c5a268e9e7d78e1d818da` (main, 2026-09-10), licensed
under Apache-2.0; see `vendor/comic_translate/UPSTREAM-LICENSE`.

Reused headless modules:

- `modules/detection/rtdetr_v2_onnx.py`, `base.py`, heuristic line and geometry
  helpers: RT-DETR-v2 bubble/text detection, box construction, line direction,
  coordinate handling, and foreground color extraction.
- `modules/detection/script_detection.py`: page/block script routing.
- `modules/ocr/manga_ocr/mobile` and `modules/ocr/ppocr/*`: MangaOCR Mobile
  ONNX for Japanese; PP-OCRv5/v6 ONNX for Korean, Chinese, English, Latin, and
  Cyrillic, matching the upstream factory's current local routing.
- `modules/utils/image_utils.py`: content segmentation, connected-component
  filtering, bubble clipping, and controlled mask dilation.
- `modules/inpainting/lama.py`, `base.py`, `schema.py` and
  `modules/utils/inpainting.py`: manga-tuned LaMa ONNX and crop/resize strategy.
- `imkit`: upstream image-processing compatibility layer.

Not copied: Qt/Gradio UI, controllers, account/authentication, translators,
cloud OCR, project state, and settings UI. Typography is newly implemented
with Pillow FreeType + libraqm because Comic Translate's renderer imports Qt
vertical-layout classes.

## Setup and commands

Install the focused dependency set:

```bash
uv sync --group ocr
uv run --group ocr python 01-ocr.py ./comic --output output.json --language auto
# edit translated fields
uv run --group ocr python 02-render.py ./output.json
```

Models download on first use to `~/.cache/comic-ocr-render/`, using the same
URLs and checksums registered by Comic Translate. Later runs use the cache.
Use `--device cpu` or `--device cuda`; automatic selection is the default.

Stage 1 stores original-image coordinates, optional bubble bounds, line-derived
direction, color when reliable, and a lossless cropped 1-bit text mask encoded
as `packbits-zlib-base64`. A raster mask is intentionally stored instead of a
bbox because the cleaning mask must identify glyph pixels. Confidence fields
are `null`: the upstream block API does not retain detector/OCR scores.

The detector does not provide semantic SFX classification. Bubble text is
conservatively labeled `dialogue`; free text remains `unknown` and is not
pretended to be SFX. Users can set `text_type: "sfx"` and `translate: false`.
The renderer never touches `translate: false` blocks.

Rendering requires `font.ttf` beside this file. It is loaded directly, tries to
select variable-font weight 800, and never silently substitutes a system font.
RTL shaping and bidirectional layout use libraqm/HarfBuzz through Pillow when
available, with `arabic-reshaper` plus the Unicode BiDi implementation in
`python-bidi` as a portable fallback. No manual Unicode reversal is performed.

Known limits: automated SFX semantics are unavailable upstream; complex or
large artwork reconstruction remains bounded by LaMa quality; a single font
must contain every glyph the user intends to render; vertical typography uses
libraqm's top-to-bottom direction but does not reproduce hand-lettered warping.
