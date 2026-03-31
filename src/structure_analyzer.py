"""
src/structure_analyzer.py
Classify OCR text blocks into document zones: header / body / footer.

Improvements over v1:
 - Adaptive thresholds: instead of fixed 12 % / 90 %, we look at the actual
   vertical distribution of blocks and find natural breaks (gaps).
 - Handles documents where the header is tall (e.g. university letterheads,
   exam sheets) or the footer is large (legal disclaimers).
 - Falls back to simple percentage thresholds when the document has too few
   blocks to compute a meaningful gap analysis.
"""
from __future__ import annotations

import numpy as np
from PIL import Image

ZONES       = ["header", "body", "footer"]
ZONE_LABELS = {"header": "En-tête", "body": "Corps", "footer": "Pied de page"}
ZONE_COLORS = {
    "header": (220, 50,  50),   # red
    "body":   (40,  170, 60),   # green
    "footer": (60,  80,  220),  # blue
}

# ── Tunable defaults ──────────────────────────────────────────────────────
_HEADER_RATIO_MIN = 0.08   # header occupies at least 8 % of height
_HEADER_RATIO_MAX = 0.25   # … but no more than 25 %
_FOOTER_RATIO_MIN = 0.80   # footer starts at least at 80 % of height
_FOOTER_RATIO_MAX = 0.95   # … and no later than 95 %


def _centre_y(block: dict) -> float:
    return sum(pt[1] for pt in block["box"]) / 4


def _find_adaptive_thresholds(blocks: list[dict], img_height: int) -> tuple[float, float]:
    """
    Find the best header/footer cut points by looking for the two largest
    vertical gaps in the sorted list of block centre-Y values.

    Returns (header_cut_y, footer_cut_y) in absolute pixels.
    """
    if len(blocks) < 6:
        # Too few blocks — use safe fixed ratios
        return img_height * 0.15, img_height * 0.88

    centres = sorted(_centre_y(b) for b in blocks)
    gaps    = [(centres[i + 1] - centres[i], i) for i in range(len(centres) - 1)]
    # Sort gaps by size descending
    gaps.sort(key=lambda g: g[0], reverse=True)

    header_cut = img_height * _HEADER_RATIO_MAX   # default
    footer_cut = img_height * _FOOTER_RATIO_MIN   # default

    # Evaluate the two largest gaps as potential zone boundaries
    candidates = sorted([g[1] for g in gaps[:4]])  # up to 4 largest gaps

    for idx in candidates:
        cut_y     = (centres[idx] + centres[idx + 1]) / 2
        ratio     = cut_y / img_height

        if _HEADER_RATIO_MIN <= ratio <= _HEADER_RATIO_MAX:
            header_cut = cut_y
        elif _FOOTER_RATIO_MIN <= ratio <= _FOOTER_RATIO_MAX:
            footer_cut = cut_y

    # Sanity: header must be above footer
    if header_cut >= footer_cut:
        header_cut = img_height * 0.15
        footer_cut = img_height * 0.85

    return header_cut, footer_cut


def analyze_structure(blocks: list[dict], image_path: str) -> dict:
    """Return blocks grouped by zone (header / body / footer)."""
    img    = np.array(Image.open(image_path).convert("RGB"))
    H      = img.shape[0]

    header_cut, footer_cut = _find_adaptive_thresholds(blocks, H)

    zones: dict[str, list] = {z: [] for z in ZONES}
    for b in blocks:
        cy = _centre_y(b)
        if cy < header_cut:
            zone = "header"
        elif cy > footer_cut:
            zone = "footer"
        else:
            zone = "body"
        zones[zone].append(b)

    # Sort each zone top-to-bottom, left-to-right
    for items in zones.values():
        items.sort(key=lambda b: (
            round(_centre_y(b) / 10),          # bucket by ~10 px rows
            sum(pt[0] for pt in b["box"]) / 4, # then left-to-right
        ))

    return zones


def get_stats(zones: dict) -> dict:
    """Compute summary statistics for the reconstructed zones."""
    all_blocks = [b for v in zones.values() for b in v]
    total      = len(all_blocks)
    avg_conf   = float(np.mean([b["confidence"] for b in all_blocks])) if total else 0.0
    return {
        "total_blocks":   total,
        "avg_confidence": round(avg_conf, 4),
        "zone_counts":    {z: len(zones[z]) for z in ZONES},
    }
