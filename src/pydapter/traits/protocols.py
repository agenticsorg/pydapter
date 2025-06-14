"""
Protocol definitions for all LionAGI traits.

This module contains the Protocol interfaces that define the contract
for each trait. Protocols provide:

- Compile-time type checking with mypy
- Runtime type checking with isinstance()
- Zero overhead at runtime (145ns isinstance checks)
- Excellent IDE integration and autocomplete
- Best debugging experience (8/10 research score)

Each Protocol defines the minimal interface required to satisfy
the corresponding trait.
"""

from __future__ import annotations

from abc import abstractmethod
from collections.abc import AsyncIterator
from typing import Any, Protocol, runtime_checkable

__all__ = [
    "Auditable",
    "Cacheable",
    "CapabilityAware",
    "Composable",
    "Extensible",
    "Hashable",
    "Identifiable",
    "Indexable",
    "Lazy",
    "Observable",
    "Operable",
    "Partial",
    "Secured",
    "Serializable",
    "Streaming",
    "Temporal",
    "Validatable",
]


@runtime_checkable
class Identifiable(Protocol):
    """
    Protocol for entities that have a unique identity.

    This is the most fundamental trait, providing stable identity
    across the system. All identified entities can be compared,
    referenced, and tracked.
    """

    @property
    @abstractmethod
    def id(self) -> str:
        """Unique identifier for this entity."""
        ...

    @property
    @abstractmethod
    def id_type(self) -> str:
        """Type/namespace of the identifier (e.g., 'uuid', 'snowflake')."""
        ...

    def same_identity(self, other: Any) -> bool:
        """Check if this entity has the same identity as another."""
        if not hasattr(other, "id") or not hasattr(other, "id_type"):
            return False
        return bool(self.id == other.id and self.id_type == other.id_type)


@runtime_checkable
class Temporal(Protocol):
    """
    Protocol for entities that track temporal information.

    Provides creation and modification timestamps with
    timezone awareness.
    """

    @property
    @abstractmethod
    def created_at(self) -> float:
        """Unix timestamp when entity was created."""
        ...

    @property
    @abstractmethod
    def updated_at(self) -> float:
        """Unix timestamp when entity was last updated."""
        ...

    def age_seconds(self) -> float:
        """Get age of entity in seconds."""
        import time

        return time.time() - self.created_at

    def is_modified(self) -> bool:
        """Check if entity has been modified since creation."""
        return self.updated_at > self.created_at


@runtime_checkable
class Auditable(Protocol):
    """
    Protocol for entities that emit audit events.

    Extends Temporal with comprehensive change tracking
    and event emission capabilities.
    """

    @property
    @abstractmethod
    def version(self) -> int:
        """Version number, incremented on each change."""
        ...

    @property
    @abstractmethod
    def audit_log(self) -> list[dict[str, Any]]:
        """Audit log entries for this entity."""
        ...

    @abstractmethod
    def emit_audit_event(self, event_type: str, **kwargs: Any) -> None:
        """Emit an audit event for tracking changes."""
        ...


@runtime_checkable
class Hashable(Protocol):
    """
    Protocol for entities that provide stable hashing.

    Ensures hash stability across sessions and processes
    for use in sets, dictionaries, and caching.
    """

    @abstractmethod
    def __hash__(self) -> int:  # type: ignore[explicit-override]
        """Stable hash value for this entity."""
        ...

    @property
    @abstractmethod
    def hash_fields(self) -> tuple[str, ...]:
        """Fields used in hash computation."""
        ...

    def verify_hash_stability(self) -> bool:
        """Verify that hash is stable across multiple calls."""
        hash1 = hash(self)
        hash2 = hash(self)
        return hash1 == hash2


@runtime_checkable
class Operable(Protocol):
    """
    Protocol for entities that support operations and transformations.

    Provides a framework for applying operations while
    maintaining type safety and error handling.
    """

    @abstractmethod
    def apply_operation(self, operation: str, **kwargs: Any) -> Any:
        """Apply a named operation to this entity."""
        ...

    @abstractmethod
    def get_supported_operations(self) -> list[str]:
        """Get list of supported operation names."""
        ...

    def supports_operation(self, operation: str) -> bool:
        """Check if entity supports a specific operation."""
        return operation in self.get_supported_operations()


