import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from shared_lib.errors import register_error_handlers


@pytest.fixture()
def app():
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/ok")
    def ok():
        return {"msg": "ok"}

    @app.get("/http-error")
    def http_error():
        raise HTTPException(status_code=422, detail="bad input")

    @app.get("/unexpected")
    def unexpected():
        raise RuntimeError("boom")

    return app


@pytest.fixture()
def client(app):
    return TestClient(app, raise_server_exceptions=False)


def test_normal_response_unaffected(client):
    resp = client.get("/ok")
    assert resp.status_code == 200
    assert resp.json() == {"msg": "ok"}


def test_http_exception_returns_standard_shape(client):
    resp = client.get("/http-error")
    assert resp.status_code == 422
    body = resp.json()
    assert body["code"] == 422
    assert body["message"] == "bad input"
    assert "trace_id" in body


def test_unhandled_exception_returns_500(client):
    resp = client.get("/unexpected")
    assert resp.status_code == 500
    body = resp.json()
    assert body["code"] == 500
    assert "trace_id" in body
