from __future__ import annotations

import numpy as np

from .bootstrap import configure_model_cache, enable_upstream


class Inpainter:
    """Comic Translate LaMa ONNX adapter with its crop HD strategy."""

    def __init__(self, device: str, resize_limit: int = 960):
        enable_upstream()
        configure_model_cache()
        from modules.inpainting.lama import LaMa
        from modules.inpainting.schema import Config, HDStrategy
        self.model = LaMa(device, backend="onnx")
        # Comic Translate's Resize HD strategy is substantially faster for
        # pages containing many disjoint text masks: one combined LaMa pass,
        # then only masked pixels are restored at original resolution.
        self.config = Config(hd_strategy=HDStrategy.RESIZE, hd_strategy_resize_limit=resize_limit)

    def inpaint(self, image: np.ndarray, mask: np.ndarray) -> np.ndarray:
        if not np.any(mask):
            return image.copy()
        return np.asarray(self.model(image.copy(), mask, self.config), dtype=np.uint8)
