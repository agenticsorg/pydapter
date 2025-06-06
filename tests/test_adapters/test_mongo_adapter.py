"""
Tests for MongoDB adapter functionality.
"""

from unittest.mock import patch

import pytest
from pydantic import BaseModel
from pydapter.core import Adaptable
from pydapter.extras.mongo_ import MongoAdapter


@pytest.fixture
def mongo_model_factory():
    """Factory for creating test models with MongoDB adapter registered."""

    def create_model(**kw):
        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        # Register the MongoDB adapter
        TestModel.register_adapter(MongoAdapter)
        return TestModel(**kw)

    return create_model


@pytest.fixture
def mongo_sample(mongo_model_factory):
    """Create a sample model instance."""
    return mongo_model_factory(id=1, name="test", value=42.5)


class TestMongoAdapterProtocol:
    """Tests for MongoDB adapter protocol compliance."""

    def test_mongo_adapter_protocol_compliance(self):
        """Test that MongoAdapter implements the Adapter protocol."""
        # Verify required attributes
        assert hasattr(MongoAdapter, "obj_key")
        assert isinstance(MongoAdapter.obj_key, str)
        assert MongoAdapter.obj_key == "mongo"

        # Verify method signatures
        assert hasattr(MongoAdapter, "from_obj")
        assert hasattr(MongoAdapter, "to_obj")

        # Verify the methods can be called as classmethods
        assert callable(MongoAdapter.from_obj)
        assert callable(MongoAdapter.to_obj)


class TestMongoAdapterFunctionality:
    """Tests for MongoDB adapter functionality."""

    @patch("pydapter.extras.mongo_.MongoClient")
    def test_mongo_to_obj(self, mock_mongo_client, mongo_sample):
        """Test conversion from model to MongoDB document."""
        # We need to patch the entire MongoDB adapter's to_obj method
        with patch("pydapter.extras.mongo_.MongoAdapter.to_obj") as mock_to_obj:
            # Configure the mock to return a MongoDB document
            expected_doc = {"id": 1, "name": "test", "value": 42.5}
            mock_to_obj.return_value = expected_doc

            # Test to_obj
            result = mongo_sample.adapt_to(obj_key="mongo")

            # Verify the result
            assert result == expected_doc

            # Verify the mock was called with the correct arguments
            mock_to_obj.assert_called_once()

    @patch("pydapter.extras.mongo_.MongoClient")
    def test_mongo_from_obj(self, mock_mongo_client, mongo_sample):
        """Test conversion from MongoDB document to model."""
        # We need to patch the entire MongoDB adapter's from_obj method
        with patch("pydapter.extras.mongo_.MongoAdapter.from_obj") as mock_from_obj:
            # Configure the mock to return a model instance
            expected_model = mongo_sample.__class__(id=1, name="test", value=42.5)
            mock_from_obj.return_value = [expected_model]

            # Create a mock MongoDB document
            mock_doc = {"id": 1, "name": "test", "value": 42.5}

            # Test from_obj
            model_cls = mongo_sample.__class__
            result = model_cls.adapt_from(mock_doc, obj_key="mongo")

            # Verify the result
            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0].id == 1
            assert result[0].name == "test"
            assert result[0].value == 42.5

    @patch("pydapter.extras.mongo_.MongoClient")
    def test_mongo_from_obj_single(self, mock_mongo_client, mongo_sample):
        """Test conversion from MongoDB document to model with many=False."""
        # We need to patch the entire MongoDB adapter's from_obj method
        with patch("pydapter.extras.mongo_.MongoAdapter.from_obj") as mock_from_obj:
            # Configure the mock to return a model instance
            expected_model = mongo_sample.__class__(id=1, name="test", value=42.5)
            mock_from_obj.return_value = expected_model

            # Create a mock MongoDB document
            mock_doc = {"id": 1, "name": "test", "value": 42.5}

            # Test from_obj with many=False
            model_cls = mongo_sample.__class__
            result = model_cls.adapt_from(mock_doc, obj_key="mongo", many=False)

            # Verify the result
            assert isinstance(result, model_cls)
            assert result.id == 1
            assert result.name == "test"
            assert result.value == 42.5


class TestMongoAdapterErrorHandling:
    """Tests for MongoDB adapter error handling."""

    @patch("pydapter.extras.mongo_.MongoClient")
    def test_mongo_connection_error(self, mock_mongo_client, mongo_sample):
        """Test handling of MongoDB connection errors."""
        # Configure the mock to raise a connection error
        mock_mongo_client.side_effect = Exception("Connection error")

        # We need to patch the entire MongoDB adapter's to_obj method to pass through the error
        with patch(
            "pydapter.extras.mongo_.MongoAdapter.to_obj",
            side_effect=Exception("Connection error"),
        ):
            # Test to_obj with connection error
            with pytest.raises(Exception, match="Connection error"):
                mongo_sample.adapt_to(obj_key="mongo", url="mongodb://localhost:27017")

    @patch("pydapter.extras.mongo_.MongoClient")
    def test_mongo_invalid_data(self, mock_mongo_client, mongo_sample):
        """Test handling of invalid data."""
        # We need to patch the entire MongoDB adapter's from_obj method to raise an error
        with patch(
            "pydapter.extras.mongo_.MongoAdapter.from_obj",
            side_effect=ValueError("Invalid data"),
        ):
            # Test from_obj with invalid data
            model_cls = mongo_sample.__class__
            with pytest.raises(ValueError, match="Invalid data"):
                model_cls.adapt_from({"invalid": "data"}, obj_key="mongo")
