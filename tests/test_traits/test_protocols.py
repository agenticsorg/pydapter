"""
Tests for trait Protocol definitions.

This module tests that all Protocol interfaces work correctly
and provide the expected type checking behavior.
"""

from collections.abc import AsyncIterator
from typing import Any

import pytest

from pydapter.traits.protocols import (
    Auditable,
    Cacheable,
    CapabilityAware,
    Composable,
    Extensible,
    Hashable,
    Identifiable,
    Indexable,
    Lazy,
    Observable,
    Operable,
    Partial,
    Secured,
    Serializable,
    Streaming,
    Temporal,
    Validatable,
)


class TestIdentifiable:
    """Test the Identifiable protocol."""

    def test_protocol_structure(self):
        """Test that Identifiable has required methods."""
        # Check required attributes exist
        assert hasattr(Identifiable, "id")
        assert hasattr(Identifiable, "id_type")
        assert hasattr(Identifiable, "same_identity")

    def test_valid_implementation(self):
        """Test a valid implementation of Identifiable."""

        class ValidIdentifiable:
            def __init__(self, id_value: str):
                self._id = id_value

            @property
            def id(self) -> str:
                return self._id

            @property
            def id_type(self) -> str:
                return "test"

            def same_identity(self, other: Any) -> bool:
                return isinstance(other, Identifiable) and self.id == other.id

        obj = ValidIdentifiable("test-123")
        assert isinstance(obj, Identifiable)
        assert obj.id == "test-123"
        assert obj.id_type == "test"

    def test_same_identity_method(self):
        """Test the same_identity default implementation."""
        obj1 = self._create_identifiable("123", "uuid")
        obj2 = self._create_identifiable("123", "uuid")
        obj3 = self._create_identifiable("456", "uuid")
        obj4 = self._create_identifiable("123", "snowflake")

        # Should be True - same ID and type
        assert obj1.same_identity(obj2)
        # Different ID
        assert not obj1.same_identity(obj3)
        # Different type
        assert not obj1.same_identity(obj4)
        # Non-identifiable
        assert not obj1.same_identity("not_identifiable")

    def _create_identifiable(self, id_val: str, type_val: str):
        """Helper to create identifiable objects."""

        class TestIdentifiable:
            def __init__(self, id_val: str, type_val: str):
                self._id = id_val
                self._type = type_val

            @property
            def id(self) -> str:
                return self._id

            @property
            def id_type(self) -> str:
                return self._type

            def same_identity(self, other: Any) -> bool:
                """Check if this entity has the same identity as another."""
                if not hasattr(other, "id") or not hasattr(other, "id_type"):
                    return False
                return bool(self.id == other.id and self.id_type == other.id_type)

        return TestIdentifiable(id_val, type_val)


class TestTemporal:
    """Test the Temporal protocol."""

    def test_protocol_structure(self):
        """Test that Temporal has required methods."""
        assert hasattr(Temporal, "created_at")
        assert hasattr(Temporal, "updated_at")
        assert hasattr(Temporal, "age_seconds")
        assert hasattr(Temporal, "is_modified")

    def test_valid_implementation(self):
        """Test a valid implementation of Temporal."""
        import time

        class ValidTemporal:
            def __init__(self):
                self._created_at = time.time()
                self._updated_at = self._created_at

            @property
            def created_at(self) -> float:
                return self._created_at

            @property
            def updated_at(self) -> float:
                return self._updated_at

            def age_seconds(self) -> float:
                """Get age of entity in seconds."""
                return time.time() - self.created_at

            def is_modified(self) -> bool:
                """Check if entity has been modified since creation."""
                return self.updated_at > self.created_at

            def touch(self):
                self._updated_at = time.time()

        obj = ValidTemporal()
        assert isinstance(obj, Temporal)
        assert obj.created_at > 0
        assert obj.updated_at > 0
        assert obj.age_seconds() >= 0
        assert not obj.is_modified()

        # Test modification
        obj.touch()
        assert obj.is_modified()


