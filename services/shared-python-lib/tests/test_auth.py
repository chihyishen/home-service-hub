from fastapi import FastAPI
from fastapi.testclient import TestClient
from shared_lib.auth import install_resource_server


def _app(monkeypatch):
    monkeypatch.setenv("AUTH_ENFORCEMENT_ENABLED", "true")
    monkeypatch.setenv("OIDC_ISSUER_URI", "https://issuer.example/realms/test")
    app = FastAPI()
    install_resource_server(app, service="accounting")

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/transactions")
    def transactions():
        return []

    return TestClient(app)


def _authorized_app(monkeypatch, *, service: str, claims: dict):
    monkeypatch.setenv("AUTH_ENFORCEMENT_ENABLED", "true")
    monkeypatch.setenv("OIDC_ISSUER_URI", "https://issuer.example/realms/test")
    monkeypatch.setattr("shared_lib.auth.PyJWKClient.get_signing_key_from_jwt", lambda self, token: type("Key", (), {"key": "key"})())
    monkeypatch.setattr("shared_lib.auth.jwt.decode", lambda *args, **kwargs: claims)
    app = FastAPI()
    install_resource_server(app, service=service)

    @app.api_route("/resource", methods=["GET", "DELETE"])
    def resource():
        return {"ok": True}

    return TestClient(app)


def test_health_is_public(monkeypatch):
    response = _app(monkeypatch).get("/health")
    assert response.status_code == 200


def test_business_endpoint_rejects_missing_token(monkeypatch):
    response = _app(monkeypatch).get("/transactions")
    assert response.status_code == 401
    assert response.json() == {"error": "unauthorized"}


def test_business_endpoint_rejects_malformed_token(monkeypatch):
    response = _app(monkeypatch).get("/transactions", headers={"Authorization": "Bearer malformed"})
    assert response.status_code == 401
    assert response.json() == {"error": "unauthorized"}


def test_ui_user_without_household_role_is_forbidden(monkeypatch):
    client = _authorized_app(monkeypatch, service="accounting", claims={"azp": "home-service-ui", "scope": "accounting.read", "realm_access": {"roles": []}})
    assert client.get("/resource", headers={"Authorization": "Bearer token"}).status_code == 403


def test_scoped_agent_does_not_require_household_role(monkeypatch):
    client = _authorized_app(monkeypatch, service="accounting", claims={"azp": "agent-one", "scope": "accounting.read"})
    assert client.get("/resource", headers={"Authorization": "Bearer token"}).status_code == 200


def test_portfolio_delete_requires_admin_and_write_scope(monkeypatch):
    headers = {"Authorization": "Bearer token"}
    user = _authorized_app(monkeypatch, service="portfolio", claims={"azp": "home-service-ui", "scope": "portfolio.write", "realm_access": {"roles": ["household-user"]}})
    assert user.delete("/resource", headers=headers).status_code == 403
    admin = _authorized_app(monkeypatch, service="portfolio", claims={"azp": "home-service-ui", "scope": "portfolio.write", "realm_access": {"roles": ["household-admin"]}})
    assert admin.delete("/resource", headers=headers).status_code == 200
