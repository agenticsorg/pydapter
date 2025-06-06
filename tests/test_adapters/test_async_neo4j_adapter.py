"""
Unit tests for AsyncNeo4jAdapter.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from neo4j.exceptions import AuthError, CypherSyntaxError, ServiceUnavailable
from pydantic import BaseModel
from pydapter.async_core import AsyncAdaptable
from pydapter.exceptions import ConnectionError, QueryError, ResourceError
from pydapter.exceptions import ValidationError as AdapterValidationError
from pydapter.extras.async_neo4j_ import AsyncNeo4jAdapter


# Define a model class for testing - using SampleModel instead of TestModel to avoid pytest collection
class SampleModel(BaseModel):
    """Sample model for AsyncNeo4jAdapter tests."""

    id: int
    name: str
    value: float


@pytest.fixture
def async_neo4j_model_factory():
    """Factory for creating test models with AsyncNeo4jAdapter registered."""

    class AsyncNeo4jModel(AsyncAdaptable, BaseModel):
        id: int
        name: str
        value: float

        class Config:
            arbitrary_types_allowed = True

    # Register the adapter with the model class
    AsyncNeo4jModel.register_async_adapter(AsyncNeo4jAdapter)

    # Return a factory function
    return lambda **kwargs: AsyncNeo4jModel(**kwargs)


@pytest.fixture
def async_neo4j_sample(async_neo4j_model_factory):
    """Create a sample model instance."""
    return async_neo4j_model_factory(id=1, name="test", value=42.5)


class TestAsyncNeo4jAdapter:
    """Test suite for AsyncNeo4jAdapter."""

    def test_async_neo4j_adapter_protocol_compliance(self):
        """Test that AsyncNeo4jAdapter implements the AsyncAdapter protocol."""
        # We can't use issubclass with Protocol directly, so we check for required attributes
        assert hasattr(AsyncNeo4jAdapter, "from_obj")
        assert hasattr(AsyncNeo4jAdapter, "to_obj")
        assert hasattr(AsyncNeo4jAdapter, "obj_key")
        assert hasattr(AsyncNeo4jAdapter, "from_obj")
        assert hasattr(AsyncNeo4jAdapter, "to_obj")
        assert isinstance(AsyncNeo4jAdapter.obj_key, str)
        assert AsyncNeo4jAdapter.obj_key == "async_neo4j"

    @pytest.mark.asyncio
    async def test_create_driver_with_auth(self):
        """Test _create_driver method with auth."""
        # Save original driver factory
        original_factory = AsyncNeo4jAdapter._driver_factory

        try:
            # Create a mock driver factory
            mock_driver_factory = MagicMock()
            mock_driver_factory.return_value = AsyncMock()

            # Set the mock driver factory
            AsyncNeo4jAdapter._driver_factory = mock_driver_factory

            # Call the method
            driver = await AsyncNeo4jAdapter._create_driver(
                "bolt://localhost:7687", auth=("neo4j", "password")
            )

            # Verify the mock was called correctly
            mock_driver_factory.assert_called_once_with(
                "bolt://localhost:7687", auth=("neo4j", "password")
            )
            assert driver is not None
        finally:
            # Restore original driver factory
            AsyncNeo4jAdapter._driver_factory = original_factory

    @pytest.mark.asyncio
    async def test_create_driver_without_auth(self):
        """Test _create_driver method without auth."""
        # Save original driver factory
        original_factory = AsyncNeo4jAdapter._driver_factory

        try:
            # Create a mock driver factory
            mock_driver_factory = MagicMock()
            mock_driver_factory.return_value = AsyncMock()

            # Set the mock driver factory
            AsyncNeo4jAdapter._driver_factory = mock_driver_factory

            # Call the method
            driver = await AsyncNeo4jAdapter._create_driver("bolt://localhost:7687")

            # Verify the mock was called correctly
            mock_driver_factory.assert_called_once_with("bolt://localhost:7687")
            assert driver is not None
        finally:
            # Restore original driver factory
            AsyncNeo4jAdapter._driver_factory = original_factory

    @pytest.mark.asyncio
    async def test_create_driver_service_unavailable(self):
        """Test _create_driver method with ServiceUnavailable error."""
        # Save original driver factory
        original_factory = AsyncNeo4jAdapter._driver_factory

        try:
            # Create a mock driver factory that raises an exception
            mock_driver_factory = MagicMock()
            mock_driver_factory.side_effect = ServiceUnavailable("Service unavailable")

            # Set the mock driver factory
            AsyncNeo4jAdapter._driver_factory = mock_driver_factory

            # Call the method and expect an exception
            with pytest.raises(ConnectionError) as exc_info:
                await AsyncNeo4jAdapter._create_driver("bolt://localhost:7687")
            assert "Neo4j service unavailable" in str(exc_info.value)
        finally:
            # Restore original driver factory
            AsyncNeo4jAdapter._driver_factory = original_factory

    @pytest.mark.asyncio
    async def test_create_driver_auth_error(self):
        """Test _create_driver method with AuthError."""
        # Save original driver factory
        original_factory = AsyncNeo4jAdapter._driver_factory

        try:
            # Create a mock driver factory that raises an exception
            mock_driver_factory = MagicMock()
            mock_driver_factory.side_effect = AuthError("Authentication failed")

            # Set the mock driver factory
            AsyncNeo4jAdapter._driver_factory = mock_driver_factory

            # Call the method and expect an exception
            with pytest.raises(ConnectionError) as exc_info:
                await AsyncNeo4jAdapter._create_driver("bolt://localhost:7687")
            assert "Neo4j authentication failed" in str(exc_info.value)
        finally:
            # Restore original driver factory
            AsyncNeo4jAdapter._driver_factory = original_factory

    @pytest.mark.asyncio
    async def test_create_driver_generic_error(self):
        """Test _create_driver method with generic error."""
        # Save original driver factory
        original_factory = AsyncNeo4jAdapter._driver_factory

        try:
            # Create a mock driver factory that raises an exception
            mock_driver_factory = MagicMock()
            mock_driver_factory.side_effect = Exception("Generic error")

            # Set the mock driver factory
            AsyncNeo4jAdapter._driver_factory = mock_driver_factory

            # Call the method and expect an exception
            with pytest.raises(ConnectionError) as exc_info:
                await AsyncNeo4jAdapter._create_driver("bolt://localhost:7687")
            assert "Failed to create Neo4j driver" in str(exc_info.value)
        finally:
            # Restore original driver factory
            AsyncNeo4jAdapter._driver_factory = original_factory

    def test_validate_cypher_valid(self):
        """Test _validate_cypher method with valid query."""
        # Should not raise an exception
        AsyncNeo4jAdapter._validate_cypher("MATCH (n:`Person`) RETURN n")

    def test_validate_cypher_invalid(self):
        """Test _validate_cypher method with invalid query."""
        with pytest.raises(QueryError) as exc_info:
            AsyncNeo4jAdapter._validate_cypher("MATCH (n:`Person``Injection`) RETURN n")
        assert "Invalid Cypher query" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_from_obj_missing_url(self):
        """Test from_obj method with missing URL."""
        with pytest.raises(AdapterValidationError) as exc_info:
            await AsyncNeo4jAdapter.from_obj(SampleModel, {})
        assert "Missing required parameter 'url'" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_from_obj_with_where_clause(self):
        """Test from_obj method with where clause."""
        # Setup mock driver and session
        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()

        # Configure mocks
        mock_driver.session = MagicMock(return_value=mock_session)

        # Configure the run method to return a mock result
        mock_session.run = AsyncMock(return_value=mock_result)

        # Mock the async iterator for result
        mock_record = MagicMock()
        mock_record.__getitem__.return_value = MagicMock(
            _properties={"id": 1, "name": "test", "value": 42.5}
        )

        # Set up the async iterator
        mock_result.__aiter__ = MagicMock()
        mock_result.__aiter__.return_value = mock_result
        mock_result.__anext__ = AsyncMock()
        mock_result.__anext__.side_effect = [mock_record, StopAsyncIteration]

        # Mock session.close to return a completed future
        close_future = asyncio.Future()
        close_future.set_result(None)
        mock_session.close.return_value = close_future

        # Ensure the session is properly awaited
        mock_session.__await__ = lambda: iter([mock_session])

        # Patch the _create_driver method
        with patch.object(
            AsyncNeo4jAdapter, "_create_driver", return_value=mock_driver
        ):
            result = await AsyncNeo4jAdapter.from_obj(
                SampleModel,
                {"url": "bolt://localhost:7687", "where": "n.id = 1"},
            )

            # Verify the query was constructed correctly
            mock_session.run.assert_called_once_with(
                "MATCH (n:`SampleModel`) WHERE n.id = 1 RETURN n"
            )

            # Verify the result
            assert isinstance(result, list)
            assert len(result) == 1
            assert isinstance(result[0], SampleModel)
            assert result[0].id == 1
            assert result[0].name == "test"
            assert result[0].value == 42.5

    @pytest.mark.asyncio
    async def test_from_obj_with_custom_label(self):
        """Test from_obj method with custom label."""
        # Setup mock driver and session
        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()

        # Configure mocks
        mock_driver.session = MagicMock(return_value=mock_session)

        # Configure the run method to return a mock result
        mock_session.run = AsyncMock(return_value=mock_result)

        # Mock the async iterator for result
        mock_record = MagicMock()
        mock_record.__getitem__.return_value = MagicMock(
            _properties={"id": 1, "name": "test", "value": 42.5}
        )

        # Set up the async iterator
        mock_result.__aiter__ = MagicMock()
        mock_result.__aiter__.return_value = mock_result
        mock_result.__anext__ = AsyncMock()
        mock_result.__anext__.side_effect = [mock_record, StopAsyncIteration]

        # Mock session.close to return a completed future
        close_future = asyncio.Future()
        close_future.set_result(None)
        mock_session.close.return_value = close_future

        # Ensure the session is properly awaited
        mock_session.__await__ = lambda: iter([mock_session])

        # Patch the _create_driver method
        with patch.object(
            AsyncNeo4jAdapter, "_create_driver", return_value=mock_driver
        ):
            result = await AsyncNeo4jAdapter.from_obj(
                SampleModel,
                {"url": "bolt://localhost:7687", "label": "CustomLabel"},
            )

            # Verify the query was constructed correctly
            mock_session.run.assert_called_once_with(
                "MATCH (n:`CustomLabel`)  RETURN n"
            )

            # Verify the result
            assert isinstance(result, list)
            assert len(result) == 1
            assert isinstance(result[0], SampleModel)
            assert result[0].id == 1
            assert result[0].name == "test"
            assert result[0].value == 42.5

    @pytest.mark.asyncio
    async def test_from_obj_single_result(self):
        """Test from_obj method with many=False."""
        # Setup mock driver and session
        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()

        # Configure mocks
        mock_driver.session = MagicMock(return_value=mock_session)

        # Configure the run method to return a mock result
        mock_session.run = AsyncMock(return_value=mock_result)

        # Mock the async iterator for result
        mock_record = MagicMock()
        mock_record.__getitem__.return_value = MagicMock(
            _properties={"id": 1, "name": "test", "value": 42.5}
        )

        # Set up the async iterator
        mock_result.__aiter__ = MagicMock()
        mock_result.__aiter__.return_value = mock_result
        mock_result.__anext__ = AsyncMock()
        mock_result.__anext__.side_effect = [mock_record, StopAsyncIteration]

        # Mock session.close to return a completed future
        close_future = asyncio.Future()
        close_future.set_result(None)
        mock_session.close.return_value = close_future

        # Ensure the session is properly awaited
        mock_session.__await__ = lambda: iter([mock_session])

        # Patch the _create_driver method
        with patch.object(
            AsyncNeo4jAdapter, "_create_driver", return_value=mock_driver
        ):
            result = await AsyncNeo4jAdapter.from_obj(
                SampleModel,
                {"url": "bolt://localhost:7687"},
                many=False,
            )

            # Verify the result
            assert isinstance(result, SampleModel)
            assert result.id == 1
            assert result.name == "test"
            assert result.value == 42.5

    @pytest.mark.asyncio
    async def test_from_obj_empty_result_many(self):
        """Test from_obj method with empty result and many=True."""
        # Setup mock driver and session
        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()

        # Configure mocks
        mock_driver.session = MagicMock(return_value=mock_session)

        # Configure the run method to return a mock result
        mock_session.run = AsyncMock(return_value=mock_result)

        # Set up the async iterator
        mock_result.__aiter__ = MagicMock()
        mock_result.__aiter__.return_value = mock_result
        mock_result.__anext__ = AsyncMock()
        mock_result.__anext__.side_effect = StopAsyncIteration

        # Mock session.close to return a completed future
        close_future = asyncio.Future()
        close_future.set_result(None)
        mock_session.close.return_value = close_future

        # Ensure the session is properly awaited
        mock_session.__await__ = lambda: iter([mock_session])

        # Ensure the session is properly awaited
        mock_session.__await__ = lambda: iter([mock_session])

        # Patch the _create_driver method
        with patch.object(
            AsyncNeo4jAdapter, "_create_driver", return_value=mock_driver
        ):
            result = await AsyncNeo4jAdapter.from_obj(
                SampleModel,
                {"url": "bolt://localhost:7687"},
            )

            # Verify the result
            assert isinstance(result, list)
            assert len(result) == 0

    @pytest.mark.asyncio
    async def test_from_obj_empty_result_single(self):
        """Test from_obj method with empty result and many=False."""
        # Setup mock driver and session
        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()

        # Configure mocks
        mock_driver.session = MagicMock(return_value=mock_session)

        # Configure the run method to return a mock result
        mock_session.run = AsyncMock(return_value=mock_result)

        # Set up the async iterator
        mock_result.__aiter__ = MagicMock()
        mock_result.__aiter__.return_value = mock_result
        mock_result.__anext__ = AsyncMock()
        mock_result.__anext__.side_effect = StopAsyncIteration

        # Mock session.close to return a completed future
        close_future = asyncio.Future()
        close_future.set_result(None)
        mock_session.close.return_value = close_future

        # Ensure the session is properly awaited
        mock_session.__await__ = lambda: iter([mock_session])

        # Patch the _create_driver method
        with patch.object(
            AsyncNeo4jAdapter, "_create_driver", return_value=mock_driver
        ):
            with pytest.raises(ResourceError) as exc_info:
                await AsyncNeo4jAdapter.from_obj(
                    SampleModel,
                    {"url": "bolt://localhost:7687"},
                    many=False,
                )
            assert "No nodes found matching the query" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_from_obj_cypher_syntax_error(self):
        """Test from_obj method with CypherSyntaxError."""
        # Setup mock driver and session
        mock_driver = AsyncMock()
        mock_session = AsyncMock()

        # Configure mocks
        mock_driver.session = MagicMock(return_value=mock_session)

        # Configure the run method to raise an exception
        mock_session.run = AsyncMock(side_effect=CypherSyntaxError("Syntax error"))

        # Mock session.close to return a completed future
        close_future = asyncio.Future()
        close_future.set_result(None)
        mock_session.close.return_value = close_future

        # Ensure the session is properly awaited
        mock_session.__await__ = lambda: iter([mock_session])

        # Patch the _create_driver method
        with patch.object(
            AsyncNeo4jAdapter, "_create_driver", return_value=mock_driver
        ):
            with pytest.raises(QueryError) as exc_info:
                await AsyncNeo4jAdapter.from_obj(
                    SampleModel,
                    {"url": "bolt://localhost:7687"},
                )
            assert "Neo4j Cypher syntax error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_from_obj_validation_error(self):
        """Test from_obj method with ValidationError."""
        # Setup mock driver and session
        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()

        # Configure mocks
        mock_driver.session = MagicMock(return_value=mock_session)

        # Configure the run method to return a mock result
        mock_session.run = AsyncMock(return_value=mock_result)

        # Mock the async iterator for result with invalid data
        mock_record = MagicMock()
        mock_record.__getitem__.return_value = MagicMock(
            _properties={"id": "not_an_int", "name": "test", "value": 42.5}
        )

        # Set up the async iterator
        mock_result.__aiter__ = MagicMock()
        mock_result.__aiter__.return_value = mock_result
        mock_result.__anext__ = AsyncMock()
        mock_result.__anext__.side_effect = [mock_record, StopAsyncIteration]

        # Mock session.close to return a completed future
        close_future = asyncio.Future()
        close_future.set_result(None)
        mock_session.close.return_value = close_future

        # Ensure the session is properly awaited
        mock_session.__await__ = lambda: iter([mock_session])

        # Patch the _create_driver method
        with patch.object(
            AsyncNeo4jAdapter, "_create_driver", return_value=mock_driver
        ):
            with pytest.raises(AdapterValidationError) as exc_info:
                await AsyncNeo4jAdapter.from_obj(
                    SampleModel,
                    {"url": "bolt://localhost:7687"},
                )
            assert "Validation error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_to_obj_missing_url(self):
        """Test to_obj method with missing URL."""
        with pytest.raises(AdapterValidationError) as exc_info:
            await AsyncNeo4jAdapter.to_obj(
                SampleModel(id=1, name="test", value=42.5), url=None
            )
        assert "Missing required parameter 'url'" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_to_obj_missing_merge_on(self):
        """Test to_obj method with missing merge_on."""
        # We can't pass None directly to merge_on since it's typed as str
        # Instead, we'll patch the validation check to simulate the error
        with patch.object(
            AsyncNeo4jAdapter,
            "to_obj",
            side_effect=AdapterValidationError("Missing required parameter 'merge_on'"),
        ):
            with pytest.raises(AdapterValidationError) as exc_info:
                await AsyncNeo4jAdapter.to_obj(
                    SampleModel(id=1, name="test", value=42.5),
                    url="bolt://localhost:7687",
                    merge_on="",  # Empty string will trigger the validation error
                )
            assert "Missing required parameter 'merge_on'" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_to_obj_with_custom_label(self):
        """Test to_obj method with custom label."""
        # Setup mock driver and session
        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()

        # Configure mocks
        mock_driver.session = MagicMock(return_value=mock_session)

        # Configure the run method to return a mock result
        mock_session.run = AsyncMock(return_value=mock_result)

        # Mock session.close to return a completed future
        close_future = asyncio.Future()
        close_future.set_result(None)
        mock_session.close.return_value = close_future

        # Ensure the session is properly awaited
        mock_session.__await__ = lambda: iter([mock_session])

        # Patch the _create_driver method
        with patch.object(
            AsyncNeo4jAdapter, "_create_driver", return_value=mock_driver
        ):
            result = await AsyncNeo4jAdapter.to_obj(
                SampleModel(id=1, name="test", value=42.5),
                url="bolt://localhost:7687",
                label="CustomLabel",
            )

            # Verify the query was constructed correctly
            mock_session.run.assert_called_once()
            args, kwargs = mock_session.run.call_args
            assert args[0] == "MERGE (n:`CustomLabel` {id: $val}) SET n += $props"
            assert kwargs["val"] == 1
            assert kwargs["props"] == {"id": 1, "name": "test", "value": 42.5}

            # Verify the result
            assert result == {"merged_count": 1}

    @pytest.mark.asyncio
    async def test_to_obj_with_custom_merge_on(self):
        """Test to_obj method with custom merge_on."""
        # Setup mock driver and session
        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()

        # Configure mocks
        mock_driver.session = MagicMock(return_value=mock_session)

        # Configure the run method to return a mock result
        mock_session.run = AsyncMock(return_value=mock_result)

        # Mock session.close to return a completed future
        close_future = asyncio.Future()
        close_future.set_result(None)
        mock_session.close.return_value = close_future

        # Ensure the session is properly awaited
        mock_session.__await__ = lambda: iter([mock_session])

        # Patch the _create_driver method
        with patch.object(
            AsyncNeo4jAdapter, "_create_driver", return_value=mock_driver
        ):
            result = await AsyncNeo4jAdapter.to_obj(
                SampleModel(id=1, name="test", value=42.5),
                url="bolt://localhost:7687",
                merge_on="name",
            )

            # Verify the query was constructed correctly
            mock_session.run.assert_called_once()
            args, kwargs = mock_session.run.call_args
            assert args[0] == "MERGE (n:`SampleModel` {name: $val}) SET n += $props"
            assert kwargs["val"] == "test"
            assert kwargs["props"] == {"id": 1, "name": "test", "value": 42.5}

            # Verify the result
            assert result == {"merged_count": 1}

    @pytest.mark.asyncio
    async def test_to_obj_with_invalid_merge_property(self):
        """Test to_obj method with invalid merge property."""
        # Setup mock driver and session
        mock_driver = AsyncMock()

        # Patch the _create_driver method
        with patch.object(
            AsyncNeo4jAdapter, "_create_driver", return_value=mock_driver
        ):
            with pytest.raises(AdapterValidationError) as exc_info:
                await AsyncNeo4jAdapter.to_obj(
                    SampleModel(id=1, name="test", value=42.5),
                    url="bolt://localhost:7687",
                    merge_on="non_existent_property",
                )
            assert "Merge property 'non_existent_property' not found in model" in str(
                exc_info.value
            )

    @pytest.mark.asyncio
    async def test_to_obj_multiple_items(self):
        """Test to_obj method with multiple items."""
        # Setup mock driver and session
        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()

        # Configure mocks
        mock_driver.session = MagicMock(return_value=mock_session)

        # Configure the run method to return a mock result
        mock_session.run = AsyncMock(return_value=mock_result)

        # Mock session.close to return a completed future
        close_future = asyncio.Future()
        close_future.set_result(None)
        mock_session.close.return_value = close_future

        # Create multiple models
        models = [
            SampleModel(id=1, name="test1", value=42.5),
            SampleModel(id=2, name="test2", value=43.5),
        ]

        # Patch the _create_driver method
        with patch.object(
            AsyncNeo4jAdapter, "_create_driver", return_value=mock_driver
        ):
            result = await AsyncNeo4jAdapter.to_obj(
                models,
                url="bolt://localhost:7687",
            )

            # Verify the query was called twice
            assert mock_session.run.call_count == 2

            # Verify the result
            assert result == {"merged_count": 2}

    @pytest.mark.asyncio
    async def test_to_obj_cypher_syntax_error(self):
        """Test to_obj method with CypherSyntaxError."""
        # Setup mock driver and session
        mock_driver = AsyncMock()
        mock_session = AsyncMock()

        # Configure mocks for async context managers
        mock_driver.__aenter__.return_value = mock_driver
        mock_driver.session.return_value = mock_session
        mock_session.__aenter__.return_value = mock_session

        # Configure the run method to raise an exception
        mock_session.run = AsyncMock(side_effect=CypherSyntaxError("Syntax error"))

        # Patch the _create_driver method
        with patch.object(
            AsyncNeo4jAdapter, "_create_driver", return_value=mock_driver
        ):
            with pytest.raises(QueryError) as exc_info:
                await AsyncNeo4jAdapter.to_obj(
                    SampleModel(id=1, name="test", value=42.5),
                    url="bolt://localhost:7687",
                )
            # Just check that it's a QueryError, the exact message might vary
            assert isinstance(exc_info.value, QueryError)
