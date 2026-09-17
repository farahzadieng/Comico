from __future__ import annotations

import numpy as np

from .bootstrap import configure_model_cache, enable_upstream


class Detector:
    """Thin headless adapter around Comic Translate's cached RT-DETR-v2 engine."""

    def __init__(self, device: str):
        enable_upstream()
        from modules.detection.rtdetr_v2_onnx import RTDetrV2ONNXDetection
        configure_model_cache()
        self.engine = RTDetrV2ONNXDetection()
        self.engine.initialize(device=device)

    def detect(self, image: np.ndarray):
        return self.engine.detect(image)


def text_type(block) -> tuple[str, bool]:
    # The upstream detector distinguishes bubble/free text, not semantics or SFX.
    if getattr(block, "text_class", "") == "text_bubble":
        return "dialogue", True
    return "unknown", True
