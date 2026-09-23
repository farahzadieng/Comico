from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "vendor" / "comic_translate"


def enable_upstream() -> None:
    """Expose the extracted Comic Translate modules under their upstream names."""
    value = str(VENDOR)
    if value not in sys.path:
        sys.path.insert(0, value)


def configure_model_cache() -> None:
    """Retarget upstream immutable model specs to this tool's documented cache."""
    enable_upstream()
    from dataclasses import replace
    from modules.utils import download as registry
    from .models import MODEL_CACHE

    registry.models_base_dir = str(MODEL_CACHE)
    for model_id, spec in list(registry.ModelDownloader.registry.items()):
        parts = Path(spec.save_dir).parts
        try:
            tail = parts[parts.index("models") + 1 :]
        except ValueError:
            tail = (model_id.value,)
        registry.ModelDownloader.registry[model_id] = replace(spec, save_dir=str(MODEL_CACHE.joinpath(*tail)))
