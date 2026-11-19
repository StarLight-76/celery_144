# upscale.py
import os
import threading
from typing import Optional

import cv2
import numpy as np
from cv2 import dnn_superres

_MODEL_PATH = os.environ.get("EDSR_MODEL_PATH", "EDSR_x2.pb")
_scaler: Optional[dnn_superres.DnnSuperResImpl] = None
_lock = threading.Lock()


def get_scaler() -> dnn_superres.DnnSuperResImpl:
    """Ленивая инициализация модели — считывается с диска ровно один раз."""
    global _scaler
    if _scaler is None:
        with _lock:
            if _scaler is None:
                scaler = dnn_superres.DnnSuperResImpl_create()
                scaler.readModel(_MODEL_PATH)
                scaler.setModel("edsr", 2)
                _scaler = scaler
    return _scaler


def upscale_bytes(image_bytes: bytes, ext: str = ".png") -> bytes:
    """
    Апскейлит изображение из bytes в bytes — без сохранения на диск.
    :param image_bytes: содержимое исходного файла
    :param ext: расширение (для выбора кодека: .png / .jpg)
    :return: байты обработанного изображения
    """
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Не удалось декодировать изображение")

    scaler = get_scaler()
    result = scaler.upsample(image)

    ext = ext.lower().lstrip(".")
    if ext in ("jpg", "jpeg"):
        ok, buf = cv2.imencode(".jpg", result, [cv2.IMWRITE_JPEG_QUALITY, 95])
    else:
        ok, buf = cv2.imencode(".png", result)
    if not ok:
        raise RuntimeError("Не удалось закодировать изображение")
    return buf.tobytes()


# Оставляем обратно-совместимую функцию для работы с путями (не используется в сервисе)
def upscale(input_path: str, output_path: str, model_path: str = None) -> None:
    global _MODEL_PATH
    if model_path and model_path != _MODEL_PATH:
        _MODEL_PATH = model_path
        global _scaler
        with _lock:
            _scaler = None
    with open(input_path, "rb") as f:
        data = upscale_bytes(f.read(), os.path.splitext(input_path)[1])
    with open(output_path, "wb") as f:
        f.write(data)
        