@runtime_checkable
class Observable(Protocol):
    """
    Protocol for entities that emit events for state changes.

    Provides observer pattern implementation with
    type-safe event handling.
    """

    @abstractmethod
    def subscribe(self, observer: Any, event_types: list[str] | None = None) -> str:
        """Subscribe to events. Returns subscription ID."""
        ...

    @abstractmethod
    def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from events."""
        ...

    @abstractmethod
    def emit_event(self, event_type: str, **data: Any) -> None:
        """Emit an event to all subscribers."""
        ...


@runtime_checkable
class Validatable(Protocol):
    """
    Protocol for entities that support validation.

    Provides comprehensive validation with detailed
    error reporting and constraint checking.
    """

    @abstractmethod
    def is_valid(self) -> bool:
        """Check if entity is currently valid."""
        ...

    @abstractmethod
    def validate(self) -> list[str]:
        """Validate entity and return list of error messages."""
        ...

    @abstractmethod
    def get_validation_constraints(self) -> dict[str, Any]:
        """Get validation constraints for this entity."""
        ...


@runtime_checkable
class Serializable(Protocol):
    """
    Protocol for entities that can be serialized and deserialized.

    Supports multiple serialization formats with
    version compatibility.
    """

    @abstractmethod
    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        ...

    @classmethod
    @abstractmethod
    def from_dict(cls, data: dict[str, Any]) -> Any:
        """Deserialize from dictionary."""
        ...

    @property
    @abstractmethod
    def serialization_version(self) -> str:
        """Version string for serialization compatibility."""
        ...


@runtime_checkable
class Composable(Protocol):
    """
    Protocol for entities that can be composed with others.

    Enables trait composition and model merging with
    conflict resolution.
    """

    @abstractmethod
    def compose_with(self, other: Any) -> Any:
        """Compose this entity with another."""
        ...

    @abstractmethod
    def get_composition_conflicts(self, other: Any) -> list[str]:
        """Get list of conflicts when composing with another entity."""
        ...

    @property
    @abstractmethod
    def composition_priority(self) -> int:
        """Priority for conflict resolution (higher wins)."""
        ...


@runtime_checkable
class Extensible(Protocol):
    """
    Protocol for entities that support dynamic extension.

    Allows runtime addition of behaviors and capabilities
    through a plugin system.
    """

    @abstractmethod
    def add_extension(self, name: str, extension: Any) -> bool:
        """Add a named extension."""
        ...

    @abstractmethod
    def get_extension(self, name: str) -> Any:
        """Get extension by name."""
        ...

    @abstractmethod
    def list_extensions(self) -> list[str]:
        """List all extension names."""
        ...


@runtime_checkable
class Cacheable(Protocol):
    """
    Protocol for entities that support caching and memoization.

    Provides cache management with invalidation
    and performance optimization.
    """

    @abstractmethod
    def get_cache_key(self) -> str:
        """Get unique cache key for this entity."""
        ...

    @abstractmethod
    def invalidate_cache(self) -> None:
        """Invalidate cached data for this entity."""
        ...

    @property
    @abstractmethod
    def cache_ttl(self) -> int:
        """Cache time-to-live in seconds."""
        ...


@runtime_checkable
class Indexable(Protocol):
    """
    Protocol for entities that can be indexed and searched.

    Provides search capabilities with field-based
    indexing and querying.
    """

    @abstractmethod
    def get_search_fields(self) -> dict[str, Any]:
        """Get fields available for searching."""
        ...

    @abstractmethod
    def matches_query(self, query: dict[str, Any]) -> bool:
        """Check if entity matches search query."""
        ...

    @property
    @abstractmethod
    def search_priority(self) -> float:
        """Priority for search result ranking."""
        ...


@runtime_checkable
class Lazy(Protocol):
    """
    Protocol for entities that support lazy loading.

    Enables deferred loading of expensive attributes
    and dependencies.
    """

    @abstractmethod
    def load_lazy_attributes(self) -> None:
        """Load all lazy attributes."""
        ...

    @abstractmethod
    def is_fully_loaded(self) -> bool:
        """Check if all lazy attributes are loaded."""
        ...

    @property
    @abstractmethod
    def lazy_fields(self) -> list[str]:
        """List of field names that are lazily loaded."""
        ...


@runtime_checkable
class Streaming(Protocol):
    """
    Protocol for entities that support streaming updates.

    Enables incremental updates and real-time
    data processing.
    """

    @abstractmethod
    async def stream_updates(self) -> AsyncIterator[dict[str, Any]]:
        """Stream incremental updates."""
        ...

    @abstractmethod
    def apply_stream_update(self, update: dict[str, Any]) -> bool:
        """Apply a streaming update."""
        ...

    @property
    @abstractmethod
    def supports_streaming(self) -> bool:
        """Check if streaming is currently supported."""
        ...


@runtime_checkable
class Partial(Protocol):
    """
    Protocol for entities that support partial construction.

    Allows incremental building of complex entities
    with validation at each step.
    """

    @abstractmethod
    def is_complete(self) -> bool:
        """Check if entity is fully constructed."""
        ...

    @abstractmethod
    def get_missing_fields(self) -> list[str]:
        """Get list of required fields that are missing."""
        ...

    @abstractmethod
    def finalize(self) -> Any:
        """Finalize partial entity into complete form."""
        ...


@runtime_checkable
class Secured(Protocol):
    """
    Protocol for entities with security policies.

    Provides access control and security policy
    enforcement.
    """

    @abstractmethod
    def check_access(self, operation: str, context: dict[str, Any]) -> bool:
        """Check if operation is allowed in given context."""
        ...

    @abstractmethod
    def get_security_policy(self) -> dict[str, Any]:
        """Get security policy for this entity."""
        ...

    @property
    @abstractmethod
    def security_level(self) -> str:
        """Security level (e.g., 'public', 'restricted', 'confidential')."""
        ...


@runtime_checkable
class CapabilityAware(Protocol):
    """
    Protocol for entities that participate in capability-based security.

    Integrates with the capability system for fine-grained
    access control.
    """

    @abstractmethod
    def grant_capability(self, capability: str, target: Any) -> bool:
        """Grant a capability to a target entity."""
        ...

    @abstractmethod
    def revoke_capability(self, capability: str, target: Any) -> bool:
        """Revoke a capability from a target entity."""
        ...

    @abstractmethod
    def has_capability(self, capability: str) -> bool:
        """Check if entity has a specific capability."""
        ...

    @property
    @abstractmethod
    def granted_capabilities(self) -> set[str]:
        """Set of capabilities granted to this entity."""
        ...
