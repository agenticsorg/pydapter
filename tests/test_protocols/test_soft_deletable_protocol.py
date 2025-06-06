"""Tests for soft deletable protocol functionality."""

import pytest
from datetime import datetime, timezone
from pydantic import BaseModel

from pydapter.protocols.soft_deletable import SoftDeletableMixin


class TestSoftDeletableProtocol:
    """Test soft deletable protocol functionality."""

    def test_soft_delete_basic(self):
        """Test basic soft delete functionality."""

        class SoftDeletableModel(SoftDeletableMixin, BaseModel):
            id: int
            name: str
            deleted_at: datetime | None = None
            is_deleted: bool = False

        model = SoftDeletableModel(id=1, name="test")
        assert model.is_deleted is False
        assert model.deleted_at is None

        # Soft delete
        model.soft_delete()
        assert model.is_deleted is True
        assert model.deleted_at is not None
        assert isinstance(model.deleted_at, datetime)
        assert model.deleted_at.tzinfo == timezone.utc

    def test_restore_functionality(self):
        """Test restore functionality."""

        class SoftDeletableModel(SoftDeletableMixin, BaseModel):
            id: int
            name: str
            deleted_at: datetime | None = None
            is_deleted: bool = False

        model = SoftDeletableModel(id=1, name="test")

        # Soft delete then restore
        model.soft_delete()
        assert model.is_deleted is True
        assert model.deleted_at is not None

        model.restore()
        assert model.is_deleted is False
        assert model.deleted_at is None

    def test_multiple_deletes_and_restores(self):
        """Test multiple delete and restore operations."""

        class SoftDeletableModel(SoftDeletableMixin, BaseModel):
            id: int
            deleted_at: datetime | None = None
            is_deleted: bool = False

        model = SoftDeletableModel(id=1)

        # First delete
        model.soft_delete()
        first_delete_time = model.deleted_at
        assert model.is_deleted is True

        # Restore
        model.restore()
        assert model.is_deleted is False
        assert model.deleted_at is None

        # Delete again
        model.soft_delete()
        second_delete_time = model.deleted_at
        assert model.is_deleted is True
        assert second_delete_time != first_delete_time

    def test_soft_delete_preserves_data(self):
        """Test that soft delete preserves all other data."""

        class ComplexModel(SoftDeletableMixin, BaseModel):
            id: int
            name: str
            value: float
            tags: list[str]
            deleted_at: datetime | None = None
            is_deleted: bool = False

        model = ComplexModel(id=1, name="complex", value=42.5, tags=["a", "b", "c"])

        # Soft delete should not affect other fields
        model.soft_delete()
        assert model.id == 1
        assert model.name == "complex"
        assert model.value == 42.5
        assert model.tags == ["a", "b", "c"]
        assert model.is_deleted is True
