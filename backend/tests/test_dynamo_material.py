"""Tests for material CRUD functions in dynamo_service.py."""
import os
from unittest.mock import MagicMock, patch, call

import pytest

# Set env vars before importing the module
os.environ.setdefault("MATERIALS_TABLE", "sylli-materials-table")


class TestStoreMaterial:
    def test_store_material_calls_put_item(self):
        """store_material should call table.put_item with the provided item."""
        mock_table = MagicMock()
        with patch("services.dynamo_service.dynamodb") as mock_dynamo:
            mock_dynamo.Table.return_value = mock_table
            from services.dynamo_service import store_material
            item = {
                "material_id": "abc-123",
                "user_id": "user-1",
                "filename": "lecture1.pdf",
                "s3_key": "materials/abc-123/lecture1.pdf",
                "file_type": "pdf",
                "week_number": 2,
                "week_confirmed": False,
                "embed_status": "pending",
                "uploaded_at": "2026-03-15T00:00:00+00:00",
            }
            store_material(item)

            mock_dynamo.Table.assert_called_once_with("sylli-materials-table")
            mock_table.put_item.assert_called_once_with(Item=item)

    def test_store_material_uses_materials_table_name_constant(self):
        """store_material should use MATERIALS_TABLE_NAME constant (from env var)."""
        from services.dynamo_service import MATERIALS_TABLE_NAME
        # By default the constant should be the default table name
        assert MATERIALS_TABLE_NAME in ("sylli-materials-table", os.environ.get("MATERIALS_TABLE", "sylli-materials-table"))


class TestGetMaterial:
    def test_get_material_returns_item_for_owner(self):
        """get_material returns the item when user_id matches."""
        mock_table = MagicMock()
        mock_item = {"material_id": "abc-123", "user_id": "user-1", "filename": "file.pdf"}
        mock_table.get_item.return_value = {"Item": mock_item}
        with patch("services.dynamo_service.dynamodb") as mock_dynamo:
            mock_dynamo.Table.return_value = mock_table
            from services.dynamo_service import get_material
            result = get_material("abc-123", "user-1")
            assert result == mock_item

    def test_get_material_returns_none_for_nonexistent(self):
        """get_material returns None when item is not found."""
        mock_table = MagicMock()
        mock_table.get_item.return_value = {}
        with patch("services.dynamo_service.dynamodb") as mock_dynamo:
            mock_dynamo.Table.return_value = mock_table
            from services.dynamo_service import get_material
            result = get_material("missing-id", "user-1")
            assert result is None

    def test_get_material_returns_none_on_ownership_mismatch(self):
        """get_material returns None (anti-enumeration) when user_id does not match."""
        mock_table = MagicMock()
        mock_item = {"material_id": "abc-123", "user_id": "other-user", "filename": "file.pdf"}
        mock_table.get_item.return_value = {"Item": mock_item}
        with patch("services.dynamo_service.dynamodb") as mock_dynamo:
            mock_dynamo.Table.return_value = mock_table
            from services.dynamo_service import get_material
            result = get_material("abc-123", "user-1")
            assert result is None

    def test_get_material_queries_correct_key(self):
        """get_material should query using material_id as the partition key."""
        mock_table = MagicMock()
        mock_table.get_item.return_value = {}
        with patch("services.dynamo_service.dynamodb") as mock_dynamo:
            mock_dynamo.Table.return_value = mock_table
            from services.dynamo_service import get_material
            get_material("my-id", "user-1")
            mock_table.get_item.assert_called_once_with(Key={"material_id": "my-id"})


class TestUpdateMaterialWeek:
    def test_update_material_week_calls_update_item(self):
        """update_material_week should call update_item with correct expression."""
        mock_table = MagicMock()
        with patch("services.dynamo_service.dynamodb") as mock_dynamo:
            mock_dynamo.Table.return_value = mock_table
            from services.dynamo_service import update_material_week
            update_material_week("abc-123", 3, week_confirmed=True)

            mock_table.update_item.assert_called_once_with(
                Key={"material_id": "abc-123"},
                UpdateExpression="SET week_number = :w, week_confirmed = :c",
                ExpressionAttributeValues={":w": 3, ":c": True},
            )

    def test_update_material_week_default_confirmed_true(self):
        """update_material_week should default week_confirmed to True."""
        mock_table = MagicMock()
        with patch("services.dynamo_service.dynamodb") as mock_dynamo:
            mock_dynamo.Table.return_value = mock_table
            from services.dynamo_service import update_material_week
            update_material_week("abc-123", 5)
            call_kwargs = mock_table.update_item.call_args[1]
            assert call_kwargs["ExpressionAttributeValues"][":c"] is True


class TestUpdateMaterialEmbedStatus:
    def test_update_material_embed_status_calls_update_item(self):
        """update_material_embed_status should update embed_status attribute."""
        mock_table = MagicMock()
        with patch("services.dynamo_service.dynamodb") as mock_dynamo:
            mock_dynamo.Table.return_value = mock_table
            from services.dynamo_service import update_material_embed_status
            update_material_embed_status("abc-123", "processing")

            mock_table.update_item.assert_called_once_with(
                Key={"material_id": "abc-123"},
                UpdateExpression="SET embed_status = :s",
                ExpressionAttributeValues={":s": "processing"},
            )

    def test_update_material_embed_status_accepts_all_states(self):
        """update_material_embed_status should accept pending, processing, ready, error."""
        mock_table = MagicMock()
        with patch("services.dynamo_service.dynamodb") as mock_dynamo:
            mock_dynamo.Table.return_value = mock_table
            from services.dynamo_service import update_material_embed_status
            for status in ("pending", "processing", "ready", "error"):
                mock_table.reset_mock()
                update_material_embed_status("id-1", status)
                call_kwargs = mock_table.update_item.call_args[1]
                assert call_kwargs["ExpressionAttributeValues"][":s"] == status


class TestListMaterialsForUser:
    def test_list_materials_queries_gsi(self):
        """list_materials_for_user should query user_id-index GSI."""
        mock_table = MagicMock()
        mock_items = [
            {"material_id": "a", "user_id": "user-1", "uploaded_at": "2026-01-01"},
            {"material_id": "b", "user_id": "user-1", "uploaded_at": "2026-01-02"},
        ]
        mock_table.query.return_value = {"Items": mock_items}
        with patch("services.dynamo_service.dynamodb") as mock_dynamo:
            mock_dynamo.Table.return_value = mock_table
            from services.dynamo_service import list_materials_for_user
            result = list_materials_for_user("user-1")

            mock_table.query.assert_called_once_with(
                IndexName="user_id-index",
                KeyConditionExpression="user_id = :uid",
                ExpressionAttributeValues={":uid": "user-1"},
                ScanIndexForward=True,
            )
            assert result == mock_items

    def test_list_materials_returns_empty_list_when_no_items(self):
        """list_materials_for_user should return empty list when no items found."""
        mock_table = MagicMock()
        mock_table.query.return_value = {}
        with patch("services.dynamo_service.dynamodb") as mock_dynamo:
            mock_dynamo.Table.return_value = mock_table
            from services.dynamo_service import list_materials_for_user
            result = list_materials_for_user("user-with-no-materials")
            assert result == []