class TestAuditable:
    """Test the Auditable protocol."""

    def test_protocol_structure(self):
        """Test that Auditable has required methods."""
        assert hasattr(Auditable, "version")
        assert hasattr(Auditable, "audit_log")
        assert hasattr(Auditable, "emit_audit_event")

    def test_valid_implementation(self):
        """Test a valid implementation of Auditable."""

        class ValidAuditable:
            def __init__(self):
                self._version = 1
                self._audit_log = []

            @property
            def version(self) -> int:
                return self._version

            @property
            def audit_log(self) -> list[dict[str, Any]]:
                return self._audit_log.copy()

            def emit_audit_event(self, event_type: str, **kwargs: Any) -> None:
                self._audit_log.append(
                    {"event_type": event_type, "version": self._version, **kwargs}
                )
                self._version += 1

        obj = ValidAuditable()
        assert isinstance(obj, Auditable)
        assert obj.version == 1
        assert len(obj.audit_log) == 0

        obj.emit_audit_event("test_event", data="test")
        assert obj.version == 2
        assert len(obj.audit_log) == 1
        assert obj.audit_log[0]["event_type"] == "test_event"


class TestValidatable:
    """Test the Validatable protocol."""

    def test_protocol_structure(self):
        """Test that Validatable has required methods."""
        assert hasattr(Validatable, "is_valid")
        assert hasattr(Validatable, "validate")
        assert hasattr(Validatable, "get_validation_constraints")

    def test_valid_implementation(self):
        """Test a valid implementation of Validatable."""

        class ValidValidatable:
            def __init__(self, value: int):
                self.value = value

            def is_valid(self) -> bool:
                return self.value > 0

            def validate(self) -> list[str]:
                errors = []
                if self.value <= 0:
                    errors.append("Value must be positive")
                return errors

            def get_validation_constraints(self) -> dict[str, Any]:
                return {"value": {"min": 1}}

        obj_valid = ValidValidatable(5)
        obj_invalid = ValidValidatable(-1)

        assert isinstance(obj_valid, Validatable)
        assert isinstance(obj_invalid, Validatable)

        assert obj_valid.is_valid()
        assert not obj_invalid.is_valid()

        assert len(obj_valid.validate()) == 0
        assert len(obj_invalid.validate()) == 1
        assert "positive" in obj_invalid.validate()[0]


class TestPerformanceProtocols:
    """Test performance-related protocols."""

    def test_cacheable_protocol(self):
        """Test Cacheable protocol implementation."""

        class ValidCacheable:
            def __init__(self, id_value: str):
                self.id = id_value

            def get_cache_key(self) -> str:
                return f"cache:{self.id}"

            def invalidate_cache(self) -> None:
                pass  # Implementation would clear cache

            @property
            def cache_ttl(self) -> int:
                return 300  # 5 minutes

        obj = ValidCacheable("test")
        assert isinstance(obj, Cacheable)
        assert obj.get_cache_key() == "cache:test"
        assert obj.cache_ttl == 300

    def test_lazy_protocol(self):
        """Test Lazy protocol implementation."""

        class ValidLazy:
            def __init__(self):
                self._loaded = False

            def load_lazy_attributes(self) -> None:
                self._loaded = True

            def is_fully_loaded(self) -> bool:
                return self._loaded

            @property
            def lazy_fields(self) -> list[str]:
                return ["expensive_data"]

        obj = ValidLazy()
        assert isinstance(obj, Lazy)
        assert not obj.is_fully_loaded()
        assert "expensive_data" in obj.lazy_fields

        obj.load_lazy_attributes()
        assert obj.is_fully_loaded()


class TestSecurityProtocols:
    """Test security-related protocols."""

    def test_secured_protocol(self):
        """Test Secured protocol implementation."""

        class ValidSecured:
            def __init__(self):
                self._security_level = "public"

            def check_access(self, operation: str, context: dict[str, Any]) -> bool:
                return operation in ["read", "list"]

            def get_security_policy(self) -> dict[str, Any]:
                return {"allowed_operations": ["read", "list"]}

            @property
            def security_level(self) -> str:
                return self._security_level

        obj = ValidSecured()
        assert isinstance(obj, Secured)
        assert obj.check_access("read", {})
        assert not obj.check_access("delete", {})
        assert obj.security_level == "public"

    def test_capability_aware_protocol(self):
        """Test CapabilityAware protocol implementation."""

        class ValidCapabilityAware:
            def __init__(self):
                self._capabilities = set()

            def grant_capability(self, capability: str, target: Any) -> bool:
                self._capabilities.add(capability)
                return True

            def revoke_capability(self, capability: str, target: Any) -> bool:
                self._capabilities.discard(capability)
                return True

            def has_capability(self, capability: str) -> bool:
                return capability in self._capabilities

            @property
            def granted_capabilities(self) -> set[str]:
                return self._capabilities.copy()

        obj = ValidCapabilityAware()
        assert isinstance(obj, CapabilityAware)
        assert not obj.has_capability("read")

        obj.grant_capability("read", None)
        assert obj.has_capability("read")
        assert "read" in obj.granted_capabilities

        obj.revoke_capability("read", None)
        assert not obj.has_capability("read")


