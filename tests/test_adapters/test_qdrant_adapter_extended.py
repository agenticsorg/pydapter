"""
Extended tests for Qdrant adapter functionality.
"""

from unittest.mock import MagicMock, patch

import pytest
from pydantic import BaseModel
from pydapter.core import Adaptable
from pydapter.extras.qdrant_ import QdrantAdapter


@pytest.fixture
def qdrant_model_factory():
    """Factory for creating test models with Qdrant adapter registered."""

    def create_model(**kw):
        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float
            embedding: list[float] = [0.1, 0.2, 0.3, 0.4, 0.5]

        # Register the Qdrant adapter
        TestModel.register_adapter(QdrantAdapter)
        return TestModel(**kw)

    return create_model


@pytest.fixture
def qdrant_sample(qdrant_model_factory):
    """Create a sample model instance."""
    return qdrant_model_factory(id=1, name="test", value=42.5)


class TestQdrantAdapterExtended:
    """Extended tests for Qdrant adapter functionality."""

    def test_qdrant_client_helper_with_url(self):
        """Test the _client helper method with URL."""
        # Mock the QdrantClient
        with patch("pydapter.extras.qdrant_.QdrantClient") as mock_qdrant_client:
            # Call the _client helper with a URL
            QdrantAdapter._client("http://localhost:6333")

            # Verify QdrantClient was called with the URL
            mock_qdrant_client.assert_called_once_with(url="http://localhost:6333")

    def test_qdrant_client_helper_without_url(self):
        """Test the _client helper method without URL (in-memory)."""
        # Mock the QdrantClient
        with patch("pydapter.extras.qdrant_.QdrantClient") as mock_qdrant_client:
            # Call the _client helper without a URL
            QdrantAdapter._client(None)

            # Verify QdrantClient was called with :memory:
            mock_qdrant_client.assert_called_once_with(":memory:")

    @patch("pydapter.extras.qdrant_.QdrantClient")
    def test_qdrant_to_obj_with_custom_vector_field(
        self, mock_qdrant_client, qdrant_model_factory
    ):
        """Test conversion from model to Qdrant point with custom vector field."""
        # Create a model with a custom vector field
        model = qdrant_model_factory(
            id=1,
            name="test",
            value=42.5,
            embedding=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6],  # 6-dimensional vector
        )

        # Setup mock client
        mock_client = MagicMock()
        mock_qdrant_client.return_value = mock_client

        # Test to_obj with custom vector field
        model.adapt_to(
            obj_key="qdrant",
            collection="test_collection",
            vector_field="embedding",  # explicitly specify the default
            url="http://localhost:6333",
        )

        # Verify recreate_collection was called with the correct vector dimension
        mock_client.recreate_collection.assert_called_once()
        call_args = mock_client.recreate_collection.call_args[1]
        assert call_args["vectors_config"].size == 6  # Should match our 6D vector

        # Verify upsert was called with the correct point
        mock_client.upsert.assert_called_once()
        collection_arg, points_arg = mock_client.upsert.call_args[0]
        assert collection_arg == "test_collection"
        assert len(points_arg) == 1
        assert points_arg[0].id == 1
        assert points_arg[0].vector == [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]

        # Check that the payload contains the expected fields
        # Note: The payload may also contain the embedding field, which we don't check here
        payload = points_arg[0].payload
        assert payload["id"] == 1
        assert payload["name"] == "test"
        assert payload["value"] == 42.5

    @patch("pydapter.extras.qdrant_.QdrantClient")
    def test_qdrant_to_obj_with_custom_id_field(
        self, mock_qdrant_client, qdrant_model_factory
    ):
        """Test conversion from model to Qdrant point with custom ID field."""
        # Create a model with a custom field that will be used as ID
        model = qdrant_model_factory(
            id=1,
            name="custom_id_value",
            value=42.5,  # We'll use this as the ID
        )

        # Setup mock client
        mock_client = MagicMock()
        mock_qdrant_client.return_value = mock_client

        # Test to_obj with custom ID field
        model.adapt_to(
            obj_key="qdrant",
            collection="test_collection",
            id_field="name",  # Use name as the ID field
            url="http://localhost:6333",
        )

        # Verify upsert was called with the correct point ID
        mock_client.upsert.assert_called_once()
        collection_arg, points_arg = mock_client.upsert.call_args[0]
        assert points_arg[0].id == "custom_id_value"  # ID should be the name value

    @patch("pydapter.extras.qdrant_.QdrantClient")
    def test_qdrant_to_obj_multiple_items(
        self, mock_qdrant_client, qdrant_model_factory
    ):
        """Test conversion from multiple models to Qdrant points."""
        # Create multiple models
        model1 = qdrant_model_factory(id=1, name="test1", value=42.5)
        model2 = qdrant_model_factory(id=2, name="test2", value=43.5)

        # Setup mock client
        mock_client = MagicMock()
        mock_qdrant_client.return_value = mock_client

        # Directly test the adapter's to_obj method with multiple items
        QdrantAdapter.to_obj(
            [model1, model2], collection="test_collection", url="http://localhost:6333"
        )

        # Verify upsert was called with multiple points
        mock_client.upsert.assert_called_once()
        collection_arg, points_arg = mock_client.upsert.call_args[0]
        assert collection_arg == "test_collection"
        assert len(points_arg) == 2
        assert points_arg[0].id == 1
        assert points_arg[1].id == 2

    @patch("pydapter.extras.qdrant_.QdrantClient")
    def test_qdrant_from_obj_with_custom_parameters(
        self, mock_qdrant_client, qdrant_sample
    ):
        """Test conversion from Qdrant search results to model with custom parameters."""
        # Setup mock client and search results
        mock_client = MagicMock()
        mock_qdrant_client.return_value = mock_client

        # Create mock search results
        mock_result1 = MagicMock()
        mock_result1.payload = {"id": 1, "name": "test1", "value": 42.5}

        mock_result2 = MagicMock()
        mock_result2.payload = {"id": 2, "name": "test2", "value": 43.5}

        mock_client.search.return_value = [mock_result1, mock_result2]

        # Test from_obj with custom parameters
        model_cls = qdrant_sample.__class__
        result = model_cls.adapt_from(
            {
                "collection": "test_collection",
                "query_vector": [0.1, 0.2, 0.3, 0.4, 0.5],
                "top_k": 10,  # Custom top_k
                "url": "http://localhost:6333",
            },
            obj_key="qdrant",
        )

        # Verify search was called with the correct parameters
        mock_client.search.assert_called_once_with(
            "test_collection",
            [0.1, 0.2, 0.3, 0.4, 0.5],
            limit=10,  # Should use our custom top_k
            with_payload=True,
            score_threshold=0.0,  # This is set in the implementation
        )

        # Verify the result
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0].id == 1
        assert result[0].name == "test1"
        assert result[0].value == 42.5
        assert result[1].id == 2
        assert result[1].name == "test2"
        assert result[1].value == 43.5

    @patch("pydapter.extras.qdrant_.QdrantClient")
    def test_qdrant_from_obj_single(self, mock_qdrant_client, qdrant_sample):
        """Test conversion from Qdrant search results to model with many=False."""
        # Setup mock client and search results
        mock_client = MagicMock()
        mock_qdrant_client.return_value = mock_client

        # Create mock search result
        mock_result = MagicMock()
        mock_result.payload = {"id": 1, "name": "test", "value": 42.5}

        mock_client.search.return_value = [mock_result]

        # Test from_obj with many=False
        model_cls = qdrant_sample.__class__
        result = model_cls.adapt_from(
            {
                "collection": "test_collection",
                "query_vector": [0.1, 0.2, 0.3, 0.4, 0.5],
                "url": "http://localhost:6333",
            },
            obj_key="qdrant",
            many=False,
        )

        # Verify the result is a single model, not a list
        assert not isinstance(result, list)
        assert result.id == 1
        assert result.name == "test"
        assert result.value == 42.5
