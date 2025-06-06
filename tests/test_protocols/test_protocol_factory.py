"""Test the protocol factory functions."""

import datetime

import pytest
from pydantic import BaseModel
from pydapter.fields import FieldTemplate
from pydapter.protocols import (
    CRYPTOGRAPHICAL,
    EMBEDDABLE,
    IDENTIFIABLE,
    INVOKABLE,
    TEMPORAL,
    Event,
    combine_with_mixins,
    create_protocol_model_class,
)


def test_create_protocol_model_class_basic():
    """Test creating a model with basic protocols."""
    # Create model with fields and behaviors
    User = create_protocol_model_class(
        "User",
        IDENTIFIABLE,
        TEMPORAL,
        username=FieldTemplate(base_type=str),
        email=FieldTemplate(base_type=str),
    )

    # Create instance
    user = User(username="john_doe", email="john@example.com")

    # Check fields exist
    assert hasattr(user, "id")
    assert hasattr(user, "created_at")
    assert hasattr(user, "updated_at")
    assert user.username == "john_doe"
    assert user.email == "john@example.com"

    # Check behavioral methods exist and work
    assert hasattr(user, "update_timestamp")
    original_updated = user.updated_at
    user.update_timestamp()
    assert user.updated_at > original_updated


def test_create_protocol_model_class_multiple_protocols():
    """Test creating a model with multiple protocols."""
    Document = create_protocol_model_class(
        "Document",
        IDENTIFIABLE,
        TEMPORAL,
        CRYPTOGRAPHICAL,
        EMBEDDABLE,
        title=FieldTemplate(base_type=str),
        content=FieldTemplate(base_type=str),
    )

    # Create instance
    doc = Document(
        title="Test Document",
        content="Important content",
    )

    # Check all fields
    assert hasattr(doc, "id")
    assert hasattr(doc, "created_at")
    assert hasattr(doc, "updated_at")
    assert hasattr(doc, "sha256")
    assert hasattr(doc, "embedding")

    # Check all methods
    assert hasattr(doc, "update_timestamp")
    assert hasattr(doc, "hash_content")
    assert hasattr(doc, "parse_embedding_response")

    # Test methods work
    doc.hash_content()
    assert doc.sha256 is not None
    assert len(doc.sha256) == 64


def test_create_protocol_model_class_with_custom_base():
    """Test creating a model with custom base class."""

    class CustomBase(BaseModel):
        class Config:
            arbitrary_types_allowed = True

        def custom_method(self):
            return "custom"

    Model = create_protocol_model_class(
        "Model",
        IDENTIFIABLE,
        base_model=CustomBase,
        display_name=FieldTemplate(base_type=str),
    )

    instance = Model(display_name="test")
    assert hasattr(instance, "id")
    assert hasattr(instance, "custom_method")
    assert instance.custom_method() == "custom"


def test_create_protocol_model_class_with_field_validator():
    """Test creating a model with field validators."""

    def custom_validator(cls, v):
        return v.upper()

    Model = create_protocol_model_class(
        "Model",
        IDENTIFIABLE,
        display_name=FieldTemplate(base_type=str, validator=custom_validator),
    )

    instance = Model(display_name="john")
    assert instance.display_name == "JOHN"  # Validator works correctly


def test_combine_with_mixins():
    """Test adding mixins to existing model."""
    from pydapter.fields import create_protocol_model

    # Create structure only
    UserStructure = create_protocol_model(
        "UserStructure",
        IDENTIFIABLE,
        TEMPORAL,
        username=FieldTemplate(base_type=str),
    )

    # Add behaviors
    User = combine_with_mixins(UserStructure, IDENTIFIABLE, TEMPORAL)

    # Create instance
    user = User(username="test")

    # Has fields
    assert hasattr(user, "id")
    assert hasattr(user, "created_at")
    assert hasattr(user, "updated_at")

    # Has methods
    assert hasattr(user, "update_timestamp")
    user.update_timestamp()
    assert isinstance(user.updated_at, datetime.datetime)


def test_combine_with_mixins_custom_name():
    """Test combine_with_mixins with custom class name."""
    from pydapter.fields import create_protocol_model

    BaseModel = create_protocol_model(
        "BaseModel",
        IDENTIFIABLE,
        display_name=FieldTemplate(base_type=str),
    )

    # Add mixins with custom name
    Entity = combine_with_mixins(BaseModel, IDENTIFIABLE, name="Entity")

    assert Entity.__name__ == "Entity"
    entity = Entity(display_name="test")
    assert hasattr(entity, "id")


def test_protocol_constants_work_as_strings():
    """Test that protocol constants work the same as strings."""
    # Using constants
    Model1 = create_protocol_model_class(
        "Model1",
        IDENTIFIABLE,
        TEMPORAL,
        display_name=FieldTemplate(base_type=str),
    )

    # Using strings
    Model2 = create_protocol_model_class(
        "Model2",
        "identifiable",
        "temporal",
        display_name=FieldTemplate(base_type=str),
    )

    # Both should have same fields and methods
    m1 = Model1(display_name="test1")
    m2 = Model2(display_name="test2")

    for attr in ["id", "created_at", "updated_at", "update_timestamp"]:
        assert hasattr(m1, attr)
        assert hasattr(m2, attr)


def test_invokable_protocol():
    """Test model with invokable protocol."""
    Task = create_protocol_model_class(
        "Task",
        IDENTIFIABLE,
        INVOKABLE,
        task_name=FieldTemplate(base_type=str),
    )

    task = Task(task_name="process_data")

    # Check fields
    assert hasattr(task, "id")
    assert hasattr(task, "execution")

    # Check methods from InvokableMixin
    assert hasattr(task, "invoke")


def test_event_class_usage():
    """Test using Event class directly."""

    class CustomEvent(Event):
        user_id: str
        action: str

    # Event requires handler args
    event = CustomEvent(
        handler=lambda: "result",
        handler_arg=(),
        handler_kwargs={},
        user_id="user123",
        action="login",
        event_type="user.login",
    )

    # Has all Event fields
    assert hasattr(event, "id")
    assert hasattr(event, "created_at")
    assert hasattr(event, "updated_at")
    assert hasattr(event, "event_type")
    assert hasattr(event, "content")
    assert hasattr(event, "request")
    assert hasattr(event, "embedding")
    assert hasattr(event, "sha256")
    assert hasattr(event, "execution")

    # Has custom fields
    assert event.user_id == "user123"
    assert event.action == "login"

    # Has all mixin methods
    assert hasattr(event, "update_timestamp")
    assert hasattr(event, "hash_content")
    assert hasattr(event, "invoke")


def test_error_on_unknown_protocol():
    """Test error handling for unknown protocols."""
    from pydapter.fields import create_protocol_model

    with pytest.raises(ValueError, match="Unknown protocol"):
        create_protocol_model("Model", "unknown_protocol")

    # Should not raise for valid protocols
    create_protocol_model("Model", IDENTIFIABLE)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
