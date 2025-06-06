"""
Integration tests for PostgreSQL adapter using TestContainers.
"""

import pytest
import sqlalchemy as sa
from pydapter.exceptions import ConnectionError
from pydapter.extras.postgres_ import PostgresAdapter


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
def postgres_table(pg_url):
    """Create a test table in PostgreSQL."""
    engine = sa.create_engine(pg_url)
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                """
            CREATE TABLE IF NOT EXISTS test_table (
                id INTEGER PRIMARY KEY,
                name TEXT,
                value FLOAT
            )
        """
            )
        )

    yield

    # Cleanup
    with engine.begin() as conn:
        conn.execute(sa.text("DROP TABLE IF EXISTS test_table"))


class TestPostgresIntegration:
    """Integration tests for PostgreSQL adapter."""

    def test_postgres_single_record(self, pg_url, sync_model_factory, postgres_table):
        """Test PostgreSQL adapter with a single record."""
        # Create test instance
        test_model = sync_model_factory(id=42, name="test_postgres", value=12.34)

        # Register adapter
        test_model.__class__.register_adapter(PostgresAdapter)

        # Store in database
        test_model.adapt_to(obj_key="postgres", engine_url=pg_url, table="test_table")

        # Retrieve from database
        retrieved = test_model.__class__.adapt_from(
            {"engine_url": pg_url, "table": "test_table", "selectors": {"id": 42}},
            obj_key="postgres",
            many=False,
        )

        # Verify data integrity
        assert retrieved.id == test_model.id
        assert retrieved.name == test_model.name
        assert retrieved.value == test_model.value

    def test_postgres_batch_operations(
        self, pg_url, sync_model_factory, postgres_table
    ):
        """Test batch operations with PostgreSQL."""
        model_cls = sync_model_factory(id=1, name="test", value=1.0).__class__

        # Register adapter
        model_cls.register_adapter(PostgresAdapter)

        # Create multiple test instances
        models = [
            model_cls(id=i, name=f"batch_{i}", value=i * 1.5) for i in range(1, 11)
        ]

        # Store batch in database
        PostgresAdapter.to_obj(models, engine_url=pg_url, table="test_table", many=True)

        # Retrieve all from database
        retrieved = model_cls.adapt_from(
            {"engine_url": pg_url, "table": "test_table"}, obj_key="postgres", many=True
        )

        # Verify all records were stored and retrieved correctly
        assert len(retrieved) == 10

        # Sort by ID for consistent comparison
        retrieved_sorted = sorted(retrieved, key=lambda m: m.id)
        for i, model in enumerate(retrieved_sorted, 1):
            assert model.id == i
            assert model.name == f"batch_{i}"
            assert model.value == i * 1.5

    def test_postgres_connection_error(self, sync_model_factory):
        """Test handling of PostgreSQL connection errors."""
        test_model = sync_model_factory(id=42, name="test_postgres", value=12.34)

        # Register adapter
        test_model.__class__.register_adapter(PostgresAdapter)

        # Test with invalid connection string
        with pytest.raises(ConnectionError):
            test_model.adapt_to(
                obj_key="postgres",
                engine_url="postgresql://invalid:invalid@localhost:5432/nonexistent",
                table="test_table",
            )

    def test_postgres_update_record(self, pg_url, sync_model_factory, postgres_table):
        """Test updating an existing record in PostgreSQL."""
        # Create test instance
        test_model = sync_model_factory(id=99, name="original", value=100.0)

        # Register adapter
        test_model.__class__.register_adapter(PostgresAdapter)

        # Store in database
        test_model.adapt_to(obj_key="postgres", engine_url=pg_url, table="test_table")

        # Create updated model with same ID
        updated_model = sync_model_factory(id=99, name="updated", value=200.0)

        # Register adapter for updated model
        updated_model.__class__.register_adapter(PostgresAdapter)

        # Update in database
        updated_model.adapt_to(
            obj_key="postgres", engine_url=pg_url, table="test_table"
        )

        # Retrieve from database
        retrieved = test_model.__class__.adapt_from(
            {"engine_url": pg_url, "table": "test_table", "selectors": {"id": 99}},
            obj_key="postgres",
            many=False,
        )

        # Verify data was updated
        assert retrieved.id == 99
        assert retrieved.name == "updated"
        assert retrieved.value == 200.0
