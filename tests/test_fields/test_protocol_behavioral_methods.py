"""Test that protocol models can be combined with behavioral mixins."""

import datetime

import pytest
from pydantic import BaseModel
from pydapter.fields import FieldTemplate, create_protocol_model
from pydapter.protocols import (
    CryptographicalMixin,
    EmbeddableMixin,
    IdentifiableMixin,
    TemporalMixin,
)


def test_structural_compliance_only():
    """Test that create_protocol_model only provides fields, not methods."""
    # Create model with protocol fields
    User = create_protocol_model(
        "User",
        "identifiable",
        "temporal",
        username=FieldTemplate(base_type=str),
    )

    # Create instance
    user = User(username="test_user")

    # Fields should exist
    assert hasattr(user, "id")
    assert hasattr(user, "created_at")
    assert hasattr(user, "updated_at")
    assert user.username == "test_user"

    # Behavioral methods should NOT exist
    assert not hasattr(user, "update_timestamp")


def test_structural_and_behavioral_compliance():
    """Test combining create_protocol_model with mixin inheritance."""
    # Step 1: Create structural model
    _UserStructure = create_protocol_model(
        "UserStructure",
        "identifiable",
        "temporal",
        username=FieldTemplate(base_type=str),
        email=FieldTemplate(base_type=str),
    )

    # Step 2: Add behavioral mixins
    class User(_UserStructure, IdentifiableMixin, TemporalMixin, BaseModel):
        """User model with both fields and methods."""

        pass

    # Create instance
    user = User(username="john_doe", email="john@example.com")

    # Fields should exist
    assert hasattr(user, "id")
    assert hasattr(user, "created_at")
    assert hasattr(user, "updated_at")
    assert user.username == "john_doe"
    assert user.email == "john@example.com"

    # Behavioral methods should NOW exist
    assert hasattr(user, "update_timestamp")

    # Test the method works
    original_updated = user.updated_at
    user.update_timestamp()
    assert user.updated_at > original_updated


def test_multiple_protocol_behaviors():
    """Test combining multiple protocol behaviors."""
    # Create structure with multiple protocols
    _DocStructure = create_protocol_model(
        "DocStructure",
        "identifiable",
        "temporal",
        "cryptographical",
        "embeddable",
        content=FieldTemplate(base_type=str),
        title=FieldTemplate(base_type=str),
    )

    # Add all behavioral mixins
    class Document(
        _DocStructure,
        IdentifiableMixin,
        TemporalMixin,
        CryptographicalMixin,
        EmbeddableMixin,
        BaseModel,
    ):
        """Document with all behaviors."""

        pass

    # Create instance
    doc = Document(
        content="Important document content",
        title="Test Document",
    )

    # Test all fields exist
    assert hasattr(doc, "id")
    assert hasattr(doc, "created_at")
    assert hasattr(doc, "updated_at")
    assert hasattr(doc, "sha256")
    assert hasattr(doc, "embedding")

    # Test all methods exist
    assert hasattr(doc, "update_timestamp")
    assert hasattr(doc, "hash_content")
    assert hasattr(doc, "parse_embedding_response")

    # Test methods work
    doc.hash_content()
    assert doc.sha256 is not None
    assert len(doc.sha256) == 64  # SHA256 hex string


def test_event_like_model_with_all_protocols():
    """Test creating an event-like model with all necessary protocols."""
    # Create a model with all the protocols that Event uses
    EventLike = create_protocol_model(
        "EventLike",
        "identifiable",
        "temporal",
        "embeddable",
        "invokable",
        "cryptographical",
        event_type=FieldTemplate(base_type=str),
        content=FieldTemplate(base_type=dict, default_factory=dict),
        request=FieldTemplate(base_type=dict, default_factory=dict),
        user_action=FieldTemplate(base_type=str),
    )

    # Create instance
    event = EventLike(
        event_type="user.login",
        user_action="login",
        content={"ip": "192.168.1.1"},
    )

    # All protocol fields should exist
    assert hasattr(event, "id")
    assert hasattr(event, "created_at")
    assert hasattr(event, "updated_at")
    assert hasattr(event, "embedding")
    assert hasattr(event, "sha256")
    assert hasattr(event, "execution")

    # Custom fields
    assert event.event_type == "user.login"
    assert event.user_action == "login"
    assert event.content == {"ip": "192.168.1.1"}


def test_protocol_model_inheritance_order():
    """Test that mixin order doesn't affect functionality."""
    # Create base structure
    _BaseStructure = create_protocol_model(
        "BaseStructure",
        "identifiable",
        "temporal",
        display_name=FieldTemplate(base_type=str),
    )

    # Test different mixin orders
    class Model1(IdentifiableMixin, TemporalMixin, _BaseStructure, BaseModel):
        pass

    class Model2(_BaseStructure, IdentifiableMixin, TemporalMixin, BaseModel):
        pass

    class Model3(TemporalMixin, _BaseStructure, IdentifiableMixin, BaseModel):
        pass

    # All should work the same
    for ModelClass in [Model1, Model2, Model3]:
        instance = ModelClass(display_name="test")
        assert hasattr(instance, "id")
        assert hasattr(instance, "update_timestamp")
        instance.update_timestamp()
        assert isinstance(instance.updated_at, datetime.datetime)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