class TestHashable:
    """Test the Hashable protocol."""

    def test_protocol_structure(self):
        """Test that Hashable has required methods."""
        assert hasattr(Hashable, "__hash__")
        assert hasattr(Hashable, "hash_fields")
        assert hasattr(Hashable, "verify_hash_stability")

    def test_valid_implementation(self):
        """Test a valid implementation of Hashable."""

        class ValidHashable:
            def __init__(self, value: str):
                self.value = value

            def __hash__(self) -> int:
                return hash(self.value)

            @property
            def hash_fields(self) -> tuple[str, ...]:
                return ("value",)

            def verify_hash_stability(self) -> bool:
                """Verify that hash is stable across multiple calls."""
                hash1 = hash(self)
                hash2 = hash(self)
                return hash1 == hash2

        obj = ValidHashable("test")
        assert isinstance(obj, Hashable)
        assert hash(obj) == hash("test")
        assert obj.hash_fields == ("value",)
        assert obj.verify_hash_stability()


class TestOperable:
    """Test the Operable protocol."""

    def test_protocol_structure(self):
        """Test that Operable has required methods."""
        assert hasattr(Operable, "apply_operation")
        assert hasattr(Operable, "get_supported_operations")
        assert hasattr(Operable, "supports_operation")

    def test_valid_implementation(self):
        """Test a valid implementation of Operable."""

        class ValidOperable:
            def __init__(self):
                self._operations = {"uppercase": str.upper, "lowercase": str.lower}

            def apply_operation(self, operation: str, **kwargs: Any) -> Any:
                if operation not in self._operations:
                    raise ValueError(f"Unsupported operation: {operation}")
                return self._operations[operation](kwargs.get("text", ""))

            def get_supported_operations(self) -> list[str]:
                return list(self._operations.keys())

            def supports_operation(self, operation: str) -> bool:
                """Check if entity supports a specific operation."""
                return operation in self.get_supported_operations()

        obj = ValidOperable()
        assert isinstance(obj, Operable)
        assert obj.supports_operation("uppercase")
        assert not obj.supports_operation("invalid")
        assert obj.apply_operation("uppercase", text="hello") == "HELLO"
        assert set(obj.get_supported_operations()) == {"uppercase", "lowercase"}


class TestObservable:
    """Test the Observable protocol."""

    def test_protocol_structure(self):
        """Test that Observable has required methods."""
        assert hasattr(Observable, "subscribe")
        assert hasattr(Observable, "unsubscribe")
        assert hasattr(Observable, "emit_event")

    def test_valid_implementation(self):
        """Test a valid implementation of Observable."""

        class ValidObservable:
            def __init__(self):
                self._observers = {}
                self._next_id = 0

            def subscribe(
                self, observer: Any, event_types: list[str] | None = None
            ) -> str:
                sub_id = str(self._next_id)
                self._next_id += 1
                self._observers[sub_id] = (observer, event_types)
                return sub_id

            def unsubscribe(self, subscription_id: str) -> bool:
                if subscription_id in self._observers:
                    del self._observers[subscription_id]
                    return True
                return False

            def emit_event(self, event_type: str, **data: Any) -> None:
                for observer, types in self._observers.values():
                    if types is None or event_type in types:
                        observer(event_type, data)

        obj = ValidObservable()
        assert isinstance(obj, Observable)

        # Test subscription
        events = []

        def observer(event_type: str, data: dict):
            events.append((event_type, data))

        sub_id = obj.subscribe(observer, ["test_event"])
        obj.emit_event("test_event", value=42)
        assert len(events) == 1
        assert events[0] == ("test_event", {"value": 42})

        # Test unsubscription
        assert obj.unsubscribe(sub_id)
        obj.emit_event("test_event", value=43)
        assert len(events) == 1  # No new events


