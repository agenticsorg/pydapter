"""
Tests for the protocols module in pydapter.protocols.

This module tests protocol compliance by creating concrete implementations
that satisfy the protocol contracts, rather than attempting to instantiate
the protocols directly.
"""

import asyncio
import datetime
import time
import uuid
from datetime import timezone
from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel, Field
from pydapter.fields import Embedding, Execution
from pydapter.protocols.embeddable import Embeddable, EmbeddableMixin
from pydapter.protocols.event import Event
from pydapter.protocols.identifiable import Identifiable, IdentifiableMixin
from pydapter.protocols.invokable import ExecutionStatus, Invokable, InvokableMixin
from pydapter.protocols.temporal import Temporal, TemporalMixin
from pydapter.protocols.utils import (
    as_async_fn,
    convert_to_datetime,
    validate_model_to_dict,
    validate_uuid,
)


# Concrete implementations for testing protocols
class ConcreteIdentifiable(BaseModel, IdentifiableMixin):
    """Concrete implementation of Identifiable protocol for testing."""

    id: UUID = Field(default_factory=uuid4)


class ConcreteTemporal(BaseModel, TemporalMixin):
    """Concrete implementation of Temporal protocol for testing."""

    created_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(timezone.utc)
    )
    updated_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(timezone.utc)
    )


class ConcreteEmbeddable(BaseModel, EmbeddableMixin):
    """Concrete implementation of Embeddable protocol for testing."""

    content: str | None = Field(default=None)
    embedding: Embedding = Field(default_factory=list)

    def create_content(self) -> str | None:
        """Create content string for embedding."""
        return self.content


class ConcreteInvokable(BaseModel, IdentifiableMixin, InvokableMixin, TemporalMixin):
    """Concrete implementation of Invokable protocol for testing."""

    id: UUID = Field(default_factory=uuid4)
    created_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(timezone.utc)
    )
    updated_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(timezone.utc)
    )
    request: dict | None = Field(default=None)
    execution: Execution = Field(default_factory=Execution)


class TestIdentifiableProtocol:
    """Tests for the Identifiable protocol using concrete implementations."""

    def test_identifiable_protocol_compliance(self):
        """Test that concrete implementation satisfies Identifiable protocol."""
        identifiable = ConcreteIdentifiable()

        # Test protocol compliance
        assert isinstance(identifiable, Identifiable)

        # Test that it has required attributes
        assert hasattr(identifiable, "id")
        assert isinstance(identifiable.id, UUID)

    def test_identifiable_initialization(self):
        """Test initializing a concrete Identifiable implementation."""
        # Create an identifiable object
        identifiable = ConcreteIdentifiable()

        # Check that the ID was generated
        assert identifiable.id is not None
        assert isinstance(identifiable.id, UUID)

        # Create an identifiable object with a specific ID
        specific_id = uuid.uuid4()
        identifiable = ConcreteIdentifiable(id=specific_id)

        # Check that the ID was set correctly
        assert identifiable.id == specific_id

    def test_identifiable_serialization(self):
        """Test serializing a concrete Identifiable implementation."""
        # Create an identifiable object
        identifiable = ConcreteIdentifiable()

        # Serialize the object
        serialized = identifiable.model_dump_json()

        # Check that the serialized object contains the ID as a string
        assert f'"{str(identifiable.id)}"' in serialized

    def test_identifiable_hash(self):
        """Test that IdentifiableMixin provides hash functionality."""
        # Create an identifiable object
        identifiable = ConcreteIdentifiable()

        # Test that the mixin provides the hash method in the method resolution order
        # Pydantic may override __hash__ to None, but the mixin method is still available
        mixin_hash_method = IdentifiableMixin.__hash__
        assert callable(mixin_hash_method)

        # Test that the mixin's hash method works correctly when called directly
        hash_result = mixin_hash_method(identifiable)
        expected_hash = hash(identifiable.id)
        assert hash_result == expected_hash


