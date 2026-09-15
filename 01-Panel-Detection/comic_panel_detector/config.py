import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class Config:
    input_directory: str
    model_path: str
    reading_direction: str

    # Single-directory mode only. In recursive mode, each collection gets
    # <collection_directory>/<output_filename> instead.
    output_file: Optional[str] = None

    recursive: bool = False
    output_filename: str = "panels.json"

    confidence_threshold: float = 0.25
    iou_threshold: float = 0.7
    missing_panel_threshold: float = 0.10

    device: str = "auto"
    debug: bool = False


def load_config(path: str) -> Config:
    config_file = Path(path)

    if not config_file.exists():
        raise FileNotFoundError(
            f"Configuration file not found: {path}"
        )

    try:
        data = json.loads(
            config_file.read_text(encoding="utf-8")
        )
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Invalid JSON configuration: {e}"
        ) from e

    required = [
        "input_directory",
        "reading_direction",
    ]

    for key in required:
        if key not in data:
            raise ValueError(
                f"Missing required field: {key}"
            )

    direction = str(data["reading_direction"]).lower()

    if direction not in ["ltr", "rtl"]:
        raise ValueError(
            "reading_direction must be 'ltr' or 'rtl'"
        )

    recursive = data.get("recursive", False)

    if not isinstance(recursive, bool):
        raise ValueError(
            "recursive must be true or false"
        )

    output_file = data.get("output_file")

    if not recursive and not output_file:
        raise ValueError(
            "Missing required field: output_file "
            "(required when recursive is false)"
        )

    output_filename = data.get(
        "output_filename",
        "panels.json"
    )

    if not isinstance(output_filename, str) or not output_filename.strip():
        raise ValueError(
            "output_filename must be a non-empty filename"
        )

    output_filename = output_filename.strip()

    # Keep recursive outputs inside each collection directory.
    if Path(output_filename).name != output_filename:
        raise ValueError(
            "output_filename must be a filename only, "
            "for example 'panels.json'"
        )

    return Config(
        input_directory=data["input_directory"],

        output_file=output_file,

        model_path=data.get(
            "model_path",
            "./models/best.pt"
        ),

        reading_direction=direction,

        recursive=recursive,

        output_filename=output_filename,

        confidence_threshold=data.get(
            "confidence_threshold",
            0.25
        ),

        iou_threshold=data.get(
            "iou_threshold",
            0.7
        ),

        missing_panel_threshold=data.get(
            "missing_panel_threshold",
            0.10
        ),

        device=data.get(
            "device",
            "auto"
        ),

        debug=data.get(
            "debug",
            False
        )
    )