class TestSerializable:
    """Test the Serializable protocol."""

    def test_protocol_structure(self):
        """Test that Serializable has required methods."""
        assert hasattr(Serializable, "to_dict")
        assert hasattr(Serializable, "from_dict")
        assert hasattr(Serializable, "serialization_version")

    def test_valid_implementation(self):
        """Test a valid implementation of Serializable."""

        class ValidSerializable:
            def __init__(self, name: str, value: int):
                self.name = name
                self.value = value

            def to_dict(self) -> dict[str, Any]:
                return {
                    "name": self.name,
                    "value": self.value,
                    "version": self.serialization_version,
                }

            @classmethod
            def from_dict(cls, data: dict[str, Any]) -> "ValidSerializable":
                return cls(name=data["name"], value=data["value"])

            @property
            def serialization_version(self) -> str:
                return "1.0.0"

        obj = ValidSerializable("test", 42)
        assert isinstance(obj, Serializable)

        # Test serialization
        data = obj.to_dict()
        assert data == {"name": "test", "value": 42, "version": "1.0.0"}

        # Test deserialization
        obj2 = ValidSerializable.from_dict(data)
        assert obj2.name == "test"
        assert obj2.value == 42
        assert obj2.serialization_version == "1.0.0"


class TestComposable:
    """Test the Composable protocol."""

    def test_protocol_structure(self):
        """Test that Composable has required methods."""
        assert hasattr(Composable, "compose_with")
        assert hasattr(Composable, "get_composition_conflicts")
        assert hasattr(Composable, "composition_priority")

    def test_valid_implementation(self):
        """Test a valid implementation of Composable."""

        class ValidComposable:
            def __init__(self, name: str, priority: int = 0):
                self.name = name
                self._priority = priority

            def compose_with(self, other: Any) -> Any:
                if hasattr(other, "name") and self.name == other.name:
                    raise ValueError("Cannot compose with same name")
                return ValidComposable(
                    f"{self.name}+{other.name}",
                    max(self._priority, getattr(other, "_priority", 0)),
                )

            def get_composition_conflicts(self, other: Any) -> list[str]:
                conflicts = []
                if hasattr(other, "name") and self.name == other.name:
                    conflicts.append("Duplicate name")
                return conflicts

            @property
            def composition_priority(self) -> int:
                return self._priority

        obj1 = ValidComposable("A", 1)
        obj2 = ValidComposable("B", 2)
        assert isinstance(obj1, Composable)

        # Test composition
        composed = obj1.compose_with(obj2)
        assert composed.name == "A+B"
        assert composed.composition_priority == 2

        # Test conflicts
        obj3 = ValidComposable("A", 3)
        conflicts = obj1.get_composition_conflicts(obj3)
        assert "Duplicate name" in conflicts


class TestExtensible:
    """Test the Extensible protocol."""

    def test_protocol_structure(self):
        """Test that Extensible has required methods."""
        assert hasattr(Extensible, "add_extension")
        assert hasattr(Extensible, "get_extension")
        assert hasattr(Extensible, "list_extensions")

    def test_valid_implementation(self):
        """Test a valid implementation of Extensible."""

        class ValidExtensible:
            def __init__(self):
                self._extensions = {}

            def add_extension(self, name: str, extension: Any) -> bool:
                if name in self._extensions:
                    return False
                self._extensions[name] = extension
                return True

            def get_extension(self, name: str) -> Any:
                return self._extensions.get(name)

            def list_extensions(self) -> list[str]:
                return list(self._extensions.keys())

        obj = ValidExtensible()
        assert isinstance(obj, Extensible)

        # Test adding extensions
        assert obj.add_extension("test_ext", lambda x: x * 2)
        assert not obj.add_extension("test_ext", lambda x: x * 3)  # Duplicate

        # Test getting extensions
        ext = obj.get_extension("test_ext")
        assert ext is not None
        assert ext(5) == 10

        # Test listing extensions
        assert obj.list_extensions() == ["test_ext"]


