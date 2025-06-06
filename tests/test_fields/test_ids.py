"""Tests for ID field functionality."""

import pytest
from uuid import UUID, uuid4

from pydapter.fields.ids import (
    ID_FROZEN,
    ID_MUTABLE,
    ID_NULLABLE,
    validate_uuid,
    serialize_uuid,
    uuid_validator,
    nullable_uuid_validator,
)
from pydapter.exceptions import ValidationError


class TestUuidValidation:
    """Test UUID validation functions."""

    def test_validate_uuid_with_uuid_object(self):
        """Test validation with UUID object."""
        test_uuid = uuid4()
        result = validate_uuid(test_uuid)
        assert result == test_uuid
        assert isinstance(result, UUID)

    def test_validate_uuid_with_string(self):
        """Test validation with UUID string."""
        test_uuid = uuid4()
        uuid_str = str(test_uuid)
        result = validate_uuid(uuid_str)
        assert result == test_uuid
        assert isinstance(result, UUID)

    def test_validate_uuid_with_invalid_string(self):
        """Test validation with invalid UUID string."""
        with pytest.raises(ValidationError, match="id must be a valid UUID"):
            validate_uuid("not-a-uuid")

        with pytest.raises(ValidationError, match="id must be a valid UUID"):
            validate_uuid("12345")

    def test_validate_uuid_nullable_true(self):
        """Test validation with nullable=True."""
        assert validate_uuid(None, nullable=True) is None
        assert validate_uuid("", nullable=True) is None
        assert validate_uuid(0, nullable=True) is None

    def test_validate_uuid_nullable_false(self):
        """Test validation with nullable=False."""
        with pytest.raises(ValidationError, match="id must be a valid UUID"):
            validate_uuid(None, nullable=False)

        with pytest.raises(ValidationError, match="id must be a valid UUID"):
            validate_uuid("", nullable=False)

    def test_serialize_uuid(self):
        """Test UUID serialization."""
        test_uuid = uuid4()
        result = serialize_uuid(test_uuid)
        assert result == str(test_uuid)
        assert isinstance(result, str)

    def test_uuid_validator(self):
        """Test uuid_validator wrapper."""
        test_uuid = uuid4()
        result = uuid_validator(None, test_uuid)
        assert result == test_uuid

        # Test with string
        result = uuid_validator(None, str(test_uuid))
        assert result == test_uuid

    def test_nullable_uuid_validator(self):
        """Test nullable_uuid_validator wrapper."""
        # Test with None
        result = nullable_uuid_validator(None, None)
        assert result is None

        # Test with valid UUID
        test_uuid = uuid4()
        result = nullable_uuid_validator(None, test_uuid)
        assert result == test_uuid


class TestIdFields:
    """Test ID field definitions."""

    def test_id_frozen_field(self):
        """Test ID_FROZEN field configuration."""
        assert ID_FROZEN.name == "id"
        assert ID_FROZEN.annotation == UUID
        assert ID_FROZEN.frozen is True
        assert ID_FROZEN.immutable is True
        assert ID_FROZEN.title == "ID"
        assert ID_FROZEN.description == "Frozen Unique identifier"
        assert ID_FROZEN.default_factory == uuid4
        assert ID_FROZEN.validator is not None

    def test_id_mutable_field(self):
        """Test ID_MUTABLE field configuration."""
        assert ID_MUTABLE.name == "id"
        assert ID_MUTABLE.annotation == UUID
        assert ID_MUTABLE.frozen is not True  # Not explicitly frozen
        assert ID_MUTABLE.immutable is True
        assert ID_MUTABLE.title == "ID"
        assert ID_MUTABLE.default_factory == uuid4
        assert ID_MUTABLE.validator is not None

    def test_id_nullable_field(self):
        """Test ID_NULLABLE field configuration."""
        assert ID_NULLABLE.name == "nullable_id"
        # Check that annotation handles Union[UUID, None]
        assert ID_NULLABLE.default is None
        assert ID_NULLABLE.immutable is True
        assert ID_NULLABLE.validator is not None

    def test_field_validators(self):
        """Test that field validators work correctly."""
        # Test ID_MUTABLE validator
        test_uuid = uuid4()
        result = ID_MUTABLE.validator(None, str(test_uuid))
        assert result == test_uuid

        # Test ID_NULLABLE validator with None
        result = ID_NULLABLE.validator(None, None)
        assert result is None

        # Test ID_NULLABLE validator with UUID
        result = ID_NULLABLE.validator(None, test_uuid)
        assert result == test_uuid
