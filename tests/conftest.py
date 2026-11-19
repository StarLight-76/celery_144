# tests/conftest.py
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


@pytest.fixture
def client(monkeypatch, tmp_path):
    import config
    monkeypatch.setattr(config.Config, "UPLOAD_DIR", str(tmp_path / "up"))
    monkeypatch.setattr(config.Config, "PROCESSED_DIR", str(tmp_path / "pr"))

    from app import app as flask_app
    flask_app.config.update(TESTING=True)
    with flask_app.test_client() as c:
        yield c
