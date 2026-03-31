"""
src/ocr_engine.py
Singleton wrapper around PaddleOCR — supports multi-language detection.
Engines are cached per language to avoid re-initialization overhead.
"""
from __future__ import annotations
import logging

logging.getLogger("ppocr").setLevel(logging.ERROR)

_engines: dict = {}   # lang -> PaddleOCR instance

# Languages supported by PaddleOCR (subset most useful for admin docs)
SUPPORTED_LANGS = {
    "fr":    "Français",
    "en":    "English",
    "ar":    "العربية",
    "ch":    "中文",
    "latin": "Latin / Multi",
}


def get_ocr_engine(lang: str = "fr"):
    """Return (and cache) a PaddleOCR instance for the given language."""
    global _engines
    if lang not in _engines:
        from paddleocr import PaddleOCR
        _engines[lang] = PaddleOCR(
            use_angle_cls=True,
            lang=lang,
            show_log=False,
            enable_mkldnn=True,   # faster inference on CPU
        )
    return _engines[lang]


def run_ocr(image_path: str, lang: str = "fr") -> list[dict]:
    """
    Run OCR on one image.

    Returns a list of block dicts:
        {box, text, confidence}

    Tries the requested language first; if avg confidence < 60 % and lang != 'en',
    also tries English and merges whichever gave better results.
    """
    blocks = _ocr_image(image_path, lang)

    # Auto-fallback: if confidence is very low, try English as well
    if lang != "en" and blocks:
        avg = sum(b["confidence"] for b in blocks) / len(blocks)
        if avg < 0.60:
            en_blocks = _ocr_image(image_path, "en")
            if en_blocks:
                en_avg = sum(b["confidence"] for b in en_blocks) / len(en_blocks)
                if en_avg > avg:
                    blocks = en_blocks

    return blocks


def _ocr_image(image_path: str, lang: str) -> list[dict]:
    """Internal: run PaddleOCR and normalise output."""
    ocr    = get_ocr_engine(lang)
    result = ocr.ocr(image_path, cls=True)
    blocks = []
    if result and result[0]:
        for line in result[0]:
            box, (text, confidence) = line
            text = text.strip()
            if not text:
                continue
            blocks.append({
                "box":        [[float(x), float(y)] for x, y in box],
                "text":       text,
                "confidence": float(confidence),
            })
    return blocks