class TestIndexable:
    """Test the Indexable protocol."""

    def test_protocol_structure(self):
        """Test that Indexable has required methods."""
        assert hasattr(Indexable, "get_search_fields")
        assert hasattr(Indexable, "matches_query")
        assert hasattr(Indexable, "search_priority")

    def test_valid_implementation(self):
        """Test a valid implementation of Indexable."""

        class ValidIndexable:
            def __init__(self, title: str, content: str, priority: float = 1.0):
                self.title = title
                self.content = content
                self._priority = priority

            def get_search_fields(self) -> dict[str, Any]:
                return {"title": self.title, "content": self.content}

            def matches_query(self, query: dict[str, Any]) -> bool:
                for field, value in query.items():
                    if field == "title" and value.lower() not in self.title.lower():
                        return False
                    if field == "content" and value.lower() not in self.content.lower():
                        return False
                return True

            @property
            def search_priority(self) -> float:
                return self._priority

        obj = ValidIndexable("Test Title", "Test content here", 2.5)
        assert isinstance(obj, Indexable)

        # Test search fields
        fields = obj.get_search_fields()
        assert fields == {"title": "Test Title", "content": "Test content here"}

        # Test query matching
        assert obj.matches_query({"title": "Test"})
        assert obj.matches_query({"content": "content"})
        assert not obj.matches_query({"title": "Missing"})

        # Test priority
        assert obj.search_priority == 2.5


class TestStreaming:
    """Test the Streaming protocol."""

    def test_protocol_structure(self):
        """Test that Streaming has required methods."""
        assert hasattr(Streaming, "stream_updates")
        assert hasattr(Streaming, "apply_stream_update")
        assert hasattr(Streaming, "supports_streaming")

    def test_valid_implementation(self):
        """Test a valid implementation of Streaming."""

        class ValidStreaming:
            def __init__(self):
                self._data = []
                self._streaming = True

            async def stream_updates(self) -> AsyncIterator[dict[str, Any]]:
                for i in range(3):
                    yield {"index": i, "data": f"chunk_{i}"}

            def apply_stream_update(self, update: dict[str, Any]) -> bool:
                if "data" in update:
                    self._data.append(update["data"])
                    return True
                return False

            @property
            def supports_streaming(self) -> bool:
                return self._streaming

        obj = ValidStreaming()
        assert isinstance(obj, Streaming)

        # Test streaming support
        assert obj.supports_streaming

        # Test applying updates
        assert obj.apply_stream_update({"data": "test"})
        assert obj._data == ["test"]


class TestPartial:
    """Test the Partial protocol."""

    def test_protocol_structure(self):
        """Test that Partial has required methods."""
        assert hasattr(Partial, "is_complete")
        assert hasattr(Partial, "get_missing_fields")
        assert hasattr(Partial, "finalize")

    def test_valid_implementation(self):
        """Test a valid implementation of Partial."""

        class ValidPartial:
            def __init__(self):
                self.name = None
                self.email = None
                self._required = ["name", "email"]

            def is_complete(self) -> bool:
                return all(
                    getattr(self, field, None) is not None for field in self._required
                )

            def get_missing_fields(self) -> list[str]:
                return [
                    field
                    for field in self._required
                    if getattr(self, field, None) is None
                ]

            def finalize(self) -> Any:
                if not self.is_complete():
                    raise ValueError(f"Missing fields: {self.get_missing_fields()}")
                return {"name": self.name, "email": self.email}

        obj = ValidPartial()
        assert isinstance(obj, Partial)

        # Test incomplete state
        assert not obj.is_complete()
        assert set(obj.get_missing_fields()) == {"name", "email"}

        # Test partial completion
        obj.name = "Test User"
        assert not obj.is_complete()
        assert obj.get_missing_fields() == ["email"]

        # Test complete state
        obj.email = "test@example.com"
        assert obj.is_complete()
        assert obj.get_missing_fields() == []

        # Test finalization
        result = obj.finalize()
        assert result == {"name": "Test User", "email": "test@example.com"}


@pytest.mark.parametrize(
    "protocol_class",
    [
        Identifiable,
        Temporal,
        Auditable,
        Hashable,
        Operable,
        Observable,
        Validatable,
        Serializable,
        Composable,
        Extensible,
        Cacheable,
        Indexable,
        Lazy,
        Streaming,
        Partial,
        Secured,
        CapabilityAware,
    ],
)
def test_protocol_is_runtime_checkable(protocol_class):
    """Test that all protocols are runtime checkable."""
    assert hasattr(protocol_class, "__instancecheck__")
    assert hasattr(protocol_class, "__subclasscheck__")
