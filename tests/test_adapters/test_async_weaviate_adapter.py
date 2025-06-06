"""
Unit tests for AsyncWeaviateAdapter.
"""

import importlib.util

import pytest
from aiohttp import ClientError
from pydantic import BaseModel
from pydapter.async_core import AsyncAdaptable
from pydapter.exceptions import ConnectionError, QueryError, ResourceError
from pydapter.exceptions import ValidationError as AdapterValidationError
from pydapter.extras.async_weaviate_ import AsyncWeaviateAdapter


# Define helper function directly in the test file
def is_weaviate_available():
    """
    Check if weaviate is properly installed and can be imported.

    Returns:
        bool: True if weaviate is available, False otherwise.
    """
    try:
        # Use importlib.util to check if the module is available without importing it
        if importlib.util.find_spec("weaviate") is None:
            return False
        return True
    except (ImportError, AttributeError):
        return False


# Create a pytest marker to skip tests if weaviate is not available
weaviate_skip_marker = pytest.mark.skipif(
    not is_weaviate_available(),
    reason="Weaviate module not available or not properly installed",
)


class TestModel(AsyncAdaptable, BaseModel):
    """Test model for AsyncWeaviateAdapter tests."""

    id: int
    name: str
    value: float
    embedding: list[float] = [0.1, 0.2, 0.3, 0.4, 0.5]


@weaviate_skip_marker
class TestAsyncWeaviateAdapterProtocol:
    """Test AsyncWeaviateAdapter protocol compliance."""

    def test_async_weaviate_adapter_protocol_compliance(self):
        """Test that AsyncWeaviateAdapter follows the AsyncAdapter protocol."""
        # Check class attributes
        assert hasattr(AsyncWeaviateAdapter, "obj_key")
        assert AsyncWeaviateAdapter.obj_key == "async_weav"

        # Check required methods
        assert hasattr(AsyncWeaviateAdapter, "to_obj")
        assert hasattr(AsyncWeaviateAdapter, "from_obj")

        # Check method signatures
        to_obj_params = AsyncWeaviateAdapter.to_obj.__code__.co_varnames
        assert "subj" in to_obj_params
        assert "class_name" in to_obj_params
        assert "vector_field" in to_obj_params
        assert "url" in to_obj_params

        from_obj_params = AsyncWeaviateAdapter.from_obj.__code__.co_varnames
        assert "subj_cls" in from_obj_params
        assert "obj" in from_obj_params
        assert "many" in from_obj_params


