# tasks.py
import os
import uuid

from celery import Celery

from config import Config
from upscale import upscale_bytes

celery_app = Celery(
    "upscale_service",
    broker=Config.CELERY_BROKER_URL,
    backend=Config.CELERY_RESULT_BACKEND,
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
)


@celery_app.task(bind=True, name="tasks.process_upscale")
def process_upscale(self, source_path: str, ext: str) -> dict:
    # Гарантируем каталог для результата заранее — до тяжёлого апскейла.
    os.makedirs(Config.PROCESSED_DIR, exist_ok=True)

    with open(source_path, "rb") as f:
        data = f.read()

    try:
        result_bytes = upscale_bytes(data, ext=ext)
    finally:
        try:
            os.remove(source_path)
        except OSError:
            pass

    if not ext.startswith("."):
        ext = "." + ext
    filename = f"{uuid.uuid4().hex}{ext}"
    out_path = os.path.join(Config.PROCESSED_DIR, filename)
    with open(out_path, "wb") as f:
        f.write(result_bytes)

    return {"file": filename}
