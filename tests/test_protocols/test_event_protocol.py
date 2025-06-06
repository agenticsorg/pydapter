"""
Tests for the event protocol in pydapter.protocols.event.
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import BaseModel
from pydapter.async_core import AsyncAdapter
from pydapter.protocols.event import Event, as_event
from pydapter.protocols.invokable import ExecutionStatus
from pydapter.protocols.types import Log


class SampleRequest(BaseModel):
    """Sample request model for testing."""

    value: int
    text: str


class TestAsEventDecorator:
    """Tests for the as_event decorator."""

    @pytest.mark.asyncio
    async def test_basic_decorator_functionality(self):
        """Test the basic functionality of the as_event decorator."""

        # Create a function with the decorator
        @as_event()
        async def sample_function(request_obj):
            return {"result": request_obj["value"] * 2}

        # Call the decorated function
        event = await sample_function({"value": 42})

        # Verify the event has the expected properties
        assert isinstance(event, Event)
        assert event.request == {"value": 42}
        assert event.execution.response == {"result": 84}
        assert event.execution.status == ExecutionStatus.COMPLETED
        assert event.execution.duration is not None
        assert event.execution.error is None
        assert event.event_type == "Event"  # Set by validator to class name

    @pytest.mark.asyncio
    async def test_decorator_with_pydantic_model(self):
        """Test the decorator with a Pydantic model as input."""

        # Create a function with the decorator
        @as_event()
        async def sample_function(request_obj):
            return {"result": request_obj.value * 2, "text": request_obj.text.upper()}

        # Create a sample request
        request = SampleRequest(value=42, text="hello")

        # Call the decorated function
        event = await sample_function(request)

        # Verify the event has the expected properties
        assert isinstance(event, Event)
        assert event.request == {"value": 42, "text": "hello"}
        assert event.execution.response == {"result": 84, "text": "HELLO"}

    @pytest.mark.asyncio
    async def test_decorator_with_request_arg(self):
        """Test the decorator with a specific request_arg parameter."""

        # Create a function with the decorator
        @as_event(request_arg="req")
        async def sample_function(other_arg, req):
            return {"result": req["value"] * 2, "other": other_arg}

        # Call the decorated function
        event = await sample_function("test", req={"value": 42})

        # Verify the event has the expected properties
        assert isinstance(event, Event)
        assert event.request == {"value": 42}
        assert event.execution.response == {"result": 84, "other": "test"}

    @pytest.mark.asyncio
    async def test_decorator_with_error(self):
        """Test the decorator when the wrapped function raises an error."""

        # Create a function with the decorator that raises an error
        @as_event()
        async def error_function(request_obj):
            raise ValueError("Test error")

        # Call the decorated function
        event = await error_function({"value": 42})

        # Verify the event has the expected error properties
        assert isinstance(event, Event)
        assert event.request == {"value": 42}
        assert event.execution.status == ExecutionStatus.FAILED
        assert event.execution.response is None
        assert "Test error" in event.execution.error
        assert event.execution.duration is not None

    @pytest.mark.asyncio
    async def test_decorator_with_embedding(self):
        """Test the as_event decorator with embedding functionality."""

        # Mock embedding function
        async def mock_embed_fn(content):
            # Simple mock that returns a fixed embedding
            return [0.1, 0.2, 0.3]

        # Create a function with the decorator
        @as_event(embed_content=True, embed_function=mock_embed_fn)
        async def sample_function(request_obj):
            return {"result": request_obj["value"] * 2}

        # Call the decorated function
        event = await sample_function({"value": 42})

        # Verify the event has the expected properties
        assert isinstance(event, Event)
        assert event.request == {"value": 42}
        assert event.execution.response == {"result": 84}
        assert event.embedding == [0.1, 0.2, 0.3]
        assert event.n_dim == 3

    @pytest.mark.asyncio
    async def test_decorator_with_sync_embedding_function(self):
        """Test the as_event decorator with a synchronous embedding function."""

        # Synchronous embedding function
        def sync_embed_fn(content):
            # Simple mock that returns a fixed embedding
            return [0.4, 0.5, 0.6]

        # Create a function with the decorator
        @as_event(embed_content=True, embed_function=sync_embed_fn)
        async def sample_function(request_obj):
            return {"result": request_obj["value"] * 2}

        # Call the decorated function
        event = await sample_function({"value": 42})

        # Verify the event has the expected properties
        assert isinstance(event, Event)
        assert event.request == {"value": 42}
        assert event.execution.response == {"result": 84}
        assert event.embedding == [0.4, 0.5, 0.6]
        assert event.n_dim == 3

    @pytest.mark.asyncio
    async def test_decorator_with_adapter_integration(self):
        """Test the as_event decorator with adapter integration."""
        # Create a mock adapter
        mock_adapter = MagicMock(spec=AsyncAdapter)
        mock_adapter.to_obj = AsyncMock()

        # Create a function with the decorator
        @as_event(adapt=True, adapter=mock_adapter, event_type="test_event")
        async def sample_function(request_obj):
            return {"result": request_obj["value"] * 2}

        # Call the decorated function
        event = await sample_function({"value": 42})

        # Verify the event has the expected properties
        assert isinstance(event, Event)
        assert event.request == {"value": 42}
        assert event.execution.response == {"result": 84}

        # Verify the adapter was called with the correct log
        mock_adapter.to_obj.assert_called_once()
        log_arg = mock_adapter.to_obj.call_args[0][0]
        assert isinstance(log_arg, Log)
        assert log_arg.event_type == "test_event"
        assert log_arg.content is not None

        # Verify the log content contains the expected data
        log_content = json.loads(log_arg.content)
        assert log_content["request"] == {"value": 42}
        assert log_content["response"] == {"result": 84}

    @pytest.mark.asyncio
    async def test_decorator_with_embedding_and_adapter(self):
        """Test the as_event decorator with both embedding and adapter integration."""

        # Mock embedding function
        async def mock_embed_fn(content):
            return [0.7, 0.8, 0.9]

        # Create a mock adapter
        mock_adapter = MagicMock(spec=AsyncAdapter)
        mock_adapter.to_obj = AsyncMock()

        # Create a function with the decorator
        @as_event(
            embed_content=True,
            embed_function=mock_embed_fn,
            adapt=True,
            adapter=mock_adapter,
            event_type="test_event_with_embedding",
        )
        async def sample_function(request_obj):
            return {"result": request_obj["value"] * 2}

        # Call the decorated function
        event = await sample_function({"value": 42})

        # Verify the event has the expected properties
        assert isinstance(event, Event)
        assert event.request == {"value": 42}
        assert event.execution.response == {"result": 84}
        assert event.embedding == [0.7, 0.8, 0.9]

        # Verify the adapter was called with the correct log
        mock_adapter.to_obj.assert_called_once()
        log_arg = mock_adapter.to_obj.call_args[0][0]
        assert isinstance(log_arg, Log)
        assert log_arg.event_type == "test_event_with_embedding"
        assert log_arg.embedding == [0.7, 0.8, 0.9]


class TestEventToLog:
    """Tests for the Event.to_log method."""

    def test_to_log_basic(self):
        """Test the basic functionality of the to_log method."""

        # Create a simple function
        def test_function(a, b):
            return a + b

        # Create an event
        event = Event(test_function, [1, 2], {})
        event.request = {"a": 1, "b": 2}
        event.execution.response = {"result": 3}

        # Call to_log
        log = event.to_log()

        # Verify the log has the expected properties
        assert isinstance(log, Log)
        assert log.id == str(event.id)
        assert log.created_at == event.created_at.isoformat()
        assert log.updated_at == event.updated_at.isoformat()
        assert log.event_type == "Event"  # Default is class name
        assert log.content is not None
        assert log.embedding == []  # No embedding by default
        assert log.duration == event.execution.duration
        assert log.status == event.execution.status.value
        assert log.error == event.execution.error
        assert log.sha256 is None  # No hash by default

    def test_to_log_with_event_type(self):
        """Test the to_log method with a custom event_type."""

        # Create a simple function
        def test_function(a, b):
            return a + b

        # Create an event
        event = Event(test_function, [1, 2], {})
        event.request = {"a": 1, "b": 2}
        event.execution.response = {"result": 3}

        # Call to_log with a custom event_type
        log = event.to_log(event_type="CustomEvent")

        # Verify the log has the expected event_type
        assert log.event_type == "CustomEvent"

    def test_to_log_with_hash_content(self):
        """Test the to_log method with hash_content=True."""

        # Create a simple function
        def test_function(a, b):
            return a + b

        # Create an event
        event = Event(test_function, [1, 2], {})
        event.request = {"a": 1, "b": 2}
        event.execution.response = {"result": 3}

        # Call to_log with hash_content=True
        log = event.to_log(hash_content=True)

        # Verify the log has a sha256 hash
        assert log.sha256 is not None
        assert isinstance(log.sha256, str)
        assert len(log.sha256) == 64  # SHA-256 hash is 64 hex characters

    def test_to_log_with_embedding(self):
        """Test the to_log method with an embedding."""

        # Create a simple function
        def test_function(a, b):
            return a + b

        # Create an event with an embedding
        event = Event(test_function, [1, 2], {})
        event.request = {"a": 1, "b": 2}
        event.execution.response = {"result": 3}
        event.embedding = [0.1, 0.2, 0.3]

        # Call to_log
        log = event.to_log()

        # Verify the log has the expected embedding
        assert log.embedding == [0.1, 0.2, 0.3]

    def test_to_log_with_error(self):
        """Test the to_log method when the event has an error."""

        # Create a simple function that raises an error
        def error_function():
            raise ValueError("Test error")

        # Create an event
        event = Event(error_function, [], {})
        event.request = {}
        event.execution.status = ExecutionStatus.FAILED
        event.execution.error = "ValueError: Test error"

        # Call to_log
        log = event.to_log()

        # Verify the log has the expected error properties
        assert log.status == "failed"
        assert log.error == "ValueError: Test error"
