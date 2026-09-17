from __future__ import annotations

import hashlib
import urllib.request
from pathlib import Path

MODEL_CACHE = Path.home() / ".cache" / "comic-ocr-render"


def download(url: str, relative: str, sha256: str | None = None) -> Path:
    target = MODEL_CACHE / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and (not sha256 or _sha(target) == sha256):
        return target
    partial = target.with_suffix(target.suffix + ".part")
    try:
        urllib.request.urlretrieve(url, partial)
        if sha256 and _sha(partial) != sha256:
            raise RuntimeError(f"Checksum mismatch for {target.name}")
        partial.replace(target)
    finally:
        if partial.exists():
            partial.unlink()
    return target


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
