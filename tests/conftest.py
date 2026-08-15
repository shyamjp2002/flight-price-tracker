import importlib
import os

import pytest


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("ENABLE_SCHEDULER", "0")
    monkeypatch.setenv("PRICE_PROVIDER", "mock")

    from app import config, db, main, service

    for module in (config, db, service, main):
        importlib.reload(module)

    from fastapi.testclient import TestClient

    with TestClient(main.app) as test_client:
        yield test_client

    os.environ.pop("DATABASE_PATH", None)
