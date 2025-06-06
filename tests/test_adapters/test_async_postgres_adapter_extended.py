"""
Extended tests for Async PostgreSQL adapter functionality.
"""

from unittest.mock import AsyncMock, patch

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


class TestAsyncPostgresAdapterExtended:
    """Extended tests for Async PostgreSQL adapter functionality."""

    @pytest.mark.asyncio
    async def test_async_postgres_from_obj_with_dsn_conversion(self):
        """Test conversion from Async PostgreSQL record to model with DSN conversion."""
        # Setup mocks for the parent class method
        with patch(
            "pydapter.extras.async_postgres_.AsyncSQLAdapter.from_obj", AsyncMock()
        ) as mock_from_obj:
            # Configure the mock to return a model instance
            class TestModel(Adaptable, BaseModel):
                id: int
                name: str
                value: float

            expected_model = TestModel(id=1, name="test", value=42.5)
            mock_from_obj.return_value = [expected_model]

            # Register the adapter
            TestModel.register_adapter(AsyncPostgresAdapter)

            # Test from_obj with PostgreSQL DSN that needs conversion
            await TestModel.adapt_from(
                {"table": "test_table"},
                obj_key="async_pg",
                dsn="postgresql://user:pass@localhost/db",
            )

            # Verify the parent method was called with the converted DSN
            call_args = mock_from_obj.call_args[0][1]
            assert (
                call_args["engine_url"] == "postgresql+asyncpg://user:pass@localhost/db"
            )

    @pytest.mark.asyncio
    async def test_async_postgres_from_obj_with_already_converted_dsn(self):
        """Test conversion from Async PostgreSQL record to model with already converted DSN."""
        # Setup mocks for the parent class method
        with patch(
            "pydapter.extras.async_postgres_.AsyncSQLAdapter.from_obj", AsyncMock()
        ) as mock_from_obj:
            # Configure the mock to return a model instance
            class TestModel(Adaptable, BaseModel):
                id: int
                name: str
                value: float

            expected_model = TestModel(id=1, name="test", value=42.5)
            mock_from_obj.return_value = [expected_model]

            # Register the adapter
            TestModel.register_adapter(AsyncPostgresAdapter)

            # Test from_obj with already converted PostgreSQL DSN
            await TestModel.adapt_from(
                {"table": "test_table"},
                obj_key="async_pg",
                dsn="postgresql+asyncpg://user:pass@localhost/db",
            )

            # Verify the parent method was called with the unchanged DSN
            call_args = mock_from_obj.call_args[0][1]
            assert (
                call_args["engine_url"] == "postgresql+asyncpg://user:pass@localhost/db"
            )

    @pytest.mark.asyncio
    async def test_async_postgres_from_obj_with_default_dsn(self):
        """Test conversion from Async PostgreSQL record to model with default DSN."""
        # Setup mocks for the parent class method
        with patch(
            "pydapter.extras.async_postgres_.AsyncSQLAdapter.from_obj", AsyncMock()
        ) as mock_from_obj:
            # Configure the mock to return a model instance
            class TestModel(Adaptable, BaseModel):
                id: int
                name: str
                value: float

            expected_model = TestModel(id=1, name="test", value=42.5)
            mock_from_obj.return_value = [expected_model]

            # Register the adapter
            TestModel.register_adapter(AsyncPostgresAdapter)

            # Test from_obj without providing a DSN (should use default)
            await TestModel.adapt_from({"table": "test_table"}, obj_key="async_pg")

            # Verify the parent method was called with the default DSN
            call_args = mock_from_obj.call_args[0][1]
            assert call_args["engine_url"] == AsyncPostgresAdapter.DEFAULT

    @pytest.mark.asyncio
    async def test_async_postgres_to_obj_with_dsn_conversion(
        self, async_postgres_sample
    ):
        """Test conversion from model to Async PostgreSQL record with DSN conversion."""
        # Setup mocks for the parent class method
        with patch(
            "pydapter.extras.async_postgres_.AsyncSQLAdapter.to_obj", AsyncMock()
        ) as mock_to_obj:
            # Test to_obj with PostgreSQL DSN that needs conversion
            await async_postgres_sample.adapt_to(
                obj_key="async_pg",
                dsn="postgresql://user:pass@localhost/db",
                table="test_table",
            )

            # Verify the parent method was called with the converted DSN
            call_kwargs = mock_to_obj.call_args[1]
            assert (
                call_kwargs["engine_url"]
                == "postgresql+asyncpg://user:pass@localhost/db"
            )
            assert call_kwargs["table"] == "test_table"

    @pytest.mark.asyncio
    async def test_async_postgres_to_obj_with_already_converted_dsn(
        self, async_postgres_sample
    ):
        """Test conversion from model to Async PostgreSQL record with already converted DSN."""
        # Setup mocks for the parent class method
        with patch(
            "pydapter.extras.async_postgres_.AsyncSQLAdapter.to_obj", AsyncMock()
        ) as mock_to_obj:
            # Test to_obj with already converted PostgreSQL DSN
            await async_postgres_sample.adapt_to(
                obj_key="async_pg",
                dsn="postgresql+asyncpg://user:pass@localhost/db",
                table="test_table",
            )

            # Verify the parent method was called with the unchanged DSN
            call_kwargs = mock_to_obj.call_args[1]
            assert (
                call_kwargs["engine_url"]
                == "postgresql+asyncpg://user:pass@localhost/db"
            )
            assert call_kwargs["table"] == "test_table"

    @pytest.mark.asyncio
    async def test_async_postgres_to_obj_with_default_dsn(self, async_postgres_sample):
        """Test conversion from model to Async PostgreSQL record with default DSN."""
        # Setup mocks for the parent class method
        with patch(
            "pydapter.extras.async_postgres_.AsyncSQLAdapter.to_obj", AsyncMock()
        ) as mock_to_obj:
            # Test to_obj without providing a DSN (should use default)
            await async_postgres_sample.adapt_to(obj_key="async_pg", table="test_table")

            # Verify the parent method was called with the default DSN
            call_kwargs = mock_to_obj.call_args[1]
            assert call_kwargs["engine_url"] == AsyncPostgresAdapter.DEFAULT
            assert call_kwargs["table"] == "test_table"

    @pytest.mark.asyncio
    async def test_async_postgres_to_obj_multiple_items(self):
        """Test conversion from multiple models to Async PostgreSQL records."""

        # Create test models
        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        model1 = TestModel(id=1, name="test1", value=42.5)
        model2 = TestModel(id=2, name="test2", value=43.5)
        models = [model1, model2]

        # Setup mocks for the parent class method
        with patch(
            "pydapter.extras.async_postgres_.AsyncSQLAdapter.to_obj", AsyncMock()
        ) as mock_to_obj:
            # Register the adapter
            TestModel.register_adapter(AsyncPostgresAdapter)

            # Directly test the adapter's to_obj method with multiple items
            await AsyncPostgresAdapter.to_obj(
                models, dsn="postgresql://user:pass@localhost/db", table="test_table"
            )

            # Verify the parent method was called with the correct arguments
            call_args = mock_to_obj.call_args
            assert (
                call_args[0][0] == models
            )  # First positional arg should be the models list
            assert (
                call_args[1]["engine_url"]
                == "postgresql+asyncpg://user:pass@localhost/db"
            )
            assert call_args[1]["table"] == "test_table"
