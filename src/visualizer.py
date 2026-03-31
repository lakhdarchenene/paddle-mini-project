"""
src/visualizer.py
Generate an annotated result image showing OCR zone detection.
"""
import numpy as np
import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from PIL import Image

from src.structure_analyzer import ZONES, ZONE_LABELS, ZONE_COLORS


def create_result_image(image_path: str, zones: dict,
                        out_path: str, doc_title: str = "Document") -> dict:
    """
    Annotate the original image with colored bounding boxes per zone,
    then produce a 3-panel figure (annotated | original | text list).
    Saves to out_path and returns basic stats.
    """
    img   = np.array(Image.open(image_path).convert("RGB"))
    annot = img.copy()

    for zone, color in ZONE_COLORS.items():
        for b in zones[zone]:
            pts = np.array(b["box"], dtype=np.int32)
            cv2.polylines(annot, [pts], isClosed=True, color=color, thickness=2)
            x = int(pts[0][0])
            y = max(int(pts[0][1]) - 4, 10)
            cv2.putText(annot, f"{b['confidence']:.0%}",
                        (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.38, color, 1, cv2.LINE_AA)

    # ── Figure ──────────────────────────────────────────────────────────────
    fig = plt.figure(figsize=(20, 13), facecolor="#12122a")
    fig.suptitle(f"Reconstruction IA  —  {doc_title}",
                 color="white", fontsize=15, fontweight="bold", y=0.98)

    # Left: annotated
    ax1 = fig.add_axes([0.01, 0.04, 0.36, 0.90])
    ax1.imshow(cv2.cvtColor(annot, cv2.COLOR_BGR2RGB))
    ax1.set_title("Détection des zones", color="#aad4ff", fontsize=11, pad=6)
    ax1.axis("off")
    handles = [mpatches.Rectangle((0, 0), 1, 1,
               color=[v / 255 for v in ZONE_COLORS[z]],
               label=ZONE_LABELS[z]) for z in ZONES]
    ax1.legend(handles=handles, loc="lower right",
               facecolor="#1e1e3a", labelcolor="white", fontsize=9, framealpha=0.9)

    # Middle: original
    ax2 = fig.add_axes([0.38, 0.04, 0.28, 0.90])
    ax2.imshow(img)
    ax2.set_title("Document original", color="#aad4ff", fontsize=11, pad=6)
    ax2.axis("off")

    # Right: text per zone
    ax3 = fig.add_axes([0.67, 0.04, 0.32, 0.90])
    ax3.set_facecolor("#0e0e22")
    ax3.axis("off")
    ax3.set_title("Texte extrait par zone", color="#aad4ff", fontsize=11, pad=6)

    all_blocks = [b for v in zones.values() for b in v]
    total      = len(all_blocks)
    avg_conf   = np.mean([b["confidence"] for b in all_blocks]) if total else 0

    lines = [
        (f"Total : {total} blocs   |   Confiance : {avg_conf:.1%}", "#ffdd55", True),
        ("", "white", False),
    ]
    for zone in ZONES:
        color_n = [v / 255 for v in ZONE_COLORS[zone]]
        label   = ZONE_LABELS[zone]
        lines.append((f"── {label.upper()} ({len(zones[zone])}) ──", color_n, True))
        for b in zones[zone]:
            txt = (b["text"][:52] + "…") if len(b["text"]) > 52 else b["text"]
            lines.append((f"  {txt}  [{b['confidence']:.0%}]", color_n, False))
        lines.append(("", "white", False))

    MAX = 46
    for i, (text, color, bold) in enumerate(lines[:MAX]):
        y_pos = 0.97 - i * (0.94 / MAX)
        ax3.text(0.02, y_pos, text, transform=ax3.transAxes,
                 fontsize=7.5, color=color,
                 fontweight="bold" if bold else "normal",
                 verticalalignment="top", fontfamily="monospace")

    plt.savefig(out_path, dpi=140, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close()

    return {"total": total, "avg_conf": float(avg_conf)}
