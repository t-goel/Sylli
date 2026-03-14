"""
Task 1: Tests for auth dependencies and infrastructure configuration.
Verifies requirements.txt has PyJWT and passlib, and that template.yaml
has the expected UsersTable and env var config.
"""
import os
import re


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BACKEND_ROOT = os.path.join(PROJECT_ROOT, "backend")


def _read_requirements():
    path = os.path.join(BACKEND_ROOT, "requirements.txt")
    with open(path) as f:
        return f.read()


def _read_template():
    path = os.path.join(PROJECT_ROOT, "template.yaml")
    with open(path) as f:
        return f.read()


def test_requirements_has_pyjwt():
    """requirements.txt must contain PyJWT."""
    content = _read_requirements()
    assert "PyJWT" in content, "PyJWT missing from requirements.txt"


def test_requirements_has_passlib():
    """requirements.txt must contain passlib[bcrypt]."""
    content = _read_requirements()
    assert "passlib" in content, "passlib missing from requirements.txt"
    assert "bcrypt" in content, "passlib[bcrypt] (bcrypt extra) missing from requirements.txt"


def test_template_has_users_table():
    """template.yaml must define UsersTable with sylli-users-table name."""
    content = _read_template()
    assert "sylli-users-table" in content, "sylli-users-table missing from template.yaml"
    assert "UsersTable" in content, "UsersTable resource missing from template.yaml"


def test_template_has_jwt_secret_env():
    """SylliFunction must have JWT_SECRET in env vars."""
    content = _read_template()
    assert "JWT_SECRET" in content, "JWT_SECRET env var missing from template.yaml"


def test_template_has_users_table_env():
    """SylliFunction must have USERS_TABLE in env vars."""
    content = _read_template()
    assert "USERS_TABLE" in content, "USERS_TABLE env var missing from template.yaml"


def test_template_has_dynamodb_policies_for_users():
    """SylliFunction must have DynamoDB read/write policies for users table."""
    content = _read_template()
    # Count occurrences of sylli-users-table — should appear in policies too
    occurrences = content.count("sylli-users-table")
    # At minimum: table definition (1) + 2 policies = 3 occurrences
    assert occurrences >= 3, (
        f"Expected sylli-users-table in table definition + 2 policies, found {occurrences} occurrences"
    )


def test_pyjwt_importable():
    """PyJWT must be importable (installed in environment)."""
    try:
        import jwt
        assert hasattr(jwt, "encode"), "jwt.encode not available"
    except ImportError:
        raise AssertionError("PyJWT not installed — run: pip install PyJWT")


def test_passlib_importable():
    """passlib must be importable with bcrypt backend."""
    try:
        from passlib.context import CryptContext
        ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
        assert ctx is not None
    except ImportError:
        raise AssertionError("passlib[bcrypt] not installed — run: pip install 'passlib[bcrypt]'")
