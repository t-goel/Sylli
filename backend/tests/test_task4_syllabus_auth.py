"""
Task 4 (Plan 02-02, Task 2): Tests for user_id enforcement in syllabus router and dynamo service.
Verifies that syllabus routes are auth-gated and that DynamoDB operations scope data by user_id.
"""
import os
import sys
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

# Ensure backend is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Set required env vars before any imports
os.environ.setdefault("JWT_SECRET", "test-secret-for-testing")
os.environ.setdefault("USERS_TABLE", "test-users-table")
os.environ.setdefault("SYLLABUS_TABLE", "test-syllabus-table")
os.environ.setdefault("SYLLABUS_BUCKET", "test-bucket")


# ---------------------------------------------------------------------------
# Helper: create a valid JWT for use in Authorization header
# ---------------------------------------------------------------------------

def make_jwt(user_id: str = "u-alice", username: str = "alice") -> str:
    """Create a valid HS256 JWT for testing auth-gated routes."""
    import jwt as pyjwt
    from datetime import datetime, timezone, timedelta

    return pyjwt.encode(
        {
            "user_id": user_id,
            "username": username,
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        },
        "test-secret-for-testing",
        algorithm="HS256",
    )


# ---------------------------------------------------------------------------
# dynamo_service tests: store_syllabus with user_id
# ---------------------------------------------------------------------------

class TestStoreSyllabusWithUserId:
    """Tests for dynamo_service.store_syllabus with user_id parameter."""

    def test_store_syllabus_accepts_user_id_parameter(self):
        """store_syllabus must accept a user_id keyword argument."""
        import inspect
        from services import dynamo_service
        sig = inspect.signature(dynamo_service.store_syllabus)
        assert "user_id" in sig.parameters, "store_syllabus must have user_id parameter"

    def test_store_syllabus_writes_user_id_to_item(self):
        """store_syllabus must include user_id in the DynamoDB Item."""
        from services import dynamo_service

        mock_table = MagicMock()
        mock_table.put_item.return_value = {}

        with patch.object(dynamo_service.dynamodb, "Table", return_value=mock_table):
            dynamo_service.store_syllabus(
                syllabus_id="syl-1",
                filename="test.pdf",
                s3_key="syllabus/syl-1/test.pdf",
                week_map={"1": "intro"},
                uploaded_at="2024-01-01T00:00:00+00:00",
                user_id="u-alice",
            )

        item = mock_table.put_item.call_args[1]["Item"]
        assert item.get("user_id") == "u-alice", "user_id must be stored in DynamoDB item"


# ---------------------------------------------------------------------------
# dynamo_service tests: get_syllabus with user_id ownership check
# ---------------------------------------------------------------------------

class TestGetSyllabusWithOwnershipCheck:
    """Tests for dynamo_service.get_syllabus with user_id ownership enforcement."""

    def test_get_syllabus_accepts_user_id_parameter(self):
        """get_syllabus must accept a user_id keyword argument."""
        import inspect
        from services import dynamo_service
        sig = inspect.signature(dynamo_service.get_syllabus)
        assert "user_id" in sig.parameters, "get_syllabus must have user_id parameter"

    def test_get_syllabus_returns_item_for_correct_owner(self):
        """get_syllabus returns the item when user_id matches owner."""
        from services import dynamo_service

        mock_table = MagicMock()
        mock_table.get_item.return_value = {
            "Item": {
                "syllabus_id": "syl-1",
                "user_id": "u-alice",
                "filename": "test.pdf",
            }
        }

        with patch.object(dynamo_service.dynamodb, "Table", return_value=mock_table):
            result = dynamo_service.get_syllabus("syl-1", user_id="u-alice")

        assert result is not None
        assert result["syllabus_id"] == "syl-1"

    def test_get_syllabus_returns_none_for_wrong_owner(self):
        """get_syllabus returns None when user_id does not match owner (not 403)."""
        from services import dynamo_service

        mock_table = MagicMock()
        mock_table.get_item.return_value = {
            "Item": {
                "syllabus_id": "syl-1",
                "user_id": "u-alice",
                "filename": "test.pdf",
            }
        }

        with patch.object(dynamo_service.dynamodb, "Table", return_value=mock_table):
            result = dynamo_service.get_syllabus("syl-1", user_id="u-bob")

        assert result is None, "Must return None (not raise) when wrong user requests syllabus"

    def test_get_syllabus_returns_none_when_not_found(self):
        """get_syllabus returns None when item does not exist in DynamoDB."""
        from services import dynamo_service

        mock_table = MagicMock()
        mock_table.get_item.return_value = {}  # No "Item" key

        with patch.object(dynamo_service.dynamodb, "Table", return_value=mock_table):
            result = dynamo_service.get_syllabus("no-such-id", user_id="u-alice")

        assert result is None


