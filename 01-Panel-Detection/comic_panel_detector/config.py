import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Config:

    input_directory: str

    output_file: str

    model_path: str

    reading_direction: str

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
            config_file.read_text(
                encoding="utf-8"
            )
        )

    except Exception as e:
        raise ValueError(
            f"Invalid JSON configuration: {e}"
        )


    required = [
        "input_directory",
        "output_file",
        "reading_direction"
    ]


    for key in required:

        if key not in data:
            raise ValueError(
                f"Missing required field: {key}"
            )


    direction = data["reading_direction"].lower()


    if direction not in [
        "ltr",
        "rtl"
    ]:
        raise ValueError(
            "reading_direction must be 'ltr' or 'rtl'"
        )


    return Config(

        input_directory=data["input_directory"],

        output_file=data["output_file"],

        model_path=data.get(
            "model_path",
            "./models/best.pt"
        ),

        reading_direction=direction,

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