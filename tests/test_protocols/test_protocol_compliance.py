"""
Tests for protocol compliance of adapter implementations.
"""

import pytest
from pydapter.adapters import CsvAdapter, JsonAdapter, TomlAdapter
from pydapter.async_core import AsyncAdaptable, AsyncAdapterRegistry
from pydapter.core import Adaptable, AdapterRegistry
from pydapter.exceptions import AdapterNotFoundError, ConfigurationError
from pydapter.extras.async_mongo_ import AsyncMongoAdapter
from pydapter.extras.async_postgres_ import AsyncPostgresAdapter
from pydapter.extras.async_qdrant_ import AsyncQdrantAdapter


@pytest.fixture
def adapter_classes():
    """Return a list of concrete adapter classes."""
    return [JsonAdapter, CsvAdapter, TomlAdapter]


@pytest.fixture
def async_adapter_classes():
    """Return a list of concrete async adapter classes."""
    return [AsyncPostgresAdapter, AsyncMongoAdapter, AsyncQdrantAdapter]


class TestProtocolCompliance:
    """Tests for protocol compliance of adapter implementations."""

    @pytest.mark.parametrize("adapter_cls", [JsonAdapter, CsvAdapter, TomlAdapter])
    def test_adapter_protocol_compliance(self, adapter_cls):
        """Test that concrete adapters implement the Adapter protocol."""
        # We can't use issubclass with Protocols that have non-method members
        # Instead, verify the required attributes and methods directly
        assert hasattr(adapter_cls, "obj_key")
        assert isinstance(adapter_cls.obj_key, str)

        # Verify method signatures
        assert hasattr(adapter_cls, "from_obj")
        assert hasattr(adapter_cls, "to_obj")

        # Verify the methods can be called as classmethods
        # We can't directly check if they're classmethods because accessing them
        # from the class gives us the function, not the classmethod wrapper
        assert callable(adapter_cls.from_obj)
        assert callable(adapter_cls.to_obj)

    @pytest.mark.parametrize(
        "adapter_cls", [AsyncPostgresAdapter, AsyncMongoAdapter, AsyncQdrantAdapter]
    )
    def test_async_adapter_protocol_compliance(self, adapter_cls):
        """Test that concrete async adapters implement the AsyncAdapter protocol."""
        # We can't use issubclass with Protocols that have non-method members
        # Instead, verify the required attributes and methods directly
        assert hasattr(adapter_cls, "obj_key")
        assert isinstance(adapter_cls.obj_key, str)

        # Verify method signatures
        assert hasattr(adapter_cls, "from_obj")
        assert hasattr(adapter_cls, "to_obj")

        # Verify the methods can be called as classmethods
        # We can't directly check if they're classmethods because accessing them
        # from the class gives us the function, not the classmethod wrapper
        assert callable(adapter_cls.from_obj)
        assert callable(adapter_cls.to_obj)


class TestAdapterRegistry:
    """Tests for AdapterRegistry functionality."""

    def test_adapter_registry_init(self):
        """Test initialization of AdapterRegistry."""
        registry = AdapterRegistry()
        assert registry._reg == {}

    def test_adapter_registry_registration(self):
        """Test registration of adapters in the registry."""
        registry = AdapterRegistry()

        # Register adapters
        registry.register(JsonAdapter)
        registry.register(CsvAdapter)
        registry.register(TomlAdapter)

        # Verify adapters are registered
        assert registry.get("json") == JsonAdapter
        assert registry.get("csv") == CsvAdapter
        assert registry.get("toml") == TomlAdapter

    def test_adapter_registry_error_handling(self):
        """Test error handling in AdapterRegistry."""
        registry = AdapterRegistry()

        # Test invalid adapter (missing obj_key)
        class InvalidAdapter:
            pass

        with pytest.raises(ConfigurationError, match="Adapter must define 'obj_key'"):
            registry.register(InvalidAdapter)

        # Test retrieval of unregistered adapter
        with pytest.raises(
            AdapterNotFoundError, match="No adapter registered for 'nonexistent'"
        ):
            registry.get("nonexistent")

    def test_adapter_registry_convenience_methods(self):
        """Test convenience methods in AdapterRegistry."""
        registry = AdapterRegistry()
        registry.register(JsonAdapter)

        # Create a test model
        from pydantic import BaseModel

        class TestModel(BaseModel):
            id: int
            name: str
            value: float

        # Test adapt_from
        model = registry.adapt_from(
            TestModel, '{"id": 1, "name": "test", "value": 42.5}', obj_key="json"
        )
        assert isinstance(model, TestModel)
        assert model.id == 1
        assert model.name == "test"
        assert model.value == 42.5

        # Test adapt_to
        obj = registry.adapt_to(model, obj_key="json")
        assert isinstance(obj, str)
        assert '"id": 1' in obj
        assert '"name": "test"' in obj
        assert '"value": 42.5' in obj


