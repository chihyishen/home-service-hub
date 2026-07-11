from __future__ import annotations

import os
from collections.abc import Callable

import jwt
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from jwt import PyJWKClient

PUBLIC_PATHS = {"/", "/health", "/health/ready", "/health/live"}


def _required_scope(method: str, service: str) -> str:
    operation = "read" if method in {"GET", "HEAD", "OPTIONS"} else "write"
    return f"{service}.{operation}"


def install_resource_server(app: FastAPI, *, service: str) -> None:
    """Install fail-closed JWT validation without recording tokens or claims."""
    if os.getenv("AUTH_ENFORCEMENT_ENABLED", "false").lower() != "true":
        return
    issuer = os.environ["OIDC_ISSUER_URI"].rstrip("/")
    audience = os.getenv("OIDC_AUDIENCE", "home-service-api")
    jwks = PyJWKClient(os.getenv("OIDC_JWKS_URI", f"{issuer}/protocol/openid-connect/certs"), cache_keys=True)

    @app.middleware("http")
    async def authorize(request: Request, call_next: Callable):
        if request.url.path in PUBLIC_PATHS:
            return await call_next(request)
        authorization = request.headers.get("authorization", "")
        if not authorization.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"error": "unauthorized"})
        token = authorization[7:]
        try:
            key = jwks.get_signing_key_from_jwt(token).key
            claims = jwt.decode(token, key, algorithms=["RS256", "ES256"], audience=audience, issuer=issuer)
        except Exception:
            return JSONResponse(status_code=401, content={"error": "unauthorized"})
        required = _required_scope(request.method, service)
        scopes = set(str(claims.get("scope", "")).split())
        if required not in scopes:
            return JSONResponse(status_code=403, content={"error": "forbidden"})
        roles = set(claims.get("realm_access", {}).get("roles", []))
        if claims.get("azp") == "home-service-ui" and not roles.intersection({"household-user", "household-admin"}):
            return JSONResponse(status_code=403, content={"error": "forbidden"})
        if service == "portfolio" and request.method == "DELETE" and "household-admin" not in roles:
            return JSONResponse(status_code=403, content={"error": "forbidden"})
        return await call_next(request)
