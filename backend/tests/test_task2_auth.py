"""
Task 2: Tests for user DynamoDB operations, auth service, and auth middleware.
Uses mocking to avoid real DynamoDB/network calls.
"""
import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# Ensure backend is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Set required env vars before any imports
os.environ.setdefault("JWT_SECRET", "test-secret-for-testing")
os.environ.setdefault("USERS_TABLE", "test-users-table")
os.environ.setdefault("SYLLABUS_TABLE", "test-syllabus-table")


# ---------------------------------------------------------------------------
# dynamo_service tests (store_user / get_user_by_username)
# ---------------------------------------------------------------------------

class TestStoredUser:
    """Tests for dynamo_service.store_user."""

    def test_store_user_raises_on_duplicate_username(self):
        """store_user must raise ValueError('Username already taken') on ConditionalCheckFailedException."""
        from botocore.exceptions import ClientError
        from services import dynamo_service

        mock_table = MagicMock()
        mock_table.put_item.side_effect = ClientError(
            {"Error": {"Code": "ConditionalCheckFailedException", "Message": "..."}},
            "PutItem"
        )

        with patch.object(dynamo_service.dynamodb, "Table", return_value=mock_table):
            with pytest.raises(ValueError, match="Username already taken"):
                dynamo_service.store_user("alice", "user-123", "hashed_pin_value")

    def test_store_user_reraises_other_client_errors(self):
        """store_user must re-raise non-conditional ClientErrors."""
        from botocore.exceptions import ClientError
        from services import dynamo_service

        mock_table = MagicMock()
        mock_table.put_item.side_effect = ClientError(
            {"Error": {"Code": "ProvisionedThroughputExceededException", "Message": "..."}},
            "PutItem"
        )

        with patch.object(dynamo_service.dynamodb, "Table", return_value=mock_table):
            with pytest.raises(ClientError):
                dynamo_service.store_user("alice", "user-123", "hashed_pin_value")

    def test_store_user_success(self):
        """store_user calls put_item with ConditionExpression attribute_not_exists."""
        from services import dynamo_service

        mock_table = MagicMock()
        mock_table.put_item.return_value = {}

        with patch.object(dynamo_service.dynamodb, "Table", return_value=mock_table):
            dynamo_service.store_user("bob", "user-456", "hashed_pin_value")

        mock_table.put_item.assert_called_once()
        call_kwargs = mock_table.put_item.call_args[1]
        assert "ConditionExpression" in call_kwargs
        assert "attribute_not_exists" in call_kwargs["ConditionExpression"]

    def test_store_user_item_contains_required_fields(self):
        """store_user puts username, user_id, hashed_pin, created_at in the item."""
        from services import dynamo_service

        mock_table = MagicMock()
        mock_table.put_item.return_value = {}

        with patch.object(dynamo_service.dynamodb, "Table", return_value=mock_table):
            dynamo_service.store_user("carol", "user-789", "hashed_pin_value")

        item = mock_table.put_item.call_args[1]["Item"]
        assert item["username"] == "carol"
        assert item["user_id"] == "user-789"
        assert item["hashed_pin"] == "hashed_pin_value"
        assert "created_at" in item


class TestGetUserByUsername:
    """Tests for dynamo_service.get_user_by_username."""

    def test_returns_user_dict_when_found(self):
        """get_user_by_username returns the Item dict when user exists."""
        from services import dynamo_service

        mock_table = MagicMock()
        mock_table.get_item.return_value = {"Item": {"username": "alice", "user_id": "u1"}}

        with patch.object(dynamo_service.dynamodb, "Table", return_value=mock_table):
            result = dynamo_service.get_user_by_username("alice")

        assert result == {"username": "alice", "user_id": "u1"}

    def test_returns_none_when_not_found(self):
        """get_user_by_username returns None when user does not exist."""
        from services import dynamo_service

        mock_table = MagicMock()
        mock_table.get_item.return_value = {}  # No "Item" key

        with patch.object(dynamo_service.dynamodb, "Table", return_value=mock_table):
            result = dynamo_service.get_user_by_username("nobody")

        assert result is None


# ---------------------------------------------------------------------------
# auth_service tests
# ---------------------------------------------------------------------------

class TestRegisterUser:
    """Tests for auth_service.register_user."""

    @pytest.mark.asyncio
    async def test_register_returns_jwt_string(self):
        """register_user returns a non-empty JWT string on success."""
        from services import auth_service

        with patch("services.auth_service.get_user_by_username", return_value=None), \
             patch("services.auth_service.store_user", return_value=None):
            token = await auth_service.register_user("dave", "1234")

        assert isinstance(token, str)
        assert len(token) > 0

    @pytest.mark.asyncio
    async def test_register_raises_if_username_taken(self):
        """register_user raises ValueError when username already exists."""
        from services import auth_service

        with patch("services.auth_service.get_user_by_username", return_value={"username": "dave"}):
            with pytest.raises(ValueError, match="Username already taken"):
                await auth_service.register_user("dave", "1234")

    @pytest.mark.asyncio
    async def test_register_validates_username_length(self):
        """register_user raises ValueError for username shorter than 3 chars."""
        from services import auth_service

        with pytest.raises(ValueError, match="Username must be at least 3 characters"):
            await auth_service.register_user("ab", "1234")

    @pytest.mark.asyncio
    async def test_register_validates_pin_length(self):
        """register_user raises ValueError for PIN outside 4-8 digit range."""
        from services import auth_service

        with pytest.raises(ValueError):
            await auth_service.register_user("alice", "123")  # Too short

        with pytest.raises(ValueError):
            await auth_service.register_user("alice", "123456789")  # Too long

    @pytest.mark.asyncio
    async def test_register_validates_pin_digits_only(self):
        """register_user raises ValueError for PIN with non-digit characters."""
        from services import auth_service

        with pytest.raises(ValueError):
            await auth_service.register_user("alice", "12ab")

    @pytest.mark.asyncio
    async def test_register_jwt_contains_user_id(self):
        """register_user JWT payload must contain user_id."""
        import jwt as pyjwt
        from services import auth_service

        with patch("services.auth_service.get_user_by_username", return_value=None), \
             patch("services.auth_service.store_user", return_value=None):
            token = await auth_service.register_user("eve", "5678")

        payload = pyjwt.decode(token, "test-secret-for-testing", algorithms=["HS256"])
        assert "user_id" in payload
        assert "username" in payload
        assert payload["username"] == "eve"


