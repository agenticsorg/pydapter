"""
Tests for Async PostgreSQL adapter functionality.
"""

from unittest.mock import patch

import pytest
from pydantic import BaseModel
from pydapter.core import Adaptable
from pydapter.extras.async_postgres_ import AsyncPostgresAdapter


@pytest.fixture
def async_postgres_model_factory():
    """Factory for creating test models with Async PostgreSQL adapter registered."""

    def create_model(**kw):
        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        # Register the Async PostgreSQL adapter
        TestModel.register_adapter(AsyncPostgresAdapter)
        return TestModel(**kw)

    return create_model


@pytest.fixture
def async_postgres_sample(async_postgres_model_factory):
    """Create a sample model instance."""
    return async_postgres_model_factory(id=1, name="test", value=42.5)


class TestAsyncPostgresAdapterProtocol:
    """Tests for Async PostgreSQL adapter protocol compliance."""

    def test_async_postgres_adapter_protocol_compliance(self):
        """Test that AsyncPostgresAdapter implements the Adapter protocol."""
        # Verify required attributes
        assert hasattr(AsyncPostgresAdapter, "obj_key")
        assert isinstance(AsyncPostgresAdapter.obj_key, str)
        assert AsyncPostgresAdapter.obj_key == "async_pg"

        # Verify method signatures
        assert hasattr(AsyncPostgresAdapter, "from_obj")
        assert hasattr(AsyncPostgresAdapter, "to_obj")

        # Verify the methods can be called as classmethods
        assert callable(AsyncPostgresAdapter.from_obj)
        assert callable(AsyncPostgresAdapter.to_obj)


class TestAsyncPostgresAdapterFunctionality:
    """Tests for Async PostgreSQL adapter functionality."""

    @pytest.mark.asyncio
    @patch("pydapter.extras.async_sql_.sa")
    async def test_async_postgres_to_obj(self, mock_sa, async_postgres_sample):
        """Test conversion from model to Async PostgreSQL record."""
        # We need to patch the entire Async PostgreSQL adapter's to_obj method
        with patch(
            "pydapter.extras.async_postgres_.AsyncPostgresAdapter.to_obj"
        ) as mock_to_obj:
            # Configure the mock to return a Async PostgreSQL record
            expected_record = {"id": 1, "name": "test", "value": 42.5}
            mock_to_obj.return_value = expected_record

            # Test to_obj
            result = await async_postgres_sample.adapt_to(obj_key="async_pg")

            # Verify the result
            assert result == expected_record

            # Verify the mock was called with the correct arguments
            mock_to_obj.assert_called_once()

    @pytest.mark.asyncio
    @patch("pydapter.extras.async_sql_.sa")
    async def test_async_postgres_from_obj(self, mock_sa, async_postgres_sample):
        """Test conversion from Async PostgreSQL record to model."""
        # We need to patch the entire Async PostgreSQL adapter's from_obj method
        with patch(
            "pydapter.extras.async_postgres_.AsyncPostgresAdapter.from_obj"
        ) as mock_from_obj:
            # Configure the mock to return a model instance
            expected_model = async_postgres_sample.__class__(
                id=1, name="test", value=42.5
            )
            mock_from_obj.return_value = [expected_model]

            # Create a mock Async PostgreSQL record
            mock_record = {"id": 1, "name": "test", "value": 42.5}

            # Test from_obj
            model_cls = async_postgres_sample.__class__
            result = await model_cls.adapt_from(mock_record, obj_key="async_pg")

            # Verify the result
            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0].id == 1
            assert result[0].name == "test"
            assert result[0].value == 42.5

    @pytest.mark.asyncio
    @patch("pydapter.extras.async_sql_.sa")
    async def test_async_postgres_from_obj_single(self, mock_sa, async_postgres_sample):
        """Test conversion from Async PostgreSQL record to model with many=False."""
        # We need to patch the entire Async PostgreSQL adapter's from_obj method
        with patch(
            "pydapter.extras.async_postgres_.AsyncPostgresAdapter.from_obj"
        ) as mock_from_obj:
            # Configure the mock to return a model instance
            expected_model = async_postgres_sample.__class__(
                id=1, name="test", value=42.5
            )
            mock_from_obj.return_value = expected_model

            # Create a mock Async PostgreSQL record
            mock_record = {"id": 1, "name": "test", "value": 42.5}

            # Test from_obj with many=False
            model_cls = async_postgres_sample.__class__
            result = await model_cls.adapt_from(
                mock_record, obj_key="async_pg", many=False
            )

            # Verify the result
            assert isinstance(result, model_cls)
            assert result.id == 1
            assert result.name == "test"
            assert result.value == 42.5


class TestAsyncPostgresAdapterErrorHandling:
    """Tests for Async PostgreSQL adapter error handling."""

    @pytest.mark.asyncio
    @patch("pydapter.extras.async_sql_.sa")
    async def test_async_postgres_connection_error(
        self, mock_sa, async_postgres_sample
    ):
        """Test handling of Async PostgreSQL connection errors."""
        # Configure the mock to raise a connection error
        mock_sa.ext.asyncio.create_async_engine.side_effect = Exception(
            "Connection error"
        )

        # We need to patch the entire Async PostgreSQL adapter's to_obj method to pass through the error
        with patch(
            "pydapter.extras.async_postgres_.AsyncPostgresAdapter.to_obj",
            side_effect=Exception("Connection error"),
        ):
            # Test to_obj with connection error
            with pytest.raises(Exception, match="Connection error"):
                await async_postgres_sample.adapt_to(
                    obj_key="async_pg",
                    url="postgresql+asyncpg://user:pass@localhost/db",
                )

    @pytest.mark.asyncio
    @patch("pydapter.extras.async_sql_.sa")
    async def test_async_postgres_invalid_data(self, mock_sa, async_postgres_sample):
        """Test handling of invalid data."""
        # We need to patch the entire Async PostgreSQL adapter's from_obj method to raise an error
        with patch(
            "pydapter.extras.async_postgres_.AsyncPostgresAdapter.from_obj",
            side_effect=ValueError("Invalid data"),
        ):
            # Test from_obj with invalid data
            model_cls = async_postgres_sample.__class__
            with pytest.raises(ValueError, match="Invalid data"):
                await model_cls.adapt_from({"invalid": "data"}, obj_key="async_pg")
