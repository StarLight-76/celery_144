# config.py
import os


class Config:
    # Broker / backend Celery
    CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND = os.environ.get(
        "CELERY_RESULT_BACKEND", "redis://localhost:6379/1"
    )
    # Папка для обработанных файлов (нужна для роута /processed/<file>)
    PROCESSED_DIR = os.environ.get("PROCESSED_DIR", "processed")
    # Хранилище исходников (нужно, чтобы задача могла забрать файл)
    UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "uploads")
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "bmp", "webp"}
