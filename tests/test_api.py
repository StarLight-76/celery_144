import io
from types import SimpleNamespace

import numpy as np
import cv2


def _png_bytes(w=32, h=32):
    img = np.zeros((h, w, 3), dtype=np.uint8)
    img[:, :, 0] = 120
    ok, buf = cv2.imencode(".png", img)
    assert ok
    return buf.tobytes()


def test_upscale_requires_file(client):
    r = client.post("/upscale")
    assert r.status_code == 400


def test_upscale_rejects_bad_ext(client):
    r = client.post(
        "/upscale",
        data={"file": (io.BytesIO(b"abc"), "evil.txt")},
        content_type="multipart/form-data",
    )
    assert r.status_code == 400


def test_upscale_returns_task_id_and_processes(client, monkeypatch):
    import tasks

    # Мокаем .delay → запускаем синхронно в текущем процессе
    def fake_delay(source_path, ext):
        result = tasks.process_upscale.run(source_path, ext)
        return SimpleNamespace(id="test-task-id", state="SUCCESS", result=result)

    monkeypatch.setattr(tasks.process_upscale, "delay", fake_delay)

    r = client.post(
        "/upscale",
        data={"file": (io.BytesIO(_png_bytes()), "pic.png")},
        content_type="multipart/form-data",
    )
    assert r.status_code == 202
    assert r.get_json()["task_id"] == "test-task-id"

    # /tasks/<id> — мокаем AsyncResult
    monkeypatch.setattr(
        tasks.process_upscale,
        "AsyncResult",
        lambda _id: SimpleNamespace(state="SUCCESS", result={"file": "out.png"}),
    )

    r = client.get("/tasks/test-task-id")
    assert r.status_code == 200
    body = r.get_json()
    assert body["status"] == "SUCCESS"
    assert body["result"]["url"].endswith("out.png")


def test_upscale_bytes_pipeline(tmp_path, monkeypatch):
    """upscale_bytes возвращает валидный PNG удвоенного размера."""
    import upscale as up

    class _Scaler:
        def upsample(self, img):
            return cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

    monkeypatch.setattr(up, "_scaler", _Scaler())

    out = up.upscale_bytes(_png_bytes(20, 20), ".png")
    arr = np.frombuffer(out, np.uint8)
    decoded = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    assert decoded is not None
    assert decoded.shape[0] == 40 and decoded.shape[1] == 40