class TestLoginUser:
    """Tests for auth_service.login_user."""

    @pytest.mark.asyncio
    async def test_login_returns_none_for_unknown_user(self):
        """login_user returns None when user does not exist."""
        from services import auth_service

        with patch("services.auth_service.get_user_by_username", return_value=None):
            result = await auth_service.login_user("nobody", "1234")

        assert result is None

    @pytest.mark.asyncio
    async def test_login_returns_none_for_wrong_pin(self):
        """login_user returns None (not exception) when PIN is wrong."""
        from services import auth_service
        from passlib.context import CryptContext

        ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
        correct_hash = ctx.hash("9999")

        with patch("services.auth_service.get_user_by_username", return_value={
            "username": "frank",
            "user_id": "u-frank",
            "hashed_pin": correct_hash,
        }):
            result = await auth_service.login_user("frank", "1234")  # Wrong PIN

        assert result is None

    @pytest.mark.asyncio
    async def test_login_returns_jwt_for_correct_credentials(self):
        """login_user returns a JWT string for correct username and PIN."""
        import jwt as pyjwt
        from services import auth_service
        from passlib.context import CryptContext

        ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
        correct_hash = ctx.hash("5678")

        with patch("services.auth_service.get_user_by_username", return_value={
            "username": "grace",
            "user_id": "u-grace",
            "hashed_pin": correct_hash,
        }):
            token = await auth_service.login_user("grace", "5678")

        assert isinstance(token, str)
        payload = pyjwt.decode(token, "test-secret-for-testing", algorithms=["HS256"])
        assert payload["user_id"] == "u-grace"
        assert payload["username"] == "grace"


# ---------------------------------------------------------------------------
# middleware/auth.py tests
# ---------------------------------------------------------------------------

class TestGetCurrentUser:
    """Tests for middleware.auth.get_current_user."""

    def _make_credentials(self, token: str):
        """Create a mock HTTPAuthorizationCredentials with the given token."""
        creds = MagicMock()
        creds.credentials = token
        return creds

    def _make_valid_token(self, user_id: str = "u-test") -> str:
        """Create a valid JWT for testing."""
        import jwt as pyjwt
        from datetime import datetime, timezone, timedelta

        return pyjwt.encode(
            {
                "user_id": user_id,
                "username": "testuser",
                "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            },
            "test-secret-for-testing",
            algorithm="HS256",
        )

    def test_valid_token_returns_user_id(self):
        """get_current_user returns user_id string for a valid token."""
        from middleware.auth import get_current_user

        token = self._make_valid_token("u-valid")
        creds = self._make_credentials(token)
        result = get_current_user(creds)
        assert result == "u-valid"

    def test_invalid_token_raises_401(self):
        """get_current_user raises HTTP 401 for an invalid token."""
        from fastapi import HTTPException
        from middleware.auth import get_current_user

        creds = self._make_credentials("not.a.valid.jwt")
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(creds)
        assert exc_info.value.status_code == 401

    def test_expired_token_raises_401(self):
        """get_current_user raises HTTP 401 for an expired token."""
        import jwt as pyjwt
        from datetime import datetime, timezone, timedelta
        from fastapi import HTTPException
        from middleware.auth import get_current_user

        expired_token = pyjwt.encode(
            {
                "user_id": "u-expired",
                "username": "expireduser",
                "exp": datetime.now(timezone.utc) - timedelta(hours=1),  # Past expiry
            },
            "test-secret-for-testing",
            algorithm="HS256",
        )
        creds = self._make_credentials(expired_token)
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(creds)
        assert exc_info.value.status_code == 401

    def test_token_without_user_id_raises_401(self):
        """get_current_user raises HTTP 401 when user_id is missing from payload."""
        import jwt as pyjwt
        from datetime import datetime, timezone, timedelta
        from fastapi import HTTPException
        from middleware.auth import get_current_user

        token_no_user_id = pyjwt.encode(
            {
                "username": "testuser",
                "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            },
            "test-secret-for-testing",
            algorithm="HS256",
        )
        creds = self._make_credentials(token_no_user_id)
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(creds)
        assert exc_info.value.status_code == 401

    def test_uses_hs256_algorithm_list(self):
        """middleware/auth.py must use algorithms=list form (not string) for jwt.decode."""
        import inspect
        from middleware import auth as auth_module

        source = inspect.getsource(auth_module)
        assert 'algorithms=["HS256"]' in source or "algorithms=['HS256']" in source, (
            "jwt.decode must use algorithms=[\"HS256\"] (list form, not string)"
        )
