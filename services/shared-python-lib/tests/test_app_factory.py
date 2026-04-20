import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from shared_lib.app_factory import create_app


@pytest.fixture()
def dummy_router():
    router = APIRouter()

    @router.get("/dummy")
    def dummy():
        return {"msg": "hello"}

    return router


@pytest.fixture()
def mock_get_db():
    return MagicMock()


def test_create_app_includes_routers(dummy_router, mock_get_db):
    app = create_app(
        title="Test Service",
        version="0.0.1",
        routers=[dummy_router],
        get_db=mock_get_db,
    )
    client = TestClient(app)
    resp = client.get("/dummy")
    assert resp.status_code == 200
    assert resp.json() == {"msg": "hello"}


def test_create_app_has_health_endpoint(dummy_router, mock_get_db):
    app = create_app(
        title="Test Service",
        version="0.0.1",
        routers=[dummy_router],
        get_db=mock_get_db,
    )
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_create_app_error_handler_shapes_response(dummy_router, mock_get_db):
    error_router = APIRouter()

    @error_router.get("/fail")
    def fail():
        raise ValueError("boom")

    app = create_app(
        title="Test",
        version="0.0.1",
        routers=[dummy_router, error_router],
        get_db=mock_get_db,
    )
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/fail")
    assert resp.status_code == 500
    assert resp.json()["code"] == 500
