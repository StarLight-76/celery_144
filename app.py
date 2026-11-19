# app.py
import os
import uuid

from flask import Flask, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename

from config import Config
from tasks import process_upscale

app = Flask(__name__)
app.config.from_object(Config)
# Ограничение размера загружаемого файла (10 МБ) — защита от «тяжёлых» запросов
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024


def _allowed(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in Config.ALLOWED_EXTENSIONS


@app.errorhandler(413)
def too_large(_e):
    return jsonify({"error": "file too large (max 10 MB)"}), 413


@app.route("/upscale", methods=["POST"])
def upscale_route():
    if "file" not in request.files:
        return jsonify({"error": "file is required"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "empty filename"}), 400

    if not _allowed(file.filename):
        return jsonify({"error": "unsupported file type"}), 400

    # Гарантируем существование каталога на момент записи.
    # Если UPLOAD_DIR подменили после старта приложения — makedirs создаст его.
    os.makedirs(Config.UPLOAD_DIR, exist_ok=True)

    ext = os.path.splitext(secure_filename(file.filename))[1].lower()
    tmp_name = f"{uuid.uuid4().hex}{ext}"
    tmp_path = os.path.join(Config.UPLOAD_DIR, tmp_name)

    try:
        file.save(tmp_path)
    except OSError as exc:
        return jsonify({"error": f"failed to save file: {exc}"}), 500

    task = process_upscale.delay(tmp_path, ext)
    return jsonify({"task_id": task.id}), 202


@app.route("/tasks/<task_id>", methods=["GET"])
def task_status(task_id: str):
    task = process_upscale.AsyncResult(task_id)

    if task.state == "PENDING":
        response = {"status": "PENDING", "result": None}
    elif task.state == "STARTED":
        response = {"status": "STARTED", "result": None}
    elif task.state == "SUCCESS":
        payload = task.result or {}
        response = {
            "status": "SUCCESS",
            "result": {
                "file": payload.get("file"),
                "url": f"/processed/{payload.get('file')}",
            },
        }
    elif task.state == "FAILURE":
        response = {"status": "FAILURE", "error": str(task.info)}
    else:
        response = {"status": task.state, "result": task.result}

    return jsonify(response)


@app.route("/processed/<path:filename>", methods=["GET"])
def processed_file(filename: str):
    return send_from_directory(Config.PROCESSED_DIR, filename)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
