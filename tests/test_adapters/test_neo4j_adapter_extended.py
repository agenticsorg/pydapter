"""
Extended tests for Neo4j adapter functionality.
"""

from unittest.mock import MagicMock, call, patch

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


class TestNeo4jAdapterExtended:
    """Extended tests for Neo4j adapter functionality."""

    @patch("pydapter.extras.neo4j_.GraphDatabase")
    def test_neo4j_from_obj_with_where_clause(self, mock_graph_db, neo4j_sample):
        """Test conversion from Neo4j node to model with where clause."""
        # Setup mock session and run
        mock_session = MagicMock()
        # Configure the context manager properly
        mock_graph_db.driver.return_value.session.return_value.__enter__.return_value = mock_session

        # Mock the result of the query
        mock_result = [
            {"n": MagicMock(_properties={"id": 1, "name": "test", "value": 42.5})}
        ]
        mock_session.run.return_value = mock_result

        # Test from_obj with where clause
        model_cls = neo4j_sample.__class__
        _ = model_cls.adapt_from(
            {"url": "bolt://localhost:7687", "where": "n.id = 1"}, obj_key="neo4j"
        )

        # Verify the cypher query included the where clause
        mock_session.run.assert_called_once()
        cypher_query = mock_session.run.call_args[0][0]
        assert "WHERE n.id = 1" in cypher_query

    @patch("pydapter.extras.neo4j_.GraphDatabase")
    def test_neo4j_from_obj_with_custom_label(self, mock_graph_db, neo4j_sample):
        """Test conversion from Neo4j node to model with custom label."""
        # Setup mock session and run
        mock_session = MagicMock()
        # Configure the context manager properly
        mock_graph_db.driver.return_value.session.return_value.__enter__.return_value = mock_session

        # Mock the result of the query
        mock_result = [
            {"n": MagicMock(_properties={"id": 1, "name": "test", "value": 42.5})}
        ]
        mock_session.run.return_value = mock_result

        # Test from_obj with custom label
        model_cls = neo4j_sample.__class__
        _ = model_cls.adapt_from(
            {"url": "bolt://localhost:7687", "label": "CustomLabel"}, obj_key="neo4j"
        )

        # Verify the cypher query used the custom label
        mock_session.run.assert_called_once()
        cypher_query = mock_session.run.call_args[0][0]
        assert "MATCH (n:`CustomLabel`)" in cypher_query

    @patch("pydapter.extras.neo4j_.GraphDatabase")
    def test_neo4j_to_obj_with_custom_label(self, mock_graph_db, neo4j_sample):
        """Test conversion from model to Neo4j node with custom label."""
        # Setup mock session and run
        mock_session = MagicMock()
        # Configure the context manager properly
        mock_graph_db.driver.return_value.session.return_value.__enter__.return_value = mock_session

        # Test to_obj with custom label
        neo4j_sample.adapt_to(
            obj_key="neo4j", url="bolt://localhost:7687", label="CustomLabel"
        )

        # Verify the cypher query used the custom label
        mock_session.run.assert_called_once()
        cypher_query = mock_session.run.call_args[0][0]
        assert "MERGE (n:`CustomLabel`" in cypher_query

    @patch("pydapter.extras.neo4j_.GraphDatabase")
    def test_neo4j_to_obj_with_custom_merge_on(self, mock_graph_db, neo4j_sample):
        """Test conversion from model to Neo4j node with custom merge field."""
        # Setup mock session and run
        mock_session = MagicMock()
        # Configure the context manager properly
        mock_graph_db.driver.return_value.session.return_value.__enter__.return_value = mock_session

        # Test to_obj with custom merge_on
        neo4j_sample.adapt_to(
            obj_key="neo4j", url="bolt://localhost:7687", merge_on="name"
        )

        # Verify the cypher query used the custom merge field
        mock_session.run.assert_called_once()
        cypher_query = mock_session.run.call_args[0][0]
        assert "MERGE (n:`TestModel` {name: $val})" in cypher_query

        # Verify the parameters
        assert mock_session.run.call_args[1]["val"] == "test"
        assert mock_session.run.call_args[1]["props"] == {
            "id": 1,
            "name": "test",
            "value": 42.5,
        }

    @patch("pydapter.extras.neo4j_.GraphDatabase")
    def test_neo4j_to_obj_multiple_items(self, mock_graph_db, neo4j_model_factory):
        """Test conversion from multiple models to Neo4j nodes."""
        # Create multiple models
        model1 = neo4j_model_factory(id=1, name="test1", value=42.5)
        model2 = neo4j_model_factory(id=2, name="test2", value=43.5)

        # Setup mock session and run
        mock_session = MagicMock()
        # Configure the context manager properly
        mock_graph_db.driver.return_value.session.return_value.__enter__.return_value = mock_session

        # Test to_obj with first model
        model1.adapt_to(obj_key="neo4j", url="bolt://localhost:7687")

        # Test to_obj with second model
        model2.adapt_to(obj_key="neo4j", url="bolt://localhost:7687")

        # Verify the session.run was called twice (once for each model)
        assert mock_session.run.call_count == 2

        # Verify the parameters for each call
        calls = [
            call(
                "MERGE (n:`TestModel` {id: $val}) SET n += $props",
                val=1,
                props={"id": 1, "name": "test1", "value": 42.5},
            ),
            call(
                "MERGE (n:`TestModel` {id: $val}) SET n += $props",
                val=2,
                props={"id": 2, "name": "test2", "value": 43.5},
            ),
        ]
        mock_session.run.assert_has_calls(calls)
