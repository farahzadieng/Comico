<div align="center">

<div style="font-weight:bold; font-size:28px; color:green;"> COMICO </div>

<br/>
This project is a preprocessing component for a larger digital comic-processing pipeline. Its purpose is to automatically detect comic panels from page images and generate structured metadata that can later be used by other stages such as panel extraction, OCR, translation, or typesetting.

<br/>

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
uv add --group panel
uv sync --group panel
uv sync --all-groups
uv run --group pipe1 python your_entry_point.py
```

# ENVIROMENTS

**Panel Detection** group name is `panel`

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
