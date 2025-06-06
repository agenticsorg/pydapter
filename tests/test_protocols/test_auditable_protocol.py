"""Tests for auditable protocol functionality."""

import pytest
from datetime import datetime
from pydantic import BaseModel

from pydapter.protocols.auditable import AuditableMixin


class TestAuditableProtocol:
    """Test auditable protocol functionality."""

    def test_auditable_mixin_basic(self):
        """Test basic auditable mixin functionality."""

        class AuditableModel(AuditableMixin, BaseModel):
            id: int
            name: str
            updated_by: str = ""
            version: int = 1

        model = AuditableModel(id=1, name="test")
        assert model.version == 1
        assert model.updated_by == ""

        # Mark as updated
        model.mark_updated_by("user123")
        assert model.updated_by == "user123"
        assert model.version == 2

    def test_auditable_with_timestamp(self):
        """Test auditable mixin with timestamp update."""

        class TimestampedAuditableModel(AuditableMixin, BaseModel):
            id: int
            name: str
            updated_by: str = ""
            version: int = 1
            updated_at: datetime | None = None

            def update_timestamp(self):
                """Update the timestamp."""
                self.updated_at = datetime.now()

        model = TimestampedAuditableModel(id=1, name="test")
        assert model.updated_at is None

        # Mark as updated - should call update_timestamp
        model.mark_updated_by("user456")
        assert model.updated_by == "user456"
        assert model.version == 2
        assert model.updated_at is not None
        assert isinstance(model.updated_at, datetime)

    def test_multiple_updates(self):
        """Test multiple updates increment version correctly."""

        class AuditableModel(AuditableMixin, BaseModel):
            id: int
            updated_by: str = ""
            version: int = 1

        model = AuditableModel(id=1)

        # Multiple updates
        model.mark_updated_by("user1")
        assert model.version == 2

        model.mark_updated_by("user2")
        assert model.version == 3
        assert model.updated_by == "user2"

        model.mark_updated_by("user3")
        assert model.version == 4
        assert model.updated_by == "user3"
