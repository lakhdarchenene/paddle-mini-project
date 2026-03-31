"""
web/app.py
Flask backend — handles image upload, OCR processing, and serves results.
"""
import os
import sys
import uuid
import datetime

# Allow imports from project root
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from flask import Flask, request, jsonify, render_template, send_from_directory

from src.ocr_engine        import run_ocr
from src.structure_analyzer import analyze_structure, get_stats
from src.visualizer         import create_result_image

# ── Paths ──────────────────────────────────────────────────────────────────
UPLOAD_DIR  = os.path.join(ROOT, "uploads")
RESULTS_DIR = os.path.join(ROOT, "results")
TMPL_DIR    = os.path.join(os.path.dirname(__file__), "templates")
STATIC_DIR  = os.path.join(os.path.dirname(__file__), "static")

for d in (UPLOAD_DIR, RESULTS_DIR):
    os.makedirs(d, exist_ok=True)

# ── App ────────────────────────────────────────────────────────────────────
app = Flask(__name__, template_folder=TMPL_DIR, static_folder=STATIC_DIR)
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024   # 20 MB

ALLOWED = {"png", "jpg", "jpeg", "bmp", "tiff", "webp"}


def allowed(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED


# ── Routes ─────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "Aucun fichier fourni."}), 400

    file = request.files["file"]
    if not file or file.filename == "":
        return jsonify({"error": "Fichier vide."}), 400

    if not allowed(file.filename):
        return jsonify({"error": f"Format non supporté. Utilisez : {', '.join(ALLOWED)}"}), 400

    # Save upload
    ext      = file.filename.rsplit(".", 1)[1].lower()
    uid      = uuid.uuid4().hex
    filename = f"{uid}.{ext}"
    up_path  = os.path.join(UPLOAD_DIR, filename)
    file.save(up_path)

    try:
        # OCR
        blocks    = run_ocr(up_path)
        zones     = analyze_structure(blocks, up_path)
        stats     = get_stats(zones)

        # Annotated result image
        res_name  = f"result_{uid}.png"
        res_path  = os.path.join(RESULTS_DIR, res_name)
        doc_title = request.form.get("title", file.filename)
        create_result_image(up_path, zones, res_path, doc_title)

        # Build serialisable zone data
        zones_data = {
            z: [{"text": b["text"], "confidence": round(b["confidence"] * 100, 1)}
                for b in items]
            for z, items in zones.items()
        }

        return jsonify({
            "success":      True,
            "filename":     file.filename,
            "stats":        stats,
            "zones":        zones_data,
            "upload_url":   f"/uploads/{filename}",
            "result_url":   f"/results/{res_name}",
            "processed_at": datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        })

    except Exception as e:
        return jsonify({"error": f"Erreur OCR : {str(e)}"}), 500


@app.route("/api/history")
def history():
    """Return the 12 most recent result images."""
    files = sorted(
        [f for f in os.listdir(RESULTS_DIR) if f.endswith(".png")],
        key=lambda f: os.path.getmtime(os.path.join(RESULTS_DIR, f)),
        reverse=True,
    )
    return jsonify([
        {
            "name": f,
            "url":  f"/results/{f}",
            "date": datetime.datetime.fromtimestamp(
                os.path.getmtime(os.path.join(RESULTS_DIR, f))
            ).strftime("%d/%m/%Y %H:%M"),
        }
        for f in files[:12]
    ])


@app.route("/uploads/<path:filename>")
def serve_upload(filename):
    return send_from_directory(UPLOAD_DIR, filename)


@app.route("/results/<path:filename>")
def serve_result(filename):
    return send_from_directory(RESULTS_DIR, filename)


# ── Run ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)
