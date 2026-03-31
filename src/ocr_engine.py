"""
src/ocr_engine.py
Singleton wrapper around PaddleOCR — initialize once, reuse everywhere.
"""
_ocr_instance = None


def get_ocr_engine():
    global _ocr_instance
    if _ocr_instance is None:
        from paddleocr import PaddleOCR
        _ocr_instance = PaddleOCR(use_angle_cls=True, lang="fr", show_log=False)
    return _ocr_instance


def run_ocr(image_path: str) -> list:
    """Run OCR on one image. Returns a list of block dicts."""
    ocr    = get_ocr_engine()
    result = ocr.ocr(image_path, cls=True)
    blocks = []
    if result and result[0]:
        for line in result[0]:
            box, (text, confidence) = line
            blocks.append({
                "box":        [[float(x), float(y)] for x, y in box],
                "text":       text,
                "confidence": float(confidence),
            })
    return blocks
