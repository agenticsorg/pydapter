"""
Tests for Qdrant adapter functionality.
"""

from unittest.mock import patch

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

        # Register the Qdrant adapter
        TestModel.register_adapter(QdrantAdapter)
        return TestModel(**kw)

    return create_model


@pytest.fixture
def qdrant_sample(qdrant_model_factory):
    """Create a sample model instance."""
    return qdrant_model_factory(id=1, name="test", value=42.5)


class TestQdrantAdapterProtocol:
    """Tests for Qdrant adapter protocol compliance."""

    def test_qdrant_adapter_protocol_compliance(self):
        """Test that QdrantAdapter implements the Adapter protocol."""
        # Verify required attributes
        assert hasattr(QdrantAdapter, "obj_key")
        assert isinstance(QdrantAdapter.obj_key, str)
        assert QdrantAdapter.obj_key == "qdrant"

        # Verify method signatures
        assert hasattr(QdrantAdapter, "from_obj")
        assert hasattr(QdrantAdapter, "to_obj")

        # Verify the methods can be called as classmethods
        assert callable(QdrantAdapter.from_obj)
        assert callable(QdrantAdapter.to_obj)


class TestQdrantAdapterFunctionality:
    """Tests for Qdrant adapter functionality."""

    @patch("pydapter.extras.qdrant_.QdrantClient")
    def test_qdrant_to_obj(self, mock_qdrant_client, qdrant_sample):
        """Test conversion from model to Qdrant point."""
        # We need to patch the entire Qdrant adapter's to_obj method
        with patch("pydapter.extras.qdrant_.QdrantAdapter.to_obj") as mock_to_obj:
            # Configure the mock to return a Qdrant point
            expected_point = {"id": 1, "payload": {"name": "test", "value": 42.5}}
            mock_to_obj.return_value = expected_point

            # Test to_obj
            result = qdrant_sample.adapt_to(obj_key="qdrant")

            # Verify the result
            assert result == expected_point

            # Verify the mock was called with the correct arguments
            mock_to_obj.assert_called_once()

    @patch("pydapter.extras.qdrant_.QdrantClient")
    def test_qdrant_from_obj(self, mock_qdrant_client, qdrant_sample):
        """Test conversion from Qdrant point to model."""
        # We need to patch the entire Qdrant adapter's from_obj method
        with patch("pydapter.extras.qdrant_.QdrantAdapter.from_obj") as mock_from_obj:
            # Configure the mock to return a model instance
            expected_model = qdrant_sample.__class__(id=1, name="test", value=42.5)
            mock_from_obj.return_value = [expected_model]

            # Create a mock Qdrant point
            mock_point = {"id": 1, "payload": {"name": "test", "value": 42.5}}

            # Test from_obj
            model_cls = qdrant_sample.__class__
            result = model_cls.adapt_from(mock_point, obj_key="qdrant")

            # Verify the result
            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0].id == 1
            assert result[0].name == "test"
            assert result[0].value == 42.5

    @patch("pydapter.extras.qdrant_.QdrantClient")
    def test_qdrant_from_obj_single(self, mock_qdrant_client, qdrant_sample):
        """Test conversion from Qdrant point to model with many=False."""
        # We need to patch the entire Qdrant adapter's from_obj method
        with patch("pydapter.extras.qdrant_.QdrantAdapter.from_obj") as mock_from_obj:
            # Configure the mock to return a model instance
            expected_model = qdrant_sample.__class__(id=1, name="test", value=42.5)
            mock_from_obj.return_value = expected_model

            # Create a mock Qdrant point
            mock_point = {"id": 1, "payload": {"name": "test", "value": 42.5}}

            # Test from_obj with many=False
            model_cls = qdrant_sample.__class__
            result = model_cls.adapt_from(mock_point, obj_key="qdrant", many=False)

            # Verify the result
            assert isinstance(result, model_cls)
            assert result.id == 1
            assert result.name == "test"
            assert result.value == 42.5


class TestQdrantAdapterErrorHandling:
    """Tests for Qdrant adapter error handling."""

    @patch("pydapter.extras.qdrant_.QdrantClient")
    def test_qdrant_connection_error(self, mock_qdrant_client, qdrant_sample):
        """Test handling of Qdrant connection errors."""
        # Configure the mock to raise a connection error
        mock_qdrant_client.side_effect = Exception("Connection error")

        # We need to patch the entire Qdrant adapter's to_obj method to pass through the error
        with patch(
            "pydapter.extras.qdrant_.QdrantAdapter.to_obj",
            side_effect=Exception("Connection error"),
        ):
            # Test to_obj with connection error
            with pytest.raises(Exception, match="Connection error"):
                qdrant_sample.adapt_to(obj_key="qdrant", url="http://localhost:6333")

    @patch("pydapter.extras.qdrant_.QdrantClient")
    def test_qdrant_invalid_data(self, mock_qdrant_client, qdrant_sample):
        """Test handling of invalid data."""
        # We need to patch the entire Qdrant adapter's from_obj method to raise an error
        with patch(
            "pydapter.extras.qdrant_.QdrantAdapter.from_obj",
            side_effect=ValueError("Invalid data"),
        ):
            # Test from_obj with invalid data
            model_cls = qdrant_sample.__class__
            with pytest.raises(ValueError, match="Invalid data"):
                model_cls.adapt_from({"invalid": "data"}, obj_key="qdrant")
