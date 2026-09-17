from __future__ import annotations

from collections import defaultdict

from .bootstrap import configure_model_cache, enable_upstream

LANG_BUCKET = {
    "en": "en", "english": "en", "ja": "ja", "japanese": "ja",
    "ko": "ko", "korean": "ko", "zh": "ch", "chinese": "ch",
    "ru": "ru", "russian": "ru", "fr": "latin", "french": "latin",
    "de": "latin", "german": "latin", "es": "latin", "spanish": "latin",
    "it": "latin", "italian": "latin", "nl": "latin", "dutch": "latin",
    "latin": "latin", "ch": "ch",
}


class OCRManager:
    """Reuse Comic Translate's PPOCRv5 engine and script router."""

    def __init__(self, language: str, device: str):
        enable_upstream()
        configure_model_cache()
        self.language = language.strip().lower()
        self.device = device
        self.engines = {}
        self.script_detector = None

    def _engine(self, bucket: str):
        if bucket == "ja":
            from modules.ocr.manga_ocr.mobile import MangaOCRMobileONNXEngine
            if bucket not in self.engines:
                engine = MangaOCRMobileONNXEngine()
                engine.initialize(device=self.device)
                self.engines[bucket] = engine
            return self.engines[bucket]
        from modules.ocr.ppocr.engine import PPOCRv5Engine
        if bucket not in self.engines:
            engine = PPOCRv5Engine()
            engine.initialize(lang=bucket, device=self.device, use_text_lines=True)
            self.engines[bucket] = engine
        return self.engines[bucket]

    def process(self, image, blocks):
        if not blocks:
            return blocks
        if self.language != "auto":
            bucket = LANG_BUCKET.get(self.language)
            if not bucket:
                raise ValueError(f"Unsupported OCR language: {self.language}")
            code = self.language[:2]
            for block in blocks:
                block.source_lang = code
            return self._engine(bucket).process_image(image, blocks)

        from modules.detection.script_detection import ScriptDetector
        if self.script_detector is None:
            self.script_detector = ScriptDetector()
        self.script_detector.annotate_blocks(image, blocks)
        script_bucket = {"latin": "latin", "cyrillic": "ru", "japanese": "ja", "korean": "ko", "chinese": "ch"}
        groups = defaultdict(list)
        for block in blocks:
            bucket = script_bucket.get((getattr(block, "script", "") or "").lower(), "latin")
            block.source_lang = {"latin": None, "ru": "ru", "ja": "ja", "ko": "ko", "ch": "zh"}[bucket]
            groups[bucket].append(block)
        for bucket, group in groups.items():
            self._engine(bucket).process_image(image, group)
        return blocks