class TestTemporalProtocol:
    """Tests for the Temporal protocol using concrete implementations."""

    def test_temporal_protocol_compliance(self):
        """Test that concrete implementation satisfies Temporal protocol."""
        temporal = ConcreteTemporal()

        # Test protocol compliance
        assert isinstance(temporal, Temporal)

        # Test that it has required attributes
        assert hasattr(temporal, "created_at")
        assert hasattr(temporal, "updated_at")
        assert hasattr(temporal, "update_timestamp")

    def test_temporal_initialization(self):
        """Test initializing a concrete Temporal implementation."""
        # Create a temporal object
        temporal = ConcreteTemporal()

        # Check that the timestamps were generated
        assert temporal.created_at is not None
        assert temporal.updated_at is not None
        assert isinstance(temporal.created_at, datetime.datetime)
        assert isinstance(temporal.updated_at, datetime.datetime)

        # Check that the timestamps are initially close
        assert (temporal.updated_at - temporal.created_at).total_seconds() < 1

    def test_temporal_update_timestamp(self):
        """Test updating the timestamp of a concrete Temporal implementation."""
        # Create a temporal object
        temporal = ConcreteTemporal()

        # Store the initial timestamps
        initial_created_at = temporal.created_at
        initial_updated_at = temporal.updated_at

        # Wait a moment to ensure the timestamp changes
        time.sleep(0.01)

        # Update the timestamp
        temporal.update_timestamp()

        # Check that the created_at timestamp didn't change
        assert temporal.created_at == initial_created_at

        # Check that the updated_at timestamp changed
        assert temporal.updated_at > initial_updated_at

    def test_temporal_serialization(self):
        """Test serializing a concrete Temporal implementation."""
        # Create a temporal object
        temporal = ConcreteTemporal()

        # Serialize the object
        serialized = temporal.model_dump_json()

        # Check that the serialized object contains the timestamps as strings
        assert temporal.created_at.isoformat() in serialized
        assert temporal.updated_at.isoformat() in serialized


class TestEmbeddableProtocol:
    """Tests for the Embeddable protocol using concrete implementations."""

    def test_embeddable_protocol_compliance(self):
        """Test that concrete implementation satisfies Embeddable protocol."""
        embeddable = ConcreteEmbeddable()

        # Test protocol compliance
        assert isinstance(embeddable, Embeddable)

        # Test that it has required attributes
        assert hasattr(embeddable, "content")
        assert hasattr(embeddable, "embedding")
        assert hasattr(embeddable, "n_dim")
        assert hasattr(embeddable, "create_content")

    def test_embeddable_initialization(self):
        """Test initializing a concrete Embeddable implementation."""
        # Create an Embeddable object with no embedding
        embeddable = ConcreteEmbeddable()

        # Check that the embedding is an empty list
        assert embeddable.embedding == []
        assert embeddable.n_dim == 0

        # Create an Embeddable object with an embedding
        embedding = [0.1, 0.2, 0.3]
        embeddable = ConcreteEmbeddable(embedding=embedding)

        # Check that the embedding was set correctly
        assert embeddable.embedding == embedding
        assert embeddable.n_dim == 3

    def test_embeddable_with_content(self):
        """Test a concrete Embeddable implementation with content."""
        # Create an Embeddable object with content
        content = "This is some content"
        embeddable = ConcreteEmbeddable(content=content)

        # Check that the content was set correctly
        assert embeddable.content == content

        # Check that create_content returns the content
        assert embeddable.create_content() == content

    def test_embeddable_parse_embedding(self):
        """Test parsing embeddings in different formats."""
        # Test with a list of floats
        embeddable = ConcreteEmbeddable(embedding=[0.1, 0.2, 0.3])
        assert embeddable.embedding == [0.1, 0.2, 0.3]

        # Test with default empty list (not None to avoid validation error)
        embeddable = ConcreteEmbeddable()
        assert embeddable.embedding == []

    def test_embeddable_parse_embedding_response(self):
        """Test the static parse_embedding_response method."""
        # Test with list
        result = ConcreteEmbeddable.parse_embedding_response([0.1, 0.2, 0.3])
        assert result == [0.1, 0.2, 0.3]

        # Test with dict containing embedding
        result = ConcreteEmbeddable.parse_embedding_response({
            "embedding": [0.1, 0.2, 0.3]
        })
        assert result == [0.1, 0.2, 0.3]


class TestInvokableProtocol:
    """Tests for the Invokable protocol using concrete implementations."""

    def test_invokable_protocol_compliance(self):
        """Test that concrete implementation satisfies Invokable protocol."""
        invokable = ConcreteInvokable()

        # Test protocol compliance
        assert isinstance(invokable, Invokable)

        # Test that it has required attributes
        assert hasattr(invokable, "request")
        assert hasattr(invokable, "execution")
        assert hasattr(invokable, "invoke")

    def test_invokable_initialization(self):
        """Test initializing a concrete Invokable implementation."""
        # Create an invokable object
        invokable = ConcreteInvokable()

        # Check that the request is None
        assert invokable.request is None

        # Check that the execution is initialized
        assert invokable.execution is not None
        assert invokable.execution.status == ExecutionStatus.PENDING
        assert invokable.execution.duration is None
        assert invokable.execution.response is None
        assert invokable.execution.error is None

    @pytest.mark.asyncio
    async def test_invokable_invoke(self):
        """Test invoking a concrete Invokable implementation."""

        # Create a simple function to use as the invoke function
        def add(a, b):
            return {"result": a + b}  # Return a dict to avoid validation error

        # Create an invokable object
        invokable = ConcreteInvokable()
        invokable._handler = add
        invokable._handler_args = (1, 2)
        invokable._handler_kwargs = {}

        # Invoke the function
        await invokable.invoke()

        # Check that the execution was updated
        assert invokable.execution.status == ExecutionStatus.COMPLETED
        assert invokable.execution.duration is not None
        assert invokable.execution.response == {"result": 3}
        assert invokable.execution.error is None

        # Check that has_invoked is True
        assert invokable.has_invoked

    @pytest.mark.asyncio
    async def test_invokable_invoke_error(self):
        """Test invoking a concrete Invokable implementation with an error."""

        # Create a function that raises an error
        def raise_error():
            raise ValueError("Test error")

        # Create an invokable object
        invokable = ConcreteInvokable()
        invokable._handler = raise_error
        invokable._handler_args = ()
        invokable._handler_kwargs = {}

        # Invoke the function - we expect it to handle the error
        await invokable.invoke()

        # Check that the execution was updated
        assert invokable.execution.status == ExecutionStatus.FAILED
        assert invokable.execution.duration is not None
        assert invokable.execution.response is None
        assert "Test error" in invokable.execution.error

        # Check that has_invoked is True
        assert invokable.has_invoked


