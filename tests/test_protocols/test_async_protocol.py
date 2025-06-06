"""
Tests for async protocol compliance and functionality.
"""

from unittest.mock import AsyncMock

import pytest
from pydantic import BaseModel
from pydapter.async_core import AsyncAdaptable, AsyncAdapterRegistry


class MockAsyncAdapter:
    """Mock async adapter for testing."""

    obj_key = "mock_async"

    @classmethod
    async def from_obj(cls, subj_cls, obj, /, *, many=False, **kw):
        """Convert from object to model asynchronously."""
        if many:
            return [
                subj_cls(id=item["id"], name=item["name"], value=item["value"])
                for item in obj
            ]
        return subj_cls(id=obj["id"], name=obj["name"], value=obj["value"])

    @classmethod
    async def to_obj(cls, subj, /, *, many=False, **kw):
        """Convert from model to object asynchronously."""
        if many:
            return [
                {"id": item.id, "name": item.name, "value": item.value} for item in subj
            ]
        return {"id": subj.id, "name": subj.name, "value": subj.value}


@pytest.fixture
def async_model_class():
    """Create an async model class for testing."""

    class TestAsyncModel(AsyncAdaptable, BaseModel):
        id: int
        name: str
        value: float

    return TestAsyncModel


@pytest.fixture
def async_sample_model(async_model_class):
    """Create a sample async model instance."""
    return async_model_class(id=1, name="test", value=42.5)


class TestAsyncAdapterProtocol:
    """Tests for AsyncAdapter protocol functionality."""

    @pytest.mark.asyncio
    async def test_async_adapter_methods(self):
        """Test that AsyncAdapter methods work correctly."""

        # Create a model class
        class TestModel(BaseModel):
            id: int
            name: str
            value: float

        # Test from_obj
        obj = {"id": 1, "name": "test", "value": 42.5}
        model = await MockAsyncAdapter.from_obj(TestModel, obj)
        assert isinstance(model, TestModel)
        assert model.id == 1
        assert model.name == "test"
        assert model.value == 42.5

        # Test to_obj
        result = await MockAsyncAdapter.to_obj(model)
        assert isinstance(result, dict)
        assert result["id"] == 1
        assert result["name"] == "test"
        assert result["value"] == 42.5


class TestAsyncAdapterRegistryFunctionality:
    """Tests for AsyncAdapterRegistry functionality."""

    @pytest.mark.asyncio
    async def test_async_registry_convenience_methods(self):
        """Test convenience methods in AsyncAdapterRegistry."""
        registry = AsyncAdapterRegistry()
        registry.register(MockAsyncAdapter)

        # Create a test model
        class TestModel(BaseModel):
            id: int
            name: str
            value: float

        # Test adapt_from
        obj = {"id": 1, "name": "test", "value": 42.5}
        model = await registry.adapt_from(TestModel, obj, obj_key="mock_async")
        assert isinstance(model, TestModel)
        assert model.id == 1
        assert model.name == "test"
        assert model.value == 42.5

        # Test adapt_to
        result = await registry.adapt_to(model, obj_key="mock_async")
        assert isinstance(result, dict)
        assert result["id"] == 1
        assert result["name"] == "test"
        assert result["value"] == 42.5


class TestAsyncAdaptableFunctionality:
    """Tests for AsyncAdaptable mixin functionality."""

    @pytest.mark.asyncio
    async def test_async_adaptable_convenience_methods(
        self, async_model_class, async_sample_model
    ):
        """Test convenience methods in AsyncAdaptable mixin."""
        # Register adapter
        async_model_class.register_async_adapter(MockAsyncAdapter)

        # Test adapt_to_async
        result = await async_sample_model.adapt_to_async(obj_key="mock_async")
        assert isinstance(result, dict)
        assert result["id"] == 1
        assert result["name"] == "test"
        assert result["value"] == 42.5

        # Test adapt_from_async
        model = await async_model_class.adapt_from_async(result, obj_key="mock_async")
        assert isinstance(model, async_model_class)
        assert model.id == 1
        assert model.name == "test"
        assert model.value == 42.5


class TestAsyncMocking:
    """Tests for mocking async adapters."""

    @pytest.mark.asyncio
    async def test_async_adapter_mocking(self, async_model_class, async_sample_model):
        """Test mocking of async adapters."""
        # Create a mock adapter
        mock_adapter = AsyncMock()
        mock_adapter.obj_key = "mock"
        mock_adapter.from_obj = AsyncMock(return_value=async_sample_model)
        mock_adapter.to_obj = AsyncMock(
            return_value={"id": 1, "name": "test", "value": 42.5}
        )

        # Register the mock adapter
        async_model_class._areg()._reg["mock"] = mock_adapter

        # Test adapt_from_async
        result = await async_model_class.adapt_from_async({"id": 1}, obj_key="mock")
        assert result == async_sample_model
        mock_adapter.from_obj.assert_awaited_once()

        # Test adapt_to_async
        obj = await async_sample_model.adapt_to_async(obj_key="mock")
        assert obj == {"id": 1, "name": "test", "value": 42.5}
        mock_adapter.to_obj.assert_awaited_once()


class TestAsyncErrorHandling:
    """Tests for async error handling."""

    @pytest.mark.asyncio
    async def test_async_adapter_error_handling(self, async_model_class):
        """Test error handling in async adapters."""
        # Create a mock adapter that raises an exception
        mock_adapter = AsyncMock()
        mock_adapter.obj_key = "error"
        mock_adapter.from_obj = AsyncMock(side_effect=ValueError("Test error"))
        mock_adapter.to_obj = AsyncMock(side_effect=ValueError("Test error"))

        # Register the mock adapter
        async_model_class._areg()._reg["error"] = mock_adapter

        # Test adapt_from_async
        with pytest.raises(ValueError, match="Test error"):
            await async_model_class.adapt_from_async({"id": 1}, obj_key="error")

        # Test adapt_to_async
        sample = async_model_class(id=1, name="test", value=42.5)
        with pytest.raises(ValueError, match="Test error"):
            await sample.adapt_to_async(obj_key="error")


@pytest.mark.asyncio
async def test_async_adapter_with_context_manager():
    """Test async adapter with context manager."""

    # Create a mock context manager
    class MockAsyncContextManager:
        async def __aenter__(self):
            return {"id": 1, "name": "test", "value": 42.5}

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    # Create a mock adapter that uses the context manager
    class ContextManagerAdapter:
        obj_key = "context"

        @classmethod
        async def from_obj(cls, subj_cls, obj, /, *, many=False, **kw):
            async with MockAsyncContextManager() as result:
                if many:
                    return [subj_cls(**result) for _ in range(2)]
                return subj_cls(**result)

        @classmethod
        async def to_obj(cls, subj, /, *, many=False, **kw):
            async with MockAsyncContextManager() as result:
                return result

    # Create a model class
    class TestModel(AsyncAdaptable, BaseModel):
        id: int
        name: str
        value: float

    # Register the adapter
    TestModel.register_async_adapter(ContextManagerAdapter)

    # Test adapt_from_async
    model = await TestModel.adapt_from_async({}, obj_key="context")
    assert isinstance(model, TestModel)
    assert model.id == 1
    assert model.name == "test"
    assert model.value == 42.5

    # Test adapt_to_async
    result = await model.adapt_to_async(obj_key="context")
    assert isinstance(result, dict)
    assert result["id"] == 1
    assert result["name"] == "test"
    assert result["value"] == 42.5