@weaviate_skip_marker
class TestAsyncWeaviateAdapterFunctionality:
    """Test AsyncWeaviateAdapter functionality."""

    @pytest.mark.asyncio
    async def test_async_weaviate_to_obj(self, mocker):
        """Test conversion from model to Weaviate object."""
        # Create test instance
        test_model = TestModel(id=1, name="test", value=42.5)

        # Register adapter
        test_model.__class__.register_async_adapter(AsyncWeaviateAdapter)

        # Mock the to_obj method to return a successful result
        mocker.patch.object(
            AsyncWeaviateAdapter, "to_obj", return_value={"added_count": 1}
        )

        # Test to_obj
        result = await test_model.adapt_to_async(
            obj_key="async_weav", class_name="TestModel", url="http://localhost:8080"
        )

        # Verify the method was called with correct parameters
        AsyncWeaviateAdapter.to_obj.assert_called_once()
        call_args = AsyncWeaviateAdapter.to_obj.call_args
        assert call_args[0][0] == test_model
        assert call_args[1]["class_name"] == "TestModel"
        assert call_args[1]["url"] == "http://localhost:8080"

        # Verify result
        assert isinstance(result, dict)
        assert result["added_count"] == 1

    @pytest.mark.asyncio
    async def test_async_weaviate_from_obj(self, mocker):
        """Test conversion from Weaviate object to model."""
        # Create test class
        test_cls = TestModel

        # Register adapter
        test_cls.register_async_adapter(AsyncWeaviateAdapter)

        # Create expected result
        expected_result = TestModel(id=1, name="test", value=42.5)

        # Mock the from_obj method to return the expected result
        mocker.patch.object(
            AsyncWeaviateAdapter, "from_obj", return_value=expected_result
        )

        # Test from_obj
        result = await test_cls.adapt_from_async(
            {
                "class_name": "TestModel",
                "query_vector": [0.1, 0.2, 0.3, 0.4, 0.5],
                "url": "http://localhost:8080",
                "top_k": 1,
            },
            obj_key="async_weav",
            many=False,
        )

        # Verify the method was called with correct parameters
        AsyncWeaviateAdapter.from_obj.assert_called_once()
        call_args = AsyncWeaviateAdapter.from_obj.call_args
        assert call_args[0][0] == test_cls
        assert call_args[0][1]["class_name"] == "TestModel"
        assert call_args[0][1]["query_vector"] == [0.1, 0.2, 0.3, 0.4, 0.5]
        assert call_args[0][1]["url"] == "http://localhost:8080"
        assert call_args[0][1]["top_k"] == 1
        assert not call_args[1]["many"]

        # Verify result
        assert isinstance(result, TestModel)
        assert result.id == 1
        assert result.name == "test"
        assert result.value == 42.5

    @pytest.mark.asyncio
    async def test_async_weaviate_from_obj_many(self, mocker):
        """Test conversion from multiple Weaviate objects to models."""
        # Create test class
        test_cls = TestModel

        # Register adapter
        test_cls.register_async_adapter(AsyncWeaviateAdapter)

        # Create expected results
        expected_results = [
            TestModel(id=1, name="test1", value=42.5),
            TestModel(id=2, name="test2", value=43.5),
        ]

        # Mock the from_obj method to return the expected results
        mocker.patch.object(
            AsyncWeaviateAdapter, "from_obj", return_value=expected_results
        )

        # Test from_obj with many=True
        results = await test_cls.adapt_from_async(
            {
                "class_name": "TestModel",
                "query_vector": [0.1, 0.2, 0.3, 0.4, 0.5],
                "url": "http://localhost:8080",
                "top_k": 5,
            },
            obj_key="async_weav",
            many=True,
        )

        # Verify the method was called with correct parameters
        AsyncWeaviateAdapter.from_obj.assert_called_once()
        call_args = AsyncWeaviateAdapter.from_obj.call_args
        assert call_args[0][0] == test_cls
        assert call_args[0][1]["class_name"] == "TestModel"
        assert call_args[0][1]["query_vector"] == [0.1, 0.2, 0.3, 0.4, 0.5]
        assert call_args[0][1]["url"] == "http://localhost:8080"
        assert call_args[0][1]["top_k"] == 5
        assert call_args[1]["many"]

        # Verify results
        assert isinstance(results, list)
        assert len(results) == 2
        assert all(isinstance(r, TestModel) for r in results)
        assert results[0].id == 1
        assert results[0].name == "test1"
        assert results[1].id == 2
        assert results[1].name == "test2"


