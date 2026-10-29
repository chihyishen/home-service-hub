from unittest.mock import MagicMock

import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient
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
    session = MagicMock()

    def get_db():
        return session

    get_db.session = session
    return get_db


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

    resp = client.get("/health/ready")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "database": "ok"}


def test_readiness_is_unavailable_when_database_query_fails(dummy_router, mock_get_db):
    mock_get_db.session.execute.side_effect = RuntimeError("database unavailable")
    app = create_app(
        title="Test Service",
        version="0.0.1",
        routers=[dummy_router],
        get_db=mock_get_db,
    )

    resp = TestClient(app).get("/health/ready")

    assert resp.status_code == 503
    assert resp.json() == {"status": "degraded", "database": "error: RuntimeError"}


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