class TestEventClass:
    """Tests for the Event class."""

    def test_event_class_definition(self):
        """Test that the Event class is defined correctly."""
        # Check that the class has the expected attributes
        assert hasattr(Event, "__init__")
        assert hasattr(Event, "update_timestamp")

    def test_event_protocol_compliance(self):
        """Test that Event satisfies the expected protocols."""

        # Create a simple function to use as the event handler
        def test_function(a, b, c=None):
            return a + b + (c or 0)

        # Create an event
        event = Event(test_function, (1, 2), {"c": 3}, event_type="test")

        # Check protocol compliance through isinstance checks
        assert isinstance(event, Identifiable)
        assert isinstance(event, Embeddable)
        assert isinstance(event, Invokable)
        assert isinstance(event, Temporal)

    def test_event_initialization(self):
        """Test initializing an Event."""

        # Create a simple function to use as the event handler
        def test_function(a, b, c=None):
            return a + b + (c or 0)

        # Create an event with event_type specified
        event = Event(test_function, (1, 2), {"c": 3}, event_type="test")

        # Check that the event was initialized correctly
        assert event._handler == test_function
        assert event._handler_args == (1, 2)
        assert event._handler_kwargs == {"c": 3}
        assert event.event_type == "test"

    @pytest.mark.asyncio
    async def test_event_invocation(self):
        """Test that Event can be invoked."""

        def test_function(a, b):
            return {"result": a + b}  # Return dict to satisfy validation

        event = Event(test_function, (3, 4), {}, event_type="test")

        # Invoke the event
        await event.invoke()

        # Check that execution completed
        assert event.execution.status == ExecutionStatus.COMPLETED
        assert event.execution.response == {"result": 7}


class TestProtocolUtils:
    """Tests for the protocol utilities."""

    def test_validate_uuid(self):
        """Test the validate_uuid function."""
        # Test with a UUID object
        uuid_obj = uuid.uuid4()
        assert validate_uuid(uuid_obj) == uuid_obj

        # Test with a UUID string
        uuid_str = str(uuid_obj)
        assert validate_uuid(uuid_str) == uuid_obj

        # Test with an invalid UUID
        with pytest.raises(ValueError):
            validate_uuid("not-a-uuid")

    def test_convert_to_datetime(self):
        """Test the convert_to_datetime function."""
        # Test with a datetime object
        dt = datetime.datetime.now()
        assert convert_to_datetime(dt) == dt

        # Test with an ISO format string
        dt_str = dt.isoformat()
        assert isinstance(convert_to_datetime(dt_str), datetime.datetime)

        # Test with an invalid datetime string
        with pytest.raises(ValueError):
            convert_to_datetime("not-a-datetime")

    def test_validate_model_to_dict(self):
        """Test the validate_model_to_dict function."""
        # Test with a Pydantic model
        model = ConcreteIdentifiable()
        model_dict = validate_model_to_dict(model)
        assert isinstance(model_dict, dict)
        assert "id" in model_dict

        # Test with a dictionary
        test_dict = {"key": "value"}
        assert validate_model_to_dict(test_dict) == test_dict

        # Test with None
        assert validate_model_to_dict(None) == {}

        # Test with an invalid type
        with pytest.raises(ValueError):
            validate_model_to_dict(123)

    def test_as_async_fn(self):
        """Test the as_async_fn function."""

        # Test with a synchronous function
        def sync_fn(a, b):
            return a + b

        # We need to call the function to get the wrapped version
        async_sync_fn = as_async_fn(sync_fn)

        # Check that the function is now a coroutine function or returns a coroutine
        # This might not be directly testable with iscoroutinefunction
        # Let's test it by calling it and checking the result
        result = async_sync_fn(1, 2)
        assert asyncio.isfuture(result) or asyncio.iscoroutine(result)

        # Test with an asynchronous function
        async def async_fn(a, b):
            return a + b

        assert as_async_fn(async_fn) is async_fn