@weaviate_skip_marker
class TestAsyncWeaviateAdapterErrorHandling:
    """Test AsyncWeaviateAdapter error handling."""

    @pytest.mark.asyncio
    async def test_missing_class_name_parameter(self):
        """Test handling of missing class_name parameter."""
        # Create test instance
        test_model = TestModel(id=1, name="test", value=42.5)

        # Register adapter
        test_model.__class__.register_async_adapter(AsyncWeaviateAdapter)

        # Test to_obj with missing class_name
        with pytest.raises(AdapterValidationError) as excinfo:
            await test_model.adapt_to_async(
                obj_key="async_weav",
                url="http://localhost:8080",
                class_name="",  # Empty class_name
            )

        assert "Missing required parameter 'class_name'" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_missing_url_parameter(self):
        """Test handling of missing url parameter."""
        # Create test instance
        test_model = TestModel(id=1, name="test", value=42.5)

        # Register adapter
        test_model.__class__.register_async_adapter(AsyncWeaviateAdapter)

        # Test to_obj with missing url
        with pytest.raises(AdapterValidationError) as excinfo:
            await test_model.adapt_to_async(
                obj_key="async_weav",
                class_name="TestModel",
                url="",  # Empty URL
            )

        assert "Missing required parameter 'url'" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_connection_error(self, mocker):
        """Test handling of connection errors."""
        # Create test instance
        test_model = TestModel(id=1, name="test", value=42.5)

        # Register adapter
        test_model.__class__.register_async_adapter(AsyncWeaviateAdapter)

        # Mock the to_obj method to raise ConnectionError
        mocker.patch.object(
            AsyncWeaviateAdapter,
            "to_obj",
            side_effect=ConnectionError(
                "Failed to connect to Weaviate: Connection failed", adapter="async_weav"
            ),
        )

        # Test to_obj with connection error
        with pytest.raises(ConnectionError) as excinfo:
            await test_model.adapt_to_async(
                obj_key="async_weav", class_name="TestModel", url="http://invalid-url"
            )

        assert "Failed to connect to Weaviate" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_query_error(self, mocker):
        """Test handling of query errors."""
        # Create test class
        test_cls = TestModel

        # Register adapter
        test_cls.register_async_adapter(AsyncWeaviateAdapter)

        # Mock the from_obj method to raise QueryError
        mocker.patch.object(
            AsyncWeaviateAdapter,
            "from_obj",
            side_effect=QueryError(
                "Error in Weaviate query: Bad request", adapter="async_weav"
            ),
        )

        # Test from_obj with query error
        with pytest.raises(QueryError) as excinfo:
            await test_cls.adapt_from_async(
                {
                    "class_name": "TestModel",
                    "query_vector": [0.1, 0.2, 0.3, 0.4, 0.5],
                    "url": "http://localhost:8080",
                },
                obj_key="async_weav",
            )

        assert "Error in Weaviate query" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_resource_not_found(self, mocker):
        """Test handling of resource not found errors."""
        # Create test class
        test_cls = TestModel

        # Register adapter
        test_cls.register_async_adapter(AsyncWeaviateAdapter)

        # Mock the from_obj method to raise ResourceError
        mocker.patch.object(
            AsyncWeaviateAdapter,
            "from_obj",
            side_effect=ResourceError(
                "No objects found matching the query", resource="TestModel"
            ),
        )

        # Test from_obj with empty result and many=False
        with pytest.raises(ResourceError) as excinfo:
            await test_cls.adapt_from_async(
                {
                    "class_name": "TestModel",
                    "query_vector": [0.1, 0.2, 0.3, 0.4, 0.5],
                    "url": "http://localhost:8080",
                },
                obj_key="async_weav",
                many=False,
            )

        assert "No objects found matching the query" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_validation_error(self, mocker):
        """Test handling of validation errors."""
        # Create test class
        test_cls = TestModel

        # Register adapter
        test_cls.register_async_adapter(AsyncWeaviateAdapter)

        # Mock the from_obj method to raise AdapterValidationError
        mocker.patch.object(
            AsyncWeaviateAdapter,
            "from_obj",
            side_effect=AdapterValidationError(
                "Validation error: missing required field 'name'"
            ),
        )

        # Test from_obj with validation error
        with pytest.raises(AdapterValidationError) as excinfo:
            await test_cls.adapt_from_async(
                {
                    "class_name": "TestModel",
                    "query_vector": [0.1, 0.2, 0.3, 0.4, 0.5],
                    "url": "http://localhost:8080",
                },
                obj_key="async_weav",
                many=False,
            )

        assert "Validation error" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_missing_vector_field(self, mocker):
        """Test handling of missing vector field."""

        # Create test instance without embedding field
        class TestModelNoVector(AsyncAdaptable, BaseModel):
            id: int
            name: str
            value: float

        test_model = TestModelNoVector(id=1, name="test", value=42.5)

        # Register adapter
        test_model.__class__.register_async_adapter(AsyncWeaviateAdapter)

        # Mock the to_obj method to raise AdapterValidationError
        mocker.patch.object(
            AsyncWeaviateAdapter,
            "to_obj",
            side_effect=AdapterValidationError(
                "Vector field 'embedding' not found in model"
            ),
        )

        # Test to_obj with missing vector field
        with pytest.raises(AdapterValidationError) as excinfo:
            await test_model.adapt_to_async(
                obj_key="async_weav",
                class_name="TestModel",
                url="http://localhost:8080",
            )

        assert "Vector field 'embedding' not found in model" in str(excinfo.value)


