"""
Tests for Neo4j adapter functionality.
"""

from unittest.mock import patch

import pytest
from pydantic import BaseModel
from pydapter.core import Adaptable
from pydapter.extras.neo4j_ import Neo4jAdapter


@pytest.fixture
def neo4j_model_factory():
    """Factory for creating test models with Neo4j adapter registered."""

    def create_model(**kw):
        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        # Register the Neo4j adapter
        TestModel.register_adapter(Neo4jAdapter)
        return TestModel(**kw)

    return create_model


@pytest.fixture
def neo4j_sample(neo4j_model_factory):
    """Create a sample model instance."""
    return neo4j_model_factory(id=1, name="test", value=42.5)


class TestNeo4jAdapterProtocol:
    """Tests for Neo4j adapter protocol compliance."""

    def test_neo4j_adapter_protocol_compliance(self):
        """Test that Neo4jAdapter implements the Adapter protocol."""
        # Verify required attributes
        assert hasattr(Neo4jAdapter, "obj_key")
        assert isinstance(Neo4jAdapter.obj_key, str)
        assert Neo4jAdapter.obj_key == "neo4j"

        # Verify method signatures
        assert hasattr(Neo4jAdapter, "from_obj")
        assert hasattr(Neo4jAdapter, "to_obj")

        # Verify the methods can be called as classmethods
        assert callable(Neo4jAdapter.from_obj)
        assert callable(Neo4jAdapter.to_obj)


class TestNeo4jAdapterFunctionality:
    """Tests for Neo4j adapter functionality."""

    @patch("pydapter.extras.neo4j_.GraphDatabase")
    def test_neo4j_to_obj(self, mock_graph_db, neo4j_sample):
        """Test conversion from model to Neo4j node."""
        # We need to patch the entire Neo4j adapter's to_obj method
        with patch("pydapter.extras.neo4j_.Neo4jAdapter.to_obj") as mock_to_obj:
            # Configure the mock to return a Neo4j node
            expected_node = {"id": 1, "name": "test", "value": 42.5}
            mock_to_obj.return_value = expected_node

            # Test to_obj
            result = neo4j_sample.adapt_to(obj_key="neo4j")

            # Verify the result
            assert result == expected_node

            # Verify the mock was called with the correct arguments
            mock_to_obj.assert_called_once()

    @patch("pydapter.extras.neo4j_.GraphDatabase")
    def test_neo4j_from_obj(self, mock_graph_db, neo4j_sample):
        """Test conversion from Neo4j node to model."""
        # We need to patch the entire Neo4j adapter's from_obj method
        with patch("pydapter.extras.neo4j_.Neo4jAdapter.from_obj") as mock_from_obj:
            # Configure the mock to return a model instance
            expected_model = neo4j_sample.__class__(id=1, name="test", value=42.5)
            mock_from_obj.return_value = [expected_model]

            # Create a mock Neo4j node
            mock_node = {"id": 1, "name": "test", "value": 42.5}

            # Test from_obj
            model_cls = neo4j_sample.__class__
            result = model_cls.adapt_from(mock_node, obj_key="neo4j")

            # Verify the result
            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0].id == 1
            assert result[0].name == "test"
            assert result[0].value == 42.5

    @patch("pydapter.extras.neo4j_.GraphDatabase")
    def test_neo4j_from_obj_single(self, mock_graph_db, neo4j_sample):
        """Test conversion from Neo4j node to model with many=False."""
        # We need to patch the entire Neo4j adapter's from_obj method
        with patch("pydapter.extras.neo4j_.Neo4jAdapter.from_obj") as mock_from_obj:
            # Configure the mock to return a model instance
            expected_model = neo4j_sample.__class__(id=1, name="test", value=42.5)
            mock_from_obj.return_value = expected_model

            # Create a mock Neo4j node
            mock_node = {"id": 1, "name": "test", "value": 42.5}

            # Test from_obj with many=False
            model_cls = neo4j_sample.__class__
            result = model_cls.adapt_from(mock_node, obj_key="neo4j", many=False)

            # Verify the result
            assert isinstance(result, model_cls)
            assert result.id == 1
            assert result.name == "test"
            assert result.value == 42.5


class TestNeo4jAdapterErrorHandling:
    """Tests for Neo4j adapter error handling."""

    @patch("pydapter.extras.neo4j_.GraphDatabase")
    def test_neo4j_connection_error(self, mock_graph_db, neo4j_sample):
        """Test handling of Neo4j connection errors."""
        # Configure the mock to raise a connection error
        mock_graph_db.driver.side_effect = Exception("Connection error")

        # We need to patch the entire Neo4j adapter's to_obj method to pass through the error
        with patch(
            "pydapter.extras.neo4j_.Neo4jAdapter.to_obj",
            side_effect=Exception("Connection error"),
        ):
            # Test to_obj with connection error
            with pytest.raises(Exception, match="Connection error"):
                neo4j_sample.adapt_to(obj_key="neo4j", uri="bolt://localhost:7687")

    @patch("pydapter.extras.neo4j_.GraphDatabase")
    def test_neo4j_invalid_data(self, mock_graph_db, neo4j_sample):
        """Test handling of invalid data."""
        # We need to patch the entire Neo4j adapter's from_obj method to raise an error
        with patch(
            "pydapter.extras.neo4j_.Neo4jAdapter.from_obj",
            side_effect=ValueError("Invalid data"),
        ):
            # Test from_obj with invalid data
            model_cls = neo4j_sample.__class__
            with pytest.raises(ValueError, match="Invalid data"):
                model_cls.adapt_from({"invalid": "data"}, obj_key="neo4j")
