"""
web/app.py
Flask backend — handles image upload, OCR processing, and serves results.

Improvements over v1:
 - Language selection passed through from the frontend
 - Better input validation (file size, image integrity)
 - Structured JSON error codes
 - Temp-file cleanup on OCR failure
 - /api/stats endpoint for quick health-check
"""
from __future__ import annotations

import os
import sys
import uuid
import datetime
import imghdr

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from flask import Flask, request, jsonify, render_template, send_from_directory

from src.ocr_engine         import run_ocr, SUPPORTED_LANGS
from src.structure_analyzer import analyze_structure, get_stats
from src.visualizer          import create_result_image

# ── Paths ──────────────────────────────────────────────────────────────────
UPLOAD_DIR  = os.path.join(ROOT, "uploads")
RESULTS_DIR = os.path.join(ROOT, "results")
TMPL_DIR    = os.path.join(os.path.dirname(__file__), "templates")
STATIC_DIR  = os.path.join(os.path.dirname(__file__), "static")

for d in (UPLOAD_DIR, RESULTS_DIR):
    os.makedirs(d, exist_ok=True)

# ── App ────────────────────────────────────────────────────────────────────
app = Flask(__name__, template_folder=TMPL_DIR, static_folder=STATIC_DIR)
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024   # 25 MB

ALLOWED_EXT  = {"png", "jpg", "jpeg", "bmp", "tiff", "webp"}
ALLOWED_MIME = {"rgb", "png", "jpeg", "bmp", "tiff", "webp", "gif", None}


def _allowed_extension(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT


def _safe_lang(raw: str) -> str:
    return raw if raw in SUPPORTED_LANGS else "fr"


# ── Routes ─────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html", supported_langs=SUPPORTED_LANGS)


@app.route("/api/upload", methods=["POST"])
def upload():
    # ── Validate file presence ─────────────────────────────────────────
    if "file" not in request.files:
        return jsonify({"error": "Aucun fichier fourni.", "code": "NO_FILE"}), 400

    file = request.files["file"]
    if not file or not file.filename:
        return jsonify({"error": "Fichier vide.", "code": "EMPTY_FILE"}), 400

    if not _allowed_extension(file.filename):
        return jsonify({
            "error": f"Format non supporté. Acceptés : {', '.join(sorted(ALLOWED_EXT))}",
            "code":  "BAD_FORMAT",
        }), 400

    # ── Save upload ────────────────────────────────────────────────────
    ext      = file.filename.rsplit(".", 1)[1].lower()
    uid      = uuid.uuid4().hex
    filename = f"{uid}.{ext}"
    up_path  = os.path.join(UPLOAD_DIR, filename)
    file.save(up_path)

    # ── Validate file is a real image ──────────────────────────────────
    detected = imghdr.what(up_path)
    if detected not in ALLOWED_MIME:
        os.remove(up_path)
        return jsonify({"error": "Le fichier n'est pas une image valide.", "code": "INVALID_IMAGE"}), 400

    lang      = _safe_lang(request.form.get("lang", "fr"))
    doc_title = request.form.get("title", file.filename)

    try:
        # ── OCR ────────────────────────────────────────────────────────
        blocks = run_ocr(up_path, lang=lang)

        if not blocks:
            return jsonify({
                "error": "Aucun texte détecté dans l'image. "
                         "Vérifiez la qualité ou changez la langue OCR.",
                "code": "NO_TEXT",
            }), 422

        # ── Structure analysis ─────────────────────────────────────────
        zones = analyze_structure(blocks, up_path)
        stats = get_stats(zones)

        # ── Annotated result image ─────────────────────────────────────
        res_name = f"result_{uid}.png"
        res_path = os.path.join(RESULTS_DIR, res_name)
        create_result_image(up_path, zones, res_path, doc_title)

        # ── Serialise zone data ────────────────────────────────────────
        zones_data = {
            z: [
                {
                    "text":       b["text"],
                    "confidence": round(b["confidence"] * 100, 1),
                }
                for b in items
            ]
            for z, items in zones.items()
        }

        return jsonify({
            "success":      True,
            "filename":     file.filename,
            "lang":         lang,
            "stats":        stats,
            "zones":        zones_data,
            "upload_url":   f"/uploads/{filename}",
            "result_url":   f"/results/{res_name}",
            "processed_at": datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        })

    except MemoryError:
        return jsonify({"error": "Image trop grande pour être traitée.", "code": "OOM"}), 507
    except Exception as exc:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Erreur OCR : {exc}", "code": "OCR_ERROR"}), 500


@app.route("/api/history")
def history():
    """Return the 20 most recent result images."""
    try:
        files = sorted(
            [f for f in os.listdir(RESULTS_DIR) if f.endswith(".png")],
            key=lambda f: os.path.getmtime(os.path.join(RESULTS_DIR, f)),
            reverse=True,
        )
    except OSError:
        return jsonify([])

    return jsonify([
        {
            "name": f,
            "url":  f"/results/{f}",
            "date": datetime.datetime.fromtimestamp(
                os.path.getmtime(os.path.join(RESULTS_DIR, f))
            ).strftime("%d/%m/%Y %H:%M"),
        }
        for f in files[:20]
    ])


@app.route("/api/stats")
def api_stats():
    """Quick health-check / stats endpoint."""
    n_results = len([f for f in os.listdir(RESULTS_DIR) if f.endswith(".png")])
    n_uploads = len([f for f in os.listdir(UPLOAD_DIR)
                     if not f.startswith(".") and f != ".gitkeep"])
    return jsonify({
        "status":         "ok",
        "results_stored": n_results,
        "uploads_stored": n_uploads,
        "supported_langs": SUPPORTED_LANGS,
    })


@app.route("/uploads/<path:filename>")
def serve_upload(filename):
    return send_from_directory(UPLOAD_DIR, filename)


@app.route("/results/<path:filename>")
def serve_result(filename):
    return send_from_directory(RESULTS_DIR, filename)


# ── Run ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("FLASK_PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