@weaviate_skip_marker
class TestAsyncWeaviateAdapterImplementation:
    """Test AsyncWeaviateAdapter actual implementation."""

    @pytest.mark.asyncio
    async def test_async_weaviate_to_obj_implementation(self, mocker):
        """Test the actual implementation of to_obj method."""
        # Create test instance
        test_model = TestModel(id=1, name="test", value=42.5)

        # Register adapter
        test_model.__class__.register_async_adapter(AsyncWeaviateAdapter)

        # Create a proper async context manager mock
        mock_response = mocker.AsyncMock()
        mock_response.status = 200
        mock_response.text = mocker.AsyncMock(return_value="Success")

        # Patch the aiohttp.ClientSession directly
        mock_get = mocker.patch("aiohttp.ClientSession.get")
        mock_get_cm = mocker.AsyncMock()
        mock_get_cm.__aenter__.return_value = mock_response
        mock_get.return_value = mock_get_cm

        mock_post = mocker.patch("aiohttp.ClientSession.post")
        mock_post_cm = mocker.AsyncMock()
        mock_post_cm.__aenter__.return_value = mock_response
        mock_post.return_value = mock_post_cm

        # Test to_obj implementation
        result = await AsyncWeaviateAdapter.to_obj(
            test_model,
            class_name="TestModel",
            url="http://localhost:8080",
            vector_field="embedding",
        )

        # Verify result
        assert isinstance(result, dict)
        assert "added_count" in result
        assert result["added_count"] == 1

        # Verify API calls were made
        assert mock_get.called
        assert mock_post.called

    @pytest.mark.asyncio
    async def test_async_weaviate_from_obj_implementation(self, mocker):
        """Test the actual implementation of from_obj method."""
        # Create test class
        test_cls = TestModel

        # Register adapter
        test_cls.register_async_adapter(AsyncWeaviateAdapter)

        # Create a proper async context manager mock
        mock_response = mocker.AsyncMock()
        mock_response.status = 200
        mock_response.json = mocker.AsyncMock(
            return_value={
                "data": {
                    "Get": {
                        "TestModel": [
                            {
                                "_additional": {"id": "some-uuid"},
                                "properties": {"name": "test", "value": 42.5},
                                "vector": [0.1, 0.2, 0.3, 0.4, 0.5],
                            }
                        ]
                    }
                }
            }
        )

        # Patch the aiohttp.ClientSession.post directly
        mock_post = mocker.patch("aiohttp.ClientSession.post")
        mock_post_cm = mocker.AsyncMock()
        mock_post_cm.__aenter__.return_value = mock_response
        mock_post.return_value = mock_post_cm

        # Test from_obj implementation
        result = await AsyncWeaviateAdapter.from_obj(
            test_cls,
            {
                "class_name": "TestModel",
                "query_vector": [0.1, 0.2, 0.3, 0.4, 0.5],
                "url": "http://localhost:8080",
                "top_k": 1,
            },
            many=False,
        )

        # Verify result
        assert isinstance(result, TestModel)
        # ID is generated from the UUID hash, so we can't assert an exact value
        assert isinstance(result.id, int)
        assert result.name == "test"
        assert result.value == 42.5
        assert result.embedding == [0.1, 0.2, 0.3, 0.4, 0.5]

        # Verify API calls were made
        assert mock_post.called

    @pytest.mark.asyncio
    async def test_async_weaviate_from_obj_many_implementation(self, mocker):
        """Test the actual implementation of from_obj method with many=True."""
        # Create test class
        test_cls = TestModel

        # Register adapter
        test_cls.register_async_adapter(AsyncWeaviateAdapter)

        # Create a proper async context manager mock
        mock_response = mocker.AsyncMock()
        mock_response.status = 200
        mock_response.json = mocker.AsyncMock(
            return_value={
                "data": {
                    "Get": {
                        "TestModel": [
                            {
                                "_additional": {"id": "uuid-1"},
                                "properties": {"name": "test1", "value": 42.5},
                                "vector": [0.1, 0.2, 0.3, 0.4, 0.5],
                            },
                            {
                                "_additional": {"id": "uuid-2"},
                                "properties": {"name": "test2", "value": 43.5},
                                "vector": [0.2, 0.3, 0.4, 0.5, 0.6],
                            },
                        ]
                    }
                }
            }
        )

        # Patch the aiohttp.ClientSession.post directly
        mock_post = mocker.patch("aiohttp.ClientSession.post")
        mock_post_cm = mocker.AsyncMock()
        mock_post_cm.__aenter__.return_value = mock_response
        mock_post.return_value = mock_post_cm

        # Test from_obj implementation with many=True
        results = await AsyncWeaviateAdapter.from_obj(
            test_cls,
            {
                "class_name": "TestModel",
                "query_vector": [0.1, 0.2, 0.3, 0.4, 0.5],
                "url": "http://localhost:8080",
                "top_k": 5,
            },
            many=True,
        )

        # Verify results
        assert isinstance(results, list)
        assert len(results) == 2
        assert all(isinstance(r, TestModel) for r in results)
        # IDs are generated from UUID hashes, so we can't assert exact values
        assert isinstance(results[0].id, int)
        assert results[0].name == "test1"
        assert isinstance(results[1].id, int)
        assert results[1].name == "test2"

        # Verify API calls were made
        assert mock_post.called

    @pytest.mark.asyncio
    async def test_async_weaviate_connection_error_implementation(self, mocker):
        """Test connection error handling in to_obj implementation."""
        # Create test instance
        test_model = TestModel(id=1, name="test", value=42.5)

        # Register adapter
        test_model.__class__.register_async_adapter(AsyncWeaviateAdapter)

        # Patch the aiohttp.ClientSession.get to raise an error
        mock_get = mocker.patch("aiohttp.ClientSession.get")
        mock_get.side_effect = ClientError("Connection failed")

        # Test to_obj implementation with connection error
        with pytest.raises(ConnectionError) as excinfo:
            await AsyncWeaviateAdapter.to_obj(
                test_model,
                class_name="TestModel",
                url="http://invalid-url",
                vector_field="embedding",
            )

        # Verify error message
        assert "Failed to connect to Weaviate" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_async_weaviate_query_error_implementation(self, mocker):
        """Test query error handling in from_obj implementation."""
        # Create test class
        test_cls = TestModel

        # Register adapter
        test_cls.register_async_adapter(AsyncWeaviateAdapter)

        # Create a proper async context manager mock
        mock_response = mocker.AsyncMock()
        mock_response.status = 400
        mock_response.text = mocker.AsyncMock(return_value="Bad request")

        # Patch the aiohttp.ClientSession.post directly
        mock_post = mocker.patch("aiohttp.ClientSession.post")
        mock_post_cm = mocker.AsyncMock()
        mock_post_cm.__aenter__.return_value = mock_response
        mock_post.return_value = mock_post_cm

        # Test from_obj implementation with query error
        with pytest.raises(QueryError) as excinfo:
            await AsyncWeaviateAdapter.from_obj(
                test_cls,
                {
                    "class_name": "TestModel",
                    "query_vector": [0.1, 0.2, 0.3, 0.4, 0.5],
                    "url": "http://localhost:8080",
                },
                many=False,
            )

        # Verify error message
        assert "Failed to execute Weaviate query" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_async_weaviate_graphql_error_implementation(self, mocker):
        """Test GraphQL error handling in from_obj implementation."""
        # Create test class
        test_cls = TestModel

        # Register adapter
        test_cls.register_async_adapter(AsyncWeaviateAdapter)

        # Create a proper async context manager mock
        mock_response = mocker.AsyncMock()
        mock_response.status = 200
        mock_response.json = mocker.AsyncMock(
            return_value={"errors": [{"message": "GraphQL syntax error"}]}
        )

        # Patch the aiohttp.ClientSession.post directly
        mock_post = mocker.patch("aiohttp.ClientSession.post")
        mock_post_cm = mocker.AsyncMock()
        mock_post_cm.__aenter__.return_value = mock_response
        mock_post.return_value = mock_post_cm

        # Test from_obj implementation with GraphQL error
        with pytest.raises(QueryError) as excinfo:
            await AsyncWeaviateAdapter.from_obj(
                test_cls,
                {
                    "class_name": "TestModel",
                    "query_vector": [0.1, 0.2, 0.3, 0.4, 0.5],
                    "url": "http://localhost:8080",
                },
                many=False,
            )

        # Verify error message
        assert "GraphQL error" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_async_weaviate_empty_result_implementation(self, mocker):
        """Test empty result handling in from_obj implementation."""
        # Create test class
        test_cls = TestModel

        # Register adapter
        test_cls.register_async_adapter(AsyncWeaviateAdapter)

        # Create a proper async context manager mock
        mock_response = mocker.AsyncMock()
        mock_response.status = 200
        mock_response.json = mocker.AsyncMock(
            return_value={"data": {"Get": {"TestModel": []}}}
        )

        # Patch the aiohttp.ClientSession.post directly
        mock_post = mocker.patch("aiohttp.ClientSession.post")
        mock_post_cm = mocker.AsyncMock()
        mock_post_cm.__aenter__.return_value = mock_response
        mock_post.return_value = mock_post_cm

        # Test from_obj implementation with empty result and many=True
        results = await AsyncWeaviateAdapter.from_obj(
            test_cls,
            {
                "class_name": "TestModel",
                "query_vector": [0.1, 0.2, 0.3, 0.4, 0.5],
                "url": "http://localhost:8080",
            },
            many=True,
        )

        # Verify empty list is returned
        assert isinstance(results, list)
        assert len(results) == 0

        # Verify API calls were made
        assert mock_post.called
