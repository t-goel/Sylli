"""
Task 3 (Plan 02-02, Task 1): Tests for auth HTTP endpoints and CORS configuration.
Tests the auth router (register/login) and app.py CORS setup.
Uses FastAPI TestClient with mocked auth_service to avoid real DynamoDB calls.
"""
import os
import sys
import pytest
from unittest.mock import patch, AsyncMock

# Ensure backend is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Set required env vars before any imports
os.environ.setdefault("JWT_SECRET", "test-secret-for-testing")
os.environ.setdefault("USERS_TABLE", "test-users-table")
os.environ.setdefault("SYLLABUS_TABLE", "test-syllabus-table")
os.environ.setdefault("SYLLABUS_BUCKET", "test-bucket")


# ---------------------------------------------------------------------------
# Structural / import tests (fail before the files exist)
# ---------------------------------------------------------------------------

class TestAuthRouterStructure:
    """Tests that verify the auth router file exists and has expected content."""

    def test_auth_router_file_exists(self):
        """backend/routers/auth.py must be importable."""
        from routers import auth  # noqa: F401

    def test_auth_router_has_register_route(self):
        """auth.py must define a POST /auth/register route."""
        import inspect
        from routers import auth as auth_module
        source = inspect.getsource(auth_module)
        assert "auth/register" in source, "Missing /auth/register route in auth.py"

    def test_auth_router_has_login_route(self):
        """auth.py must define a POST /auth/login route."""
        import inspect
        from routers import auth as auth_module
        source = inspect.getsource(auth_module)
        assert "auth/login" in source, "Missing /auth/login route in auth.py"

    def test_auth_router_exports_router(self):
        """auth.py must export an APIRouter named 'router'."""
        from routers import auth as auth_module
        from fastapi import APIRouter
        assert hasattr(auth_module, "router"), "auth.py must define 'router'"
        assert isinstance(auth_module.router, APIRouter)

    def test_app_has_cors_middleware(self):
        """app.py must include CORSMiddleware."""
        import inspect
        import app as app_module
        source = inspect.getsource(app_module)
        assert "CORSMiddleware" in source, "app.py must add CORSMiddleware"

    def test_app_includes_auth_router(self):
        """app.py must include the auth router."""
        import inspect
        import app as app_module
        source = inspect.getsource(app_module)
        assert "auth" in source, "app.py must import and include auth router"


# ---------------------------------------------------------------------------
# HTTP behavior tests using TestClient
# ---------------------------------------------------------------------------

class TestRegisterEndpoint:
    """Tests for POST /api/v1/auth/register."""

    def _get_client(self):
        from fastapi.testclient import TestClient
        import importlib
        import app as app_module
        importlib.reload(app_module)
        return TestClient(app_module.app)

    def test_register_returns_200_with_token(self):
        """POST /auth/register with valid credentials returns 200 with token."""
        from fastapi.testclient import TestClient
        import app as app_module

        with patch("routers.auth.register_user", new_callable=AsyncMock) as mock_reg:
            mock_reg.return_value = "fake.jwt.token"
            client = TestClient(app_module.app)
            resp = client.post(
                "/api/v1/auth/register",
                json={"username": "alice", "pin": "1234"},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert "token" in body
        assert body["token"] == "fake.jwt.token"

    def test_register_returns_409_for_duplicate_username(self):
        """POST /auth/register with already-taken username returns 409."""
        import app as app_module

        with patch("routers.auth.register_user", new_callable=AsyncMock) as mock_reg:
            mock_reg.side_effect = ValueError("Username already taken")
            from fastapi.testclient import TestClient
            client = TestClient(app_module.app)
            resp = client.post(
                "/api/v1/auth/register",
                json={"username": "alice", "pin": "1234"},
            )

        assert resp.status_code == 409
        assert "Username already taken" in resp.json()["detail"]

    def test_register_returns_422_for_missing_fields(self):
        """POST /auth/register with missing body returns 422 (Pydantic validation)."""
        from fastapi.testclient import TestClient
        import app as app_module

        client = TestClient(app_module.app)
        resp = client.post("/api/v1/auth/register", json={})
        assert resp.status_code == 422


class TestLoginEndpoint:
    """Tests for POST /api/v1/auth/login."""

    def test_login_returns_200_with_token(self):
        """POST /auth/login with correct credentials returns 200 with token."""
        import app as app_module

        with patch("routers.auth.login_user", new_callable=AsyncMock) as mock_login:
            mock_login.return_value = "valid.jwt.token"
            from fastapi.testclient import TestClient
            client = TestClient(app_module.app)
            resp = client.post(
                "/api/v1/auth/login",
                json={"username": "alice", "pin": "1234"},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert "token" in body
        assert body["token"] == "valid.jwt.token"

    def test_login_returns_401_for_wrong_pin(self):
        """POST /auth/login with wrong PIN returns 401."""
        import app as app_module

        with patch("routers.auth.login_user", new_callable=AsyncMock) as mock_login:
            mock_login.return_value = None  # login_user returns None on bad credentials
            from fastapi.testclient import TestClient
            client = TestClient(app_module.app)
            resp = client.post(
                "/api/v1/auth/login",
                json={"username": "alice", "pin": "9999"},
            )

        assert resp.status_code == 401
        assert "Invalid username or PIN" in resp.json()["detail"]

    def test_login_returns_422_for_missing_fields(self):
        """POST /auth/login with missing body returns 422 (Pydantic validation)."""
        from fastapi.testclient import TestClient
        import app as app_module

        client = TestClient(app_module.app)
        resp = client.post("/api/v1/auth/login", json={})
        assert resp.status_code == 422


class TestCORSConfiguration:
    """Tests for CORS middleware configuration in app.py."""

    def test_cors_allows_localhost_3000(self):
        """CORS preflight from localhost:3000 must not be blocked."""
        from fastapi.testclient import TestClient
        import app as app_module

        client = TestClient(app_module.app)
        resp = client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )
        # CORS preflight should succeed (200 or 204)
        assert resp.status_code in (200, 204)
        assert "access-control-allow-origin" in resp.headers
        assert resp.headers["access-control-allow-origin"] in (
            "http://localhost:3000",
            "*",
        )
