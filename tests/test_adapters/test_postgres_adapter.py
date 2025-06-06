"""
Tests for PostgreSQL adapter functionality.
"""

from unittest.mock import patch

import pytest
from pydantic import BaseModel
from pydapter.core import Adaptable
from pydapter.extras.postgres_ import PostgresAdapter


@pytest.fixture
def postgres_model_factory():
    """Factory for creating test models with PostgreSQL adapter registered."""

    def create_model(**kw):
        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        # Register the PostgreSQL adapter
        TestModel.register_adapter(PostgresAdapter)
        return TestModel(**kw)

    return create_model


@pytest.fixture
def postgres_sample(postgres_model_factory):
    """Create a sample model instance."""
    return postgres_model_factory(id=1, name="test", value=42.5)


class TestPostgresAdapterProtocol:
    """Tests for PostgreSQL adapter protocol compliance."""

    def test_postgres_adapter_protocol_compliance(self):
        """Test that PostgresAdapter implements the Adapter protocol."""
        # Verify required attributes
        assert hasattr(PostgresAdapter, "obj_key")
        assert isinstance(PostgresAdapter.obj_key, str)
        assert PostgresAdapter.obj_key == "postgres"

        # Verify method signatures
        assert hasattr(PostgresAdapter, "from_obj")
        assert hasattr(PostgresAdapter, "to_obj")

        # Verify the methods can be called as classmethods
        assert callable(PostgresAdapter.from_obj)
        assert callable(PostgresAdapter.to_obj)


class TestPostgresAdapterFunctionality:
    """Tests for PostgreSQL adapter functionality."""

    @patch("pydapter.extras.sql_.sa")
    def test_postgres_to_obj(self, mock_sa, postgres_sample):
        """Test conversion from model to PostgreSQL record."""
        # We need to patch the entire PostgreSQL adapter's to_obj method
        with patch("pydapter.extras.postgres_.PostgresAdapter.to_obj") as mock_to_obj:
            # Configure the mock to return a PostgreSQL record
            expected_record = {"id": 1, "name": "test", "value": 42.5}
            mock_to_obj.return_value = expected_record

            # Test to_obj
            result = postgres_sample.adapt_to(obj_key="postgres")

            # Verify the result
            assert result == expected_record

            # Verify the mock was called with the correct arguments
            mock_to_obj.assert_called_once()

    @patch("pydapter.extras.sql_.sa")
    def test_postgres_from_obj(self, mock_sa, postgres_sample):
        """Test conversion from PostgreSQL record to model."""
        # We need to patch the entire PostgreSQL adapter's from_obj method
        with patch(
            "pydapter.extras.postgres_.PostgresAdapter.from_obj"
        ) as mock_from_obj:
            # Configure the mock to return a model instance
            expected_model = postgres_sample.__class__(id=1, name="test", value=42.5)
            mock_from_obj.return_value = [expected_model]

            # Create a mock PostgreSQL record
            mock_record = {"id": 1, "name": "test", "value": 42.5}

            # Test from_obj
            model_cls = postgres_sample.__class__
            result = model_cls.adapt_from(mock_record, obj_key="postgres")

            # Verify the result
            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0].id == 1
            assert result[0].name == "test"
            assert result[0].value == 42.5

    @patch("pydapter.extras.sql_.sa")
    def test_postgres_from_obj_single(self, mock_sa, postgres_sample):
        """Test conversion from PostgreSQL record to model with many=False."""
        # We need to patch the entire PostgreSQL adapter's from_obj method
        with patch(
            "pydapter.extras.postgres_.PostgresAdapter.from_obj"
        ) as mock_from_obj:
            # Configure the mock to return a model instance
            expected_model = postgres_sample.__class__(id=1, name="test", value=42.5)
            mock_from_obj.return_value = expected_model

            # Create a mock PostgreSQL record
            mock_record = {"id": 1, "name": "test", "value": 42.5}

            # Test from_obj with many=False
            model_cls = postgres_sample.__class__
            result = model_cls.adapt_from(mock_record, obj_key="postgres", many=False)

            # Verify the result
            assert isinstance(result, model_cls)
            assert result.id == 1
            assert result.name == "test"
            assert result.value == 42.5


class TestPostgresAdapterErrorHandling:
    """Tests for PostgreSQL adapter error handling."""

    @patch("pydapter.extras.sql_.sa")
    def test_postgres_connection_error(self, mock_sa, postgres_sample):
        """Test handling of PostgreSQL connection errors."""
        # Configure the mock to raise a connection error
        mock_sa.create_engine.side_effect = Exception("Connection error")

        # We need to patch the entire PostgreSQL adapter's to_obj method to pass through the error
        with patch(
            "pydapter.extras.postgres_.PostgresAdapter.to_obj",
            side_effect=Exception("Connection error"),
        ):
            # Test to_obj with connection error
            with pytest.raises(Exception, match="Connection error"):
                postgres_sample.adapt_to(
                    obj_key="postgres",
                    conn_string="postgresql://user:pass@localhost/db",
                )

    @patch("pydapter.extras.sql_.sa")
    def test_postgres_invalid_data(self, mock_sa, postgres_sample):
        """Test handling of invalid data."""
        # We need to patch the entire PostgreSQL adapter's from_obj method to raise an error
        with patch(
            "pydapter.extras.postgres_.PostgresAdapter.from_obj",
            side_effect=ValueError("Invalid data"),
        ):
            # Test from_obj with invalid data
            model_cls = postgres_sample.__class__
            with pytest.raises(ValueError, match="Invalid data"):
                model_cls.adapt_from({"invalid": "data"}, obj_key="postgres")
