"""
Integration tests for MongoDB adapter using TestContainers.
"""

import pytest
from pydapter.exceptions import ConnectionError, ResourceError
from pydapter.extras.mongo_ import MongoAdapter
from pymongo import MongoClient


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
def mongo_cleanup(mongo_url):
    """Clean up MongoDB collections after tests."""
    yield

    # Cleanup after test
    client = MongoClient(mongo_url)
    db = client["testdb"]
    for collection in db.list_collection_names():
        db.drop_collection(collection)
    client.close()


class TestMongoIntegration:
    """Integration tests for MongoDB adapter."""

    def test_mongodb_single_document(
        self, mongo_url, sync_model_factory, mongo_cleanup
    ):
        """Test MongoDB adapter with a single document."""
        # Create test instance
        test_model = sync_model_factory(id=43, name="test_mongo", value=56.78)

        # Register adapter
        test_model.__class__.register_adapter(MongoAdapter)

        # Store in database
        test_model.adapt_to(
            obj_key="mongo", url=mongo_url, db="testdb", collection="test_collection"
        )

        # Retrieve from database
        retrieved = test_model.__class__.adapt_from(
            {
                "url": mongo_url,
                "db": "testdb",
                "collection": "test_collection",
                "filter": {"id": 43},
            },
            obj_key="mongo",
            many=False,
        )

        # Verify data integrity
        assert retrieved.id == test_model.id
        assert retrieved.name == test_model.name
        assert retrieved.value == test_model.value

    def test_mongodb_batch_operations(
        self, mongo_url, sync_model_factory, mongo_cleanup
    ):
        """Test batch operations with MongoDB."""
        model_cls = sync_model_factory(id=1, name="test", value=1.0).__class__

        # Register adapter
        model_cls.register_adapter(MongoAdapter)

        # Create multiple test instances
        models = [
            model_cls(id=i, name=f"batch_{i}", value=i * 1.5) for i in range(1, 11)
        ]

        # Store batch in database
        MongoAdapter.to_obj(
            models, url=mongo_url, db="testdb", collection="batch_collection", many=True
        )

        # Retrieve all from database
        retrieved = model_cls.adapt_from(
            {"url": mongo_url, "db": "testdb", "collection": "batch_collection"},
            obj_key="mongo",
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

    def test_mongodb_connection_error(self, sync_model_factory):
        """Test handling of MongoDB connection errors."""
        test_model = sync_model_factory(id=43, name="test_mongo", value=56.78)

        # Register adapter
        test_model.__class__.register_adapter(MongoAdapter)

        # Test with invalid connection string
        with pytest.raises(ConnectionError):
            test_model.adapt_to(
                obj_key="mongo",
                url="mongodb://invalid:invalid@localhost:27017",
                db="testdb",
                collection="test_collection",
            )

    def test_mongodb_resource_not_found(
        self, mongo_url, sync_model_factory, mongo_cleanup
    ):
        """Test handling of resource not found errors."""
        model_cls = sync_model_factory(id=1, name="test", value=1.0).__class__

        # Register adapter
        model_cls.register_adapter(MongoAdapter)

        # Try to retrieve from non-existent collection
        with pytest.raises(ResourceError):
            model_cls.adapt_from(
                {
                    "url": mongo_url,
                    "db": "testdb",
                    "collection": "nonexistent_collection",
                    "filter": {"id": 999},
                },
                obj_key="mongo",
                many=False,
            )

    def test_mongodb_filter_query(self, mongo_url, sync_model_factory, mongo_cleanup):
        """Test filtering with MongoDB queries."""
        model_cls = sync_model_factory(id=1, name="test", value=1.0).__class__

        # Register adapter
        model_cls.register_adapter(MongoAdapter)

        # Create multiple test instances with different values
        models = [
            model_cls(id=i, name=f"test_{i}", value=i * 10.0) for i in range(1, 11)
        ]

        # Store batch in database
        MongoAdapter.to_obj(
            models, url=mongo_url, db="testdb", collection="filter_test", many=True
        )

        # Retrieve with filter (value > 50)
        retrieved = model_cls.adapt_from(
            {
                "url": mongo_url,
                "db": "testdb",
                "collection": "filter_test",
                "filter": {"value": {"$gt": 50}},
            },
            obj_key="mongo",
            many=True,
        )

        # Verify filtered results
        assert len(retrieved) == 5  # IDs 6-10 have values > 50
        for model in retrieved:
            assert model.value > 50
