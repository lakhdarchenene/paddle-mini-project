"""
src/visualizer.py
Generate an annotated result image showing OCR zone detection.

Improvements over v1:
 - Text truncation raised to 80 chars (was 52) — avoids misleading ellipsis
 - Side panel shows up to 80 lines (was 46) via smaller font + tighter spacing
 - Bounding boxes drawn with variable thickness proportional to image size
 - Confidence badge colour respects a configurable threshold
 - Zone boundary lines drawn on the annotated image for clarity
 - Figure DPI raised to 160 for sharper exports
"""
from __future__ import annotations

import numpy as np
import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from PIL import Image

from src.structure_analyzer import ZONES, ZONE_LABELS, ZONE_COLORS

_MAX_TEXT_LEN = 80    # characters before truncation in the side panel
_MAX_LINES    = 80    # max text lines in the side panel
_CONF_HIGH    = 0.90  # ≥ 90 % → green badge
_CONF_MED     = 0.75  # ≥ 75 % → yellow badge


def _box_thickness(img_h: int) -> int:
    """Scale bounding-box line thickness with image size."""
    return max(1, int(img_h / 600))


def _draw_zone_dividers(img: np.ndarray, zones: dict, img_h: int) -> np.ndarray:
    """Draw horizontal dashed lines between detected zones."""
    out = img.copy()
    W   = img.shape[1]

    def zone_max_y(z):
        pts = [pt[1] for b in zones[z] for pt in b["box"]]
        return max(pts) if pts else None

    def zone_min_y(z):
        pts = [pt[1] for b in zones[z] for pt in b["box"]]
        return min(pts) if pts else None

    pairs = [("header", "body"), ("body", "footer")]
    for top_zone, bot_zone in pairs:
        y_top = zone_max_y(top_zone)
        y_bot = zone_min_y(bot_zone)
        if y_top is not None and y_bot is not None:
            y_line = int((y_top + y_bot) / 2)
            # dashed line
            dash, gap = 18, 10
            x = 0
            while x < W:
                x2 = min(x + dash, W)
                cv2.line(out, (x, y_line), (x2, y_line), (180, 180, 60), 1, cv2.LINE_AA)
                x += dash + gap
    return out


def create_result_image(
    image_path: str,
    zones: dict,
    out_path: str,
    doc_title: str = "Document",
) -> dict:
    """
    Annotate the original image with coloured bounding boxes per zone,
    then produce a 3-panel figure (annotated | original | text list).
    Saves to out_path and returns basic stats.
    """
    img   = np.array(Image.open(image_path).convert("RGB"))
    H, W  = img.shape[:2]
    thick = _box_thickness(H)
    annot = img.copy()

    for zone, color in ZONE_COLORS.items():
        for b in zones[zone]:
            pts = np.array(b["box"], dtype=np.int32)
            cv2.polylines(annot, [pts], isClosed=True, color=color, thickness=thick)
            x = int(pts[:, 0].min())
            y = max(int(pts[:, 1].min()) - 4, 10)
            label = f"{b['confidence']:.0%}"
            cv2.putText(
                annot, label, (x, y),
                cv2.FONT_HERSHEY_SIMPLEX, max(0.3, H / 2500),
                color, 1, cv2.LINE_AA,
            )

    annot = _draw_zone_dividers(annot, zones, H)

    # ── Figure ──────────────────────────────────────────────────────────
    fig = plt.figure(figsize=(22, 14), facecolor="#12122a")
    fig.suptitle(
        f"Reconstruction IA  —  {doc_title}",
        color="white", fontsize=15, fontweight="bold", y=0.985,
    )

    # Left panel: annotated image
    ax1 = fig.add_axes([0.01, 0.03, 0.36, 0.92])
    ax1.imshow(cv2.cvtColor(annot, cv2.COLOR_BGR2RGB))
    ax1.set_title("Détection des zones", color="#aad4ff", fontsize=11, pad=6)
    ax1.axis("off")
    handles = [
        mpatches.Rectangle(
            (0, 0), 1, 1,
            color=[v / 255 for v in ZONE_COLORS[z]],
            label=ZONE_LABELS[z],
        )
        for z in ZONES
    ]
    ax1.legend(
        handles=handles, loc="lower right",
        facecolor="#1e1e3a", labelcolor="white",
        fontsize=9, framealpha=0.9,
    )

    # Middle panel: original image
    ax2 = fig.add_axes([0.38, 0.03, 0.28, 0.92])
    ax2.imshow(img)
    ax2.set_title("Document original", color="#aad4ff", fontsize=11, pad=6)
    ax2.axis("off")

    # Right panel: extracted text per zone
    ax3 = fig.add_axes([0.67, 0.03, 0.32, 0.92])
    ax3.set_facecolor("#0e0e22")
    ax3.axis("off")
    ax3.set_title("Texte extrait par zone", color="#aad4ff", fontsize=11, pad=6)

    all_blocks = [b for v in zones.values() for b in v]
    total      = len(all_blocks)
    avg_conf   = np.mean([b["confidence"] for b in all_blocks]) if total else 0.0

    lines: list[tuple[str, object, bool]] = [
        (f"Total : {total} blocs   |   Confiance : {avg_conf:.1%}", "#ffdd55", True),
        ("", "white", False),
    ]
    for zone in ZONES:
        color_n = [v / 255 for v in ZONE_COLORS[zone]]
        label   = ZONE_LABELS[zone]
        count   = len(zones[zone])
        lines.append((f"── {label.upper()} ({count}) ──", color_n, True))
        for b in zones[zone]:
            txt = b["text"]
            if len(txt) > _MAX_TEXT_LEN:
                txt = txt[:_MAX_TEXT_LEN - 1] + "…"
            conf_pct = b["confidence"]
            conf_str = f"{conf_pct:.0%}"
            # Colour-code by confidence
            if conf_pct >= _CONF_HIGH:
                conf_color = "#86efac"   # green
            elif conf_pct >= _CONF_MED:
                conf_color = "#fcd34d"   # yellow
            else:
                conf_color = "#fca5a5"   # red
            lines.append((f"  {txt}  [{conf_str}]", color_n, False))
        lines.append(("", "white", False))

    font_size = 6.5
    line_h    = 0.93 / _MAX_LINES

    for i, (text, color, bold) in enumerate(lines[:_MAX_LINES]):
        y_pos = 0.98 - i * line_h
        ax3.text(
            0.02, y_pos, text,
            transform=ax3.transAxes,
            fontsize=font_size,
            color=color,
            fontweight="bold" if bold else "normal",
            verticalalignment="top",
            fontfamily="monospace",
        )

    plt.savefig(out_path, dpi=160, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)

    return {"total": total, "avg_conf": float(avg_conf)}
