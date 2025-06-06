"""
Integration tests for Neo4j adapter using TestContainers.
"""

import pytest
from neo4j import GraphDatabase
from pydapter.exceptions import ConnectionError, ResourceError
from pydapter.extras.neo4j_ import Neo4jAdapter


def is_docker_available():
    """Check if Docker is available."""
    import subprocess

    try:
        subprocess.run(["docker", "info"], check=True, capture_output=True)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


# Skip tests if Docker is not available
pytestmark = pytest.mark.skipif(
    not is_docker_available(), reason="Docker is not available"
)


@pytest.fixture
def neo4j_cleanup(neo4j_url, neo4j_auth):
    """Clean up Neo4j database after tests."""
    yield

    # Cleanup after test
    driver = GraphDatabase.driver(neo4j_url, auth=neo4j_auth)
    with driver.session() as session:
        # Delete all nodes with TestModel label
        session.run("MATCH (n:TestModel) DETACH DELETE n")
        # Delete all nodes with BatchTest label
        session.run("MATCH (n:BatchTest) DETACH DELETE n")
    driver.close()


class TestNeo4jIntegration:
    """Integration tests for Neo4j adapter."""

    def test_neo4j_single_node(
        self, neo4j_url, neo4j_auth, sync_model_factory, neo4j_cleanup
    ):
        """Test Neo4j adapter with a single node."""
        # Create test instance
        test_model = sync_model_factory(id=44, name="test_neo4j", value=90.12)

        # Register adapter
        test_model.__class__.register_adapter(Neo4jAdapter)

        # Store in database
        test_model.adapt_to(
            obj_key="neo4j",
            url=neo4j_url,
            auth=neo4j_auth,
            label="TestModel",
            merge_on="id",
        )
        # Retrieve from database
        retrieved = test_model.__class__.adapt_from(
            {
                "url": neo4j_url,
                "auth": neo4j_auth,
                "label": "TestModel",
                "where": "n.id = 44",
            },
            obj_key="neo4j",
            many=False,
        )

        # Verify data integrity
        assert retrieved.id == test_model.id
        assert retrieved.name == test_model.name
        assert retrieved.value == test_model.value

    def test_neo4j_batch_operations(
        self, neo4j_url, neo4j_auth, sync_model_factory, neo4j_cleanup
    ):
        """Test batch operations with Neo4j."""
        model_cls = sync_model_factory(id=1, name="test", value=1.0).__class__

        # Register adapter
        model_cls.register_adapter(Neo4jAdapter)

        # Create multiple test instances
        models = [
            model_cls(id=i, name=f"batch_{i}", value=i * 1.5) for i in range(1, 11)
        ]

        # Store batch in database
        for model in models:
            model.adapt_to(
                obj_key="neo4j",
                url=neo4j_url,
                auth=neo4j_auth,
                label="BatchTest",
                merge_on="id",
            )

        # Retrieve all from database
        retrieved = model_cls.adapt_from(
            {"url": neo4j_url, "auth": neo4j_auth, "label": "BatchTest"},
            obj_key="neo4j",
            many=True,
        )

        # Verify all records were stored and retrieved correctly
        assert len(retrieved) == 10

        # Sort by ID for consistent comparison
        retrieved_sorted = sorted(retrieved, key=lambda m: m.id)
        for i, model in enumerate(retrieved_sorted, 1):
            assert model.id == i
            assert model.name == f"batch_{i}"
            assert model.value == i * 1.5

    def test_neo4j_connection_error(self, sync_model_factory):
        """Test handling of Neo4j connection errors."""
        test_model = sync_model_factory(id=44, name="test_neo4j", value=90.12)

        # Register adapter
        test_model.__class__.register_adapter(Neo4jAdapter)

        # Test with invalid connection string
        with pytest.raises(ConnectionError):
            test_model.adapt_to(
                obj_key="neo4j",
                url="neo4j://invalid:invalid@localhost:7687",
                label="TestModel",
                merge_on="id",
            )

    def test_neo4j_resource_not_found(
        self, neo4j_url, neo4j_auth, sync_model_factory, neo4j_cleanup
    ):
        """Test handling of resource not found errors."""
        model_cls = sync_model_factory(id=1, name="test", value=1.0).__class__

        # Register adapter
        model_cls.register_adapter(Neo4jAdapter)

        # Try to retrieve from non-existent node
        with pytest.raises(ResourceError):
            model_cls.adapt_from(
                {
                    "url": neo4j_url,
                    "auth": neo4j_auth,
                    "label": "NonExistentLabel",
                    "where": "n.id = 999",
                },
                obj_key="neo4j",
                many=False,
            )

    def test_neo4j_update_node(
        self, neo4j_url, neo4j_auth, sync_model_factory, neo4j_cleanup
    ):
        """Test updating an existing node in Neo4j."""
        # Create test instance
        test_model = sync_model_factory(id=99, name="original", value=100.0)

        # Register adapter
        test_model.__class__.register_adapter(Neo4jAdapter)

        # Store in database
        test_model.adapt_to(
            obj_key="neo4j",
            url=neo4j_url,
            auth=neo4j_auth,
            label="TestModel",
            merge_on="id",
        )

        # Create updated model with same ID
        updated_model = sync_model_factory(id=99, name="updated", value=200.0)

        # Register adapter for updated model
        updated_model.__class__.register_adapter(Neo4jAdapter)

        # Update in database
        updated_model.adapt_to(
            obj_key="neo4j",
            url=neo4j_url,
            auth=neo4j_auth,
            label="TestModel",
            merge_on="id",
        )

        # Retrieve from database
        retrieved = test_model.__class__.adapt_from(
            {
                "url": neo4j_url,
                "auth": neo4j_auth,
                "label": "TestModel",
                "where": "n.id = 99",
            },
            obj_key="neo4j",
            many=False,
        )

        # Verify data was updated
        assert retrieved.id == 99
        assert retrieved.name == "updated"
        assert retrieved.value == 200.0

    def test_neo4j_where_clause(
        self, neo4j_url, neo4j_auth, sync_model_factory, neo4j_cleanup
    ):
        """Test filtering with Neo4j where clause."""
        model_cls = sync_model_factory(id=1, name="test", value=1.0).__class__

        # Register adapter
        model_cls.register_adapter(Neo4jAdapter)

        # Create multiple test instances with different values
        models = [
            model_cls(id=i, name=f"test_{i}", value=i * 10.0) for i in range(1, 11)
        ]

        # Store batch in database
        for model in models:
            model.adapt_to(
                obj_key="neo4j",
                url=neo4j_url,
                auth=neo4j_auth,
                label="TestModel",
                merge_on="id",
            )

        # Retrieve with where clause (value > 50)
        retrieved = model_cls.adapt_from(
            {
                "url": neo4j_url,
                "auth": neo4j_auth,
                "label": "TestModel",
                "where": "n.value > 50",
            },
            obj_key="neo4j",
            many=True,
        )

        # Verify filtered results
        assert len(retrieved) == 5  # IDs 6-10 have values > 50
        for model in retrieved:
            assert model.value > 50
