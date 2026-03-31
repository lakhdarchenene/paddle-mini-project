"""
src/structure_analyzer.py
Classify OCR text blocks into document zones: header / body / footer.
"""
import numpy as np
from PIL import Image

ZONES       = ["header", "body", "footer"]
ZONE_LABELS = {"header": "En-tête", "body": "Corps", "footer": "Pied de page"}
ZONE_COLORS = {"header": (220, 50, 50), "body": (40, 170, 60), "footer": (60, 80, 220)}


def analyze_structure(blocks: list, image_path: str) -> dict:
    """Return blocks grouped by zone (header/body/footer)."""
    img = np.array(Image.open(image_path).convert("RGB"))
    H   = img.shape[0]

    zones = {z: [] for z in ZONES}
    for b in blocks:
        ys   = [pt[1] for pt in b["box"]]
        cy   = sum(ys) / 4
        zone = "header" if cy < H * 0.12 else ("footer" if cy > H * 0.90 else "body")
        zones[zone].append(b)

    for items in zones.values():
        items.sort(key=lambda b: (
            sum(pt[1] for pt in b["box"]) / 4,
            sum(pt[0] for pt in b["box"]) / 4,
        ))
    return zones


def get_stats(zones: dict) -> dict:
    """Compute summary statistics for the reconstructed zones."""
    all_blocks = [b for v in zones.values() for b in v]
    total      = len(all_blocks)
    avg_conf   = float(np.mean([b["confidence"] for b in all_blocks])) if total else 0.0
    return {
        "total_blocks":  total,
        "avg_confidence": round(avg_conf, 4),
        "zone_counts":   {z: len(zones[z]) for z in ZONES},
    }