# ---------------------------------------------------------------------------
# syllabus router tests: auth enforcement
# ---------------------------------------------------------------------------

class TestSyllabusRouterAuthEnforcement:
    """Tests for auth enforcement on syllabus routes."""

    def _get_client(self):
        from fastapi.testclient import TestClient
        import app as app_module
        return TestClient(app_module.app, raise_server_exceptions=False)

    def test_post_syllabus_without_token_returns_401(self):
        """POST /api/v1/syllabus without Authorization header returns 401."""
        client = self._get_client()
        import io
        resp = client.post(
            "/api/v1/syllabus",
            files={"file": ("test.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")},
        )
        assert resp.status_code == 401

    def test_get_syllabus_without_token_returns_401(self):
        """GET /api/v1/syllabus/{id} without Authorization header returns 401."""
        client = self._get_client()
        resp = client.get("/api/v1/syllabus/some-id")
        assert resp.status_code == 401

    def test_get_syllabus_wrong_user_returns_404(self):
        """GET /api/v1/syllabus/{id} for another user's syllabus returns 404."""
        client = self._get_client()
        token = make_jwt(user_id="u-alice")

        with patch("routers.syllabus.fetch_syllabus", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = None  # None means not found or wrong owner
            resp = client.get(
                "/api/v1/syllabus/syl-owned-by-bob",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 404

    def test_get_syllabus_correct_user_returns_200(self):
        """GET /api/v1/syllabus/{id} for own syllabus returns 200."""
        client = self._get_client()
        token = make_jwt(user_id="u-alice")

        with patch("routers.syllabus.fetch_syllabus", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = {"syllabus_id": "syl-1", "week_map": {}}
            resp = client.get(
                "/api/v1/syllabus/syl-1",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 200

    def test_post_syllabus_with_token_passes_user_id_to_service(self):
        """POST /api/v1/syllabus with valid token passes user_id to upload_syllabus_to_s3."""
        import io
        client = self._get_client()
        token = make_jwt(user_id="u-alice")

        with patch("routers.syllabus.upload_syllabus_to_s3", new_callable=AsyncMock) as mock_upload:
            mock_upload.return_value = {"syllabus_id": "syl-new", "week_map": {}}
            resp = client.post(
                "/api/v1/syllabus",
                files={"file": ("test.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")},
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 200
        # Verify user_id was passed to the service
        call_kwargs = mock_upload.call_args[1]
        assert call_kwargs.get("user_id") == "u-alice", "user_id must be passed to upload_syllabus_to_s3"


# ---------------------------------------------------------------------------
# syllabus_service tests: user_id forwarding
# ---------------------------------------------------------------------------

class TestSyllabusServiceUserIdForwarding:
    """Tests for user_id forwarding through syllabus_service."""

    def test_upload_syllabus_to_s3_accepts_user_id(self):
        """upload_syllabus_to_s3 must accept a user_id parameter."""
        import inspect
        from services import syllabus_service
        sig = inspect.signature(syllabus_service.upload_syllabus_to_s3)
        assert "user_id" in sig.parameters, "upload_syllabus_to_s3 must accept user_id"

    def test_fetch_syllabus_accepts_user_id(self):
        """fetch_syllabus must accept a user_id parameter."""
        import inspect
        from services import syllabus_service
        sig = inspect.signature(syllabus_service.fetch_syllabus)
        assert "user_id" in sig.parameters, "fetch_syllabus must accept user_id"

    @pytest.mark.asyncio
    async def test_fetch_syllabus_passes_user_id_to_dynamo(self):
        """fetch_syllabus must pass user_id to dynamo_service.get_syllabus."""
        from services import syllabus_service

        with patch("services.syllabus_service.get_syllabus") as mock_get:
            mock_get.return_value = {"syllabus_id": "syl-1"}
            result = await syllabus_service.fetch_syllabus("syl-1", user_id="u-alice")

        mock_get.assert_called_once()
        call_args = mock_get.call_args
        # Verify user_id was passed (either as positional or keyword)
        assert "u-alice" in (list(call_args.args) + list(call_args.kwargs.values()))

    def test_syllabus_router_imports_get_current_user(self):
        """routers/syllabus.py must import get_current_user from middleware.auth."""
        import inspect
        from routers import syllabus as syllabus_module
        source = inspect.getsource(syllabus_module)
        assert "get_current_user" in source, "syllabus router must import get_current_user"
        assert "Depends" in source, "syllabus router must use Depends(get_current_user)"