class TestAsyncAdapterRegistry:
    """Tests for AsyncAdapterRegistry functionality."""

    def test_async_adapter_registry_init(self):
        """Test initialization of AsyncAdapterRegistry."""
        registry = AsyncAdapterRegistry()
        assert registry._reg == {}

    def test_async_adapter_registry_registration(self):
        """Test registration of async adapters in the registry."""
        registry = AsyncAdapterRegistry()

        # Register adapters
        registry.register(AsyncPostgresAdapter)
        registry.register(AsyncMongoAdapter)
        registry.register(AsyncQdrantAdapter)

        # Verify adapters are registered
        assert registry.get("async_pg") == AsyncPostgresAdapter
        assert registry.get("async_mongo") == AsyncMongoAdapter
        assert registry.get("async_qdrant") == AsyncQdrantAdapter

    def test_async_adapter_registry_error_handling(self):
        """Test error handling in AsyncAdapterRegistry."""
        registry = AsyncAdapterRegistry()

        # Test invalid adapter (missing obj_key)
        class InvalidAdapter:
            pass

        with pytest.raises(
            ConfigurationError, match="AsyncAdapter must define 'obj_key'"
        ):
            registry.register(InvalidAdapter)

        # Test retrieval of unregistered adapter
        with pytest.raises(
            AdapterNotFoundError, match="No async adapter for 'nonexistent'"
        ):
            registry.get("nonexistent")


class TestAdaptableMixin:
    """Tests for Adaptable mixin functionality."""

    def test_adaptable_registry(self):
        """Test registry access in Adaptable mixin."""
        from pydantic import BaseModel

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        # Verify registry is created
        registry = TestModel._registry()
        assert isinstance(registry, AdapterRegistry)

        # Verify registry is cached
        assert TestModel._registry() is registry

    def test_adaptable_registration(self):
        """Test adapter registration in Adaptable mixin."""
        from pydantic import BaseModel

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        # Register adapters
        TestModel.register_adapter(JsonAdapter)
        TestModel.register_adapter(CsvAdapter)

        # Verify adapters are registered
        registry = TestModel._registry()
        assert registry.get("json") == JsonAdapter
        assert registry.get("csv") == CsvAdapter

    def test_adaptable_convenience_methods(self):
        """Test convenience methods in Adaptable mixin."""
        from pydantic import BaseModel

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        # Register adapter
        TestModel.register_adapter(JsonAdapter)

        # Create instance
        instance = TestModel(id=1, name="test", value=42.5)

        # Test adapt_to
        obj = instance.adapt_to(obj_key="json")
        assert isinstance(obj, str)
        assert '"id": 1' in obj
        assert '"name": "test"' in obj
        assert '"value": 42.5' in obj

        # Test adapt_from
        model = TestModel.adapt_from(obj, obj_key="json")
        assert isinstance(model, TestModel)
        assert model.id == 1
        assert model.name == "test"
        assert model.value == 42.5


class TestAsyncAdaptableMixin:
    """Tests for AsyncAdaptable mixin functionality."""

    def test_async_adaptable_registry(self):
        """Test registry access in AsyncAdaptable mixin."""
        from pydantic import BaseModel

        class TestModel(AsyncAdaptable, BaseModel):
            id: int
            name: str
            value: float

        # Verify registry is created
        registry = TestModel._areg()
        assert isinstance(registry, AsyncAdapterRegistry)

        # Verify registry is cached
        assert TestModel._areg() is registry

    def test_async_adaptable_registration(self):
        """Test adapter registration in AsyncAdaptable mixin."""
        from pydantic import BaseModel

        class TestModel(AsyncAdaptable, BaseModel):
            id: int
            name: str
            value: float

        # Register adapters
        TestModel.register_async_adapter(AsyncPostgresAdapter)
        TestModel.register_async_adapter(AsyncMongoAdapter)

        # Verify adapters are registered
        registry = TestModel._areg()
        assert registry.get("async_pg") == AsyncPostgresAdapter
        assert registry.get("async_mongo") == AsyncMongoAdapter
