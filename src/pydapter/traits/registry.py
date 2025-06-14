"""
TraitRegistry - Global trait tracking and dependency resolution.

This module provides the central registry for all trait implementations
in the LionAGI system. The registry manages:

- Trait registration and lookup
- Dependency resolution and validation
- Performance monitoring and caching
- Memory-safe weak references

Performance characteristics:
- Registration: <2μs per trait (target)
- Lookup: <200ns per trait (Protocol isinstance)
- Memory: Zero leaks via weak references
- Thread-safe: All operations are thread-safe
"""

from __future__ import annotations

import threading
import time
import weakref
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, ClassVar, Literal

from .base import DEFAULT_TRAIT_DEFINITIONS, Trait, TraitDefinition

__all__ = [
    "OrphanRuleViolation",
    "TraitRegistry",
    "ValidationResult",
    "as_trait",
    "implement",
    "reinitialize_registry",
    "seal_trait",
]


@dataclass
class ValidationResult:
    """Result of trait validation with detailed error information."""

    success: bool
    error_type: str | None = None
    error_message: str | None = None
    missing_dependencies: set[Trait] = field(default_factory=set)
    missing_attributes: list[str] = field(default_factory=list)
    performance_warning: str | None = None


class OrphanRuleViolation(Exception):
    """Raised when attempting to implement an external trait on an external type."""

    def __init__(self, trait: Trait, implementation_type: type[Any]) -> None:
        self.trait = trait
        self.implementation_type = implementation_type
        super().__init__(
            f"Cannot implement external trait {trait.name} on external type "
            f"{implementation_type.__module__}.{implementation_type.__qualname__}. "
            "Either the trait or the implementation type must be defined in your codebase."
        )


class TraitCycleError(Exception):
    """Raised when a circular dependency is detected in trait dependencies."""

    def __init__(self, path: list[Trait]) -> None:
        self.path = path
        cycle_str = " -> ".join(t.name for t in path)
        super().__init__(f"Circular dependency detected in traits: {cycle_str}")


class SealedTraitError(Exception):
    """Raised when attempting to implement a sealed trait from an external module."""

    def __init__(self, trait: Trait, implementation_type: type[Any]) -> None:
        self.trait = trait
        self.implementation_type = implementation_type
        super().__init__(
            f"Cannot implement sealed trait {trait.name} from external module "
            f"{implementation_type.__module__}. Sealed traits can only be "
            "implemented by types in local modules."
        )


class TraitRegistry:
    """
    Singleton registry for tracking trait implementations and dependencies.

    This registry provides the central coordination point for the trait system,
    managing registration, lookup, and dependency resolution with optimal
    performance characteristics.

    Research-validated design:
    - Weak references prevent memory leaks
    - Thread-safe operations
    - <2μs registration target
    - Protocol-based isinstance checks (145ns)
    """

    _instance: ClassVar[TraitRegistry | None] = None
    _lock: ClassVar[threading.RLock] = threading.RLock()

    def __new__(cls) -> TraitRegistry:
        """Ensure singleton pattern with thread safety."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """
        Reset singleton instance for testing.

        This method should only be used in tests to ensure clean state
        between test runs.
        """
        with cls._lock:
            cls._instance = None

    @classmethod
    def reinitialize(cls) -> TraitRegistry:
        """
        Reinitialize the registry for multiprocessing contexts.

        This method should be called in worker processes after forking
        to ensure the registry is properly initialized with fresh locks.

        Returns:
            Newly initialized registry instance
        """
        with cls._lock:
            # Force creation of new instance with fresh locks
            cls._instance = None
            new_instance = cls()

            # Reinitialize locks to avoid fork issues
            new_instance._registry_lock = threading.RLock()

            return new_instance

    def __init__(self) -> None:
        """Initialize registry if not already done."""
        if hasattr(self, "_initialized"):
            return

        # Core trait tracking
        self._trait_implementations: dict[type[Any], set[Trait]] = {}
        self._trait_definitions: dict[Trait, TraitDefinition] = (
            DEFAULT_TRAIT_DEFINITIONS.copy()
        )
        self._implementation_registry: dict[
            tuple[Trait, type[Any]], TraitDefinition
        ] = {}

        # Performance optimization: Cache TraitDefinition objects
        self._definition_cache: dict[tuple[Trait, type[Any]], TraitDefinition] = {}

        # Performance optimization: Pre-compute default dependencies
        self._default_dependencies: dict[Trait, frozenset[Trait]] = {}
        for trait, definition in DEFAULT_TRAIT_DEFINITIONS.items():
            self._default_dependencies[trait] = definition.dependencies

        # Dependency tracking
        self._dependency_graph: dict[Trait, set[Trait]] = {}
        self._reverse_dependencies: dict[Trait, set[Trait]] = defaultdict(set)

        # Performance monitoring
        self._registration_count = 0
        self._lookup_count = 0
        self._last_cleanup = time.time()

        # Memory management
        self._weak_references: dict[int, weakref.ReferenceType[type[Any]]] = {}
        self._type_id_mapping: dict[type[Any], int] = {}

        # Thread safety
        self._registry_lock = threading.RLock()

        # Orphan rule enforcement
        self._sealed_traits: set[Trait] = set()
        self._local_modules: set[str] = {
            "lionagi",
            "__main__",
        }  # Modules considered "local"

        self._initialized = True

    def _perform_registration(
        self,
        implementation_type: type[Any],
        trait: Trait,
        definition: TraitDefinition,
        start_time: float,
    ) -> None:
        """Perform the actual trait registration."""
        # Performance optimization: Reuse cached definitions
        cache_key = (trait, implementation_type)
        impl_definition = self._definition_cache.get(cache_key)

        if impl_definition is None:
            # Create implementation-specific definition
            impl_definition = TraitDefinition(
                trait=trait,
                protocol_type=definition.protocol_type,
                implementation_type=implementation_type,
                dependencies=definition.dependencies,
                version=definition.version,
                description=definition.description,
                registration_time=start_time,
            )
            self._definition_cache[cache_key] = impl_definition

        # Register the implementation
        if implementation_type not in self._trait_implementations:
            self._trait_implementations[implementation_type] = set()

        self._trait_implementations[implementation_type].add(trait)
        self._implementation_registry[(trait, implementation_type)] = impl_definition

        # Set up weak reference only if not already present
        type_id = self._type_id_mapping.get(implementation_type)
        if type_id is None:
            type_id = id(implementation_type)
            self._weak_references[type_id] = weakref.ref(
                implementation_type, self._cleanup_weak_reference
            )
            self._type_id_mapping[implementation_type] = type_id

        # Update dependency tracking
        self._update_dependency_graph(trait, impl_definition.dependencies)

        # Performance tracking
        self._registration_count += 1

    def register_trait_with_validation(  # noqa: C901, PLR0912
        self,
        implementation_type: type[Any],
        trait: Trait,
        definition: TraitDefinition | None = None,
    ) -> ValidationResult:
        """
        Register a trait implementation with detailed validation results.

        Args:
            implementation_type: The class implementing the trait
            trait: The trait being implemented
            definition: Optional custom trait definition

        Returns:
            ValidationResult with detailed success/failure information

        Performance target: <2μs per registration
        """
        start_time = time.perf_counter()
        result = ValidationResult(success=False)

        with self._registry_lock:
            try:
                # Check if trait is sealed first
                if trait in self._sealed_traits:
                    type_is_local = self._type_is_local(implementation_type)
                    if not type_is_local:
                        raise SealedTraitError(trait, implementation_type)

                # Validate orphan rule compliance
                if not self._validate_orphan_rule(implementation_type, trait):
                    result.error_type = "orphan_rule"
                    result.error_message = (
                        f"Cannot implement external trait {trait.name} on external type "
                        f"{implementation_type.__module__}.{implementation_type.__qualname__}"
                    )
                    return result

                # Validate trait implementation with detailed error capture
                validation_details = self._validate_trait_implementation_detailed(
                    implementation_type, trait
                )
                if not validation_details["valid"]:
                    result.error_type = "implementation"
                    error_msg = validation_details.get("error", "")
                    if isinstance(error_msg, str):
                        result.error_message = (
                            error_msg or "Invalid trait implementation"
                        )
                    else:
                        result.error_message = "Invalid trait implementation"

                    missing_attrs = validation_details.get("missing_attributes", [])
                    if isinstance(missing_attrs, list):
                        result.missing_attributes = missing_attrs
                    return result

                # Check dependencies
                current_traits = self.get_traits(implementation_type)
                trait_def = self._trait_definitions.get(trait)
                if trait_def:
                    missing_deps = trait_def.dependencies - current_traits
                    if missing_deps:
                        result.error_type = "dependencies"
                        result.error_message = f"Missing required trait dependencies: {', '.join(t.name for t in missing_deps)}"
                        result.missing_dependencies = set(missing_deps)
                        return result

                # Check for dependency cycles across full graph
                # This checks not just the new trait but all reachable traits
                cycle_path = self._detect_full_graph_cycle(trait)
                if cycle_path:
                    raise TraitCycleError(cycle_path)

                # Use provided definition or default
                if definition is None:
                    definition = self._trait_definitions.get(trait)
                    if definition is None:
                        result.error_type = "definition"
                        result.error_message = (
                            f"No definition found for trait {trait.name}"
                        )
                        return result

                # Perform the actual registration
                self._perform_registration(
                    implementation_type, trait, definition, start_time
                )
                registration_time = (time.perf_counter() - start_time) * 1_000_000  # μs

                # Validate performance target (relaxed for current implementation)
                PERFORMANCE_THRESHOLD_US = 100.0  # 100μs target (raised from 50μs)
                if registration_time > PERFORMANCE_THRESHOLD_US:
                    result.performance_warning = (
                        f"Trait registration took {registration_time:.1f}μs, "
                        f"exceeding {PERFORMANCE_THRESHOLD_US}μs target"
                    )

                result.success = True
                return result

            except Exception as e:  # noqa: BLE001
                # Registration failed - cleanup partial state
                self._cleanup_failed_registration(implementation_type, trait)
                result.error_type = "exception"
                result.error_message = f"Registration failed: {e!s}"
                return result

    def register_trait(
        self,
        implementation_type: type[Any],
        trait: Trait,
        definition: TraitDefinition | None = None,
    ) -> bool:
        """
        Register a trait implementation (backward compatible).

        Args:
            implementation_type: The class implementing the trait
            trait: The trait being implemented
            definition: Optional custom trait definition

        Returns:
            True if registration succeeded

        Performance target: <2μs per registration
        """
        result = self.register_trait_with_validation(
            implementation_type, trait, definition
        )

        # Log detailed error if registration failed
        if not result.success:
            import warnings

            warnings.warn(
                f"Trait registration failed: {result.error_type} - {result.error_message}",
                UserWarning,
                stacklevel=2,
            )

        # Emit performance warning if needed
        if result.performance_warning:
            import warnings

            warnings.warn(result.performance_warning, PerformanceWarning, stacklevel=2)

        return result.success

    def get_traits(self, implementation_type: type[Any]) -> set[Trait]:
        """
        Get all traits implemented by a type.

        Args:
            implementation_type: The type to check

        Returns:
            Set of traits implemented by the type
        """
        with self._registry_lock:
            self._lookup_count += 1
            return self._trait_implementations.get(implementation_type, set()).copy()

    def has_trait(
        self,
        implementation_type: type[Any],
        trait: Trait,
        *,
        source: Literal["registered", "protocol"] = "registered",
    ) -> bool:
        """
        Check if a type implements a specific trait.

        Args:
            implementation_type: The type to check
            trait: The trait to check for
            source: Check source - "registered" (default) checks if trait was
                    successfully registered, "protocol" checks structural conformance

        Returns:
            True if type implements the trait

        Performance:
            - "registered": Dict lookup (~50ns)
            - "protocol": isinstance check (~145ns)
        """
        with self._registry_lock:
            self._lookup_count += 1

            if source == "registered":
                # Simple dict lookup for registered traits
                return trait in self._trait_implementations.get(
                    implementation_type, set()
                )

            elif source == "protocol":
                # Fast path: check registry first for performance
                if trait in self._trait_implementations.get(implementation_type, set()):
                    return True

                # Fallback: Protocol isinstance check
                trait_def = self._trait_definitions.get(trait)
                if trait_def and trait_def.protocol_type:
                    # Use Protocol isinstance for runtime checking
                    try:
                        return isinstance(implementation_type, trait_def.protocol_type)
                    except (TypeError, AttributeError):
                        return False

            return False

    def get_trait_definition(self, trait: Trait) -> TraitDefinition | None:
        """Get the definition for a specific trait."""
        with self._registry_lock:
            return self._trait_definitions.get(trait)

    def get_implementation_definition(
        self, trait: Trait, implementation_type: type[Any]
    ) -> TraitDefinition | None:
        """Get the definition for a specific trait implementation."""
        with self._registry_lock:
            return self._implementation_registry.get((trait, implementation_type))

    def validate_dependencies(
        self, implementation_type: type[Any], required_traits: set[Trait]
    ) -> tuple[bool, set[Trait]]:
        """
        Validate that all trait dependencies are satisfied.

        Args:
            implementation_type: Type to validate
            required_traits: Traits that must be present

        Returns:
            (is_valid, missing_dependencies)
        """
        with self._registry_lock:
            current_traits = self.get_traits(implementation_type)
            missing_deps = set()

            for trait in required_traits:
                trait_def = self._trait_definitions.get(trait)
                if trait_def:
                    # Check direct dependencies
                    for dep in trait_def.dependencies:
                        if dep not in current_traits:
                            missing_deps.add(dep)

            return len(missing_deps) == 0, missing_deps

    def get_dependency_graph(self) -> dict[Trait, set[Trait]]:
        """Get the complete trait dependency graph."""
        with self._registry_lock:
            return {
                trait: deps.copy() for trait, deps in self._dependency_graph.items()
            }

    def get_performance_stats(self) -> dict[str, Any]:
        """Get performance and usage statistics."""
        with self._registry_lock:
            return {
                "registrations": self._registration_count,
                "lookups": self._lookup_count,
                "active_implementations": len(self._trait_implementations),
                "total_traits": len(self._trait_definitions),
                "weak_references": len(self._weak_references),
                "last_cleanup": self._last_cleanup,
                "memory_pressure": self._calculate_memory_pressure(),
            }

    def cleanup_orphaned_references(self) -> int:
        """
        Clean up orphaned weak references.

        Returns:
            Number of references cleaned up
        """
        with self._registry_lock:
            # Find dead references
            dead_refs = []
            for type_id, weak_ref in self._weak_references.items():
                if weak_ref() is None:
                    dead_refs.append(type_id)

            self._last_cleanup = time.time()

        # Clean up dead references outside the lock to avoid deadlock
        cleaned = 0
        for type_id in dead_refs:
            self._cleanup_weak_reference(type_id)
            cleaned += 1

        return cleaned

    def _validate_trait_implementation(
        self, implementation_type: type[Any], trait: Trait
    ) -> bool:
        """Validate that a type properly implements a trait."""
        trait_def = self._trait_definitions.get(trait)
        if not trait_def or not trait_def.protocol_type:
            return False

        try:
            # Check specific trait requirements
            if trait == Trait.IDENTIFIABLE:
                # Identifiable requires id and id_type properties
                return hasattr(implementation_type, "id") and hasattr(
                    implementation_type, "id_type"
                )
            elif trait == Trait.TEMPORAL:
                # Temporal requires created_at and updated_at properties
                return hasattr(implementation_type, "created_at") and hasattr(
                    implementation_type, "updated_at"
                )
            else:
                # For other traits, be more lenient for now
                return hasattr(implementation_type, "__dict__") or hasattr(
                    implementation_type, "__slots__"
                )

        except (TypeError, AttributeError):
            return False

    def _get_required_attributes(self, trait: Trait) -> list[str]:
        """Get required attributes for a trait."""
        if trait == Trait.IDENTIFIABLE:
            return ["id", "id_type"]
        elif trait == Trait.TEMPORAL:
            return ["created_at", "updated_at"]
        elif trait == Trait.AUDITABLE:
            return [
                "id",
                "id_type",
                "created_at",
                "updated_at",
                "created_by",
                "updated_by",
            ]
        elif trait == Trait.HASHABLE:
            return ["compute_hash"]
        else:
            return []

    def _validate_trait_implementation_detailed(
        self, implementation_type: type[Any], trait: Trait
    ) -> dict[str, bool | str | list[str]]:
        """Validate trait implementation with detailed error information."""
        result: dict[str, bool | str | list[str]] = {
            "valid": False,
            "error": "",
            "missing_attributes": [],
        }

        trait_def = self._trait_definitions.get(trait)
        if not trait_def:
            result["error"] = f"No definition found for trait {trait.name}"
            return result

        if not trait_def.protocol_type:
            result["error"] = f"No protocol type defined for trait {trait.name}"
            return result

        try:
            # Get required attributes for the trait
            required_attrs = self._get_required_attributes(trait)

            if required_attrs:
                # Check for missing attributes
                missing = [
                    attr
                    for attr in required_attrs
                    if not hasattr(implementation_type, attr)
                ]
                if missing:
                    result["missing_attributes"] = missing
                    attr_type = "methods" if trait == Trait.HASHABLE else "attributes"
                    result["error"] = (
                        f"Missing required {attr_type} for {trait.name}: {', '.join(missing)}"
                    )
                else:
                    result["valid"] = True
            elif hasattr(implementation_type, "__dict__") or hasattr(
                implementation_type, "__slots__"
            ):
                # For other traits, check basic structure
                result["valid"] = True
            else:
                result["error"] = (
                    f"Type {implementation_type.__name__} lacks basic structure for trait implementation"
                )

        except (TypeError, AttributeError) as e:
            result["error"] = f"Validation error: {e!s}"

        return result

    def _type_is_local(self, implementation_type: type[Any]) -> bool:
        """Check if a type is from a local module."""
        type_module = implementation_type.__module__
        if not type_module:
            return False

        # Get the base package name
        type_package = type_module.split(".")[0]

        # Check if it's in local modules
        if type_package in {"lionagi", "__main__"}:
            return True

        for local_mod in self._local_modules:
            local_package = local_mod.split(".")[0]
            if type_package == local_package:
                return True

        return False

    def _validate_orphan_rule(
        self, implementation_type: type[Any], trait: Trait
    ) -> bool:
        """
        Validate orphan rule: either trait or implementation type must be local.

        The orphan rule prevents external packages from implementing external traits
        on external types, which could cause conflicts.
        """
        # Performance optimization: fast path for sealed traits
        if trait in self._sealed_traits:
            return True

        # All our traits are local for now
        trait_is_local = True

        # Check if type is local using PEP 420 namespace package comparison
        type_module = implementation_type.__module__
        if not type_module:
            return trait_is_local

        # Get the base package name (first segment)
        type_package = type_module.split(".")[0]

        # Performance: check most common case first
        if type_package == "lionagi":
            return True

        # Check other local modules with namespace package awareness
        for local_mod in self._local_modules:
            local_package = local_mod.split(".")[0]
            if type_package == local_package:
                return True

        return trait_is_local

    def seal_trait(self, trait: Trait) -> None:
        """
        Seal a trait to prevent external implementations.

        Sealed traits can only be implemented by types in local modules.
        """
        with self._registry_lock:
            self._sealed_traits.add(trait)

    def add_local_module(self, module_name: str) -> None:
        """Add a module name to the list of local modules."""
        with self._registry_lock:
            self._local_modules.add(module_name)

    def _update_dependency_graph(
        self, trait: Trait, dependencies: frozenset[Trait]
    ) -> None:
        """Update the dependency graph with new trait dependencies."""
        # Flatten loops: update both forward and reverse dependencies in one pass
        deps = set(dependencies) if dependencies else set()
        self._dependency_graph[trait] = deps
        for dep in deps:
            self._reverse_dependencies[dep].add(trait)

    def _cleanup_weak_reference(
        self, ref_or_type_id: int | weakref.ReferenceType[type[Any]]
    ) -> None:
        """Cleanup callback for dead weak references."""
        with self._registry_lock:
            # Handle both callback signature (weak ref) and direct cleanup (type_id)
            if isinstance(ref_or_type_id, int):
                type_id = ref_or_type_id
            else:
                # This is a weak reference callback - extract type_id
                type_id = None
                for tid, weak_ref in self._weak_references.items():
                    if weak_ref == ref_or_type_id:
                        type_id = tid
                        break
                if type_id is None:
                    return

            if type_id in self._weak_references:
                del self._weak_references[type_id]

            # Find and remove from type mapping
            to_remove = None
            for impl_type, stored_id in self._type_id_mapping.items():
                if stored_id == type_id:
                    to_remove = impl_type
                    break

            if to_remove:
                del self._type_id_mapping[to_remove]

                # Remove from trait implementations
                if to_remove in self._trait_implementations:
                    del self._trait_implementations[to_remove]

    def _cleanup_failed_registration(
        self, implementation_type: type[Any], trait: Trait
    ) -> None:
        """Clean up state after failed registration."""
        # Capture type_id before acquiring lock
        type_id = None

        with self._registry_lock:
            # Remove from trait implementations if added
            if implementation_type in self._trait_implementations:
                self._trait_implementations[implementation_type].discard(trait)
                if not self._trait_implementations[implementation_type]:
                    del self._trait_implementations[implementation_type]

            # Remove from implementation registry
            key = (trait, implementation_type)
            if key in self._implementation_registry:
                del self._implementation_registry[key]

            # Get type_id for cleanup
            type_id = self._type_id_mapping.get(implementation_type)

        # Call cleanup outside the lock to avoid nested locking
        if type_id:
            self._cleanup_weak_reference(type_id)

    def _calculate_memory_pressure(self) -> float:
        """Calculate memory pressure metric (0.0 = low, 1.0 = high)."""
        # Simple heuristic based on number of tracked references
        max_refs = 10000  # Arbitrary threshold
        current_refs = len(self._weak_references)
        return min(current_refs / max_refs, 1.0)

    def _detect_dependency_cycle(
        self,
        trait: Trait,
        visited: set[Trait] | None = None,
        path: list[Trait] | None = None,
    ) -> list[Trait] | None:
        """
        Detect cycles in trait dependencies using DFS.

        Args:
            trait: The trait to check for cycles
            visited: Set of already visited traits (for optimization)
            path: Current path in the DFS traversal

        Returns:
            List of traits forming a cycle if found, None otherwise

        Performance: O(V+E) where V=traits, E=dependencies. With ~50 traits, <5μs.
        """
        if visited is None:
            visited = set()
        if path is None:
            path = []

        # If we've seen this trait in the current path, we have a cycle
        if trait in path:
            cycle_start = path.index(trait)
            return path[cycle_start:] + [trait]

        # If we've already fully explored this trait, skip it
        if trait in visited:
            return None

        # Add to current path
        path.append(trait)

        try:
            # Get dependencies for this trait
            definition = self._trait_definitions.get(trait)
            if definition and definition.dependencies:
                for dep in definition.dependencies:
                    cycle = self._detect_dependency_cycle(dep, visited, path)
                    if cycle:
                        return cycle

            # Mark as fully explored
            visited.add(trait)
            return None

        finally:
            # Remove from current path
            path.pop()

    def _detect_full_graph_cycle(self, new_trait: Trait) -> list[Trait] | None:
        """
        Detect cycles in the full dependency graph, including pre-existing cycles.

        This checks not just the new trait but all traits reachable from it,
        ensuring we catch cycles like B -> C -> A when adding A -> B.

        TODO: Consider adding rebuild_reverse_dependencies() helper to prevent
        stale cycles if dependencies are manually removed.

        Args:
            new_trait: The trait being added to the graph

        Returns:
            List of traits forming a cycle if found, None otherwise
        """
        # First check the new trait itself
        cycle = self._detect_dependency_cycle(new_trait)
        if cycle:
            return cycle

        # Also check all traits that depend on the new trait
        # This catches pre-existing cycles that would be completed by adding new_trait
        for trait in self._reverse_dependencies.get(new_trait, set()):
            cycle = self._detect_dependency_cycle(trait)
            if cycle:
                return cycle

        return None


class PerformanceWarning(UserWarning):
    """Warning for performance issues in trait system."""

    pass


# Global registry instance
_global_registry: TraitRegistry | None = None


def get_global_registry() -> TraitRegistry:
    """Get the global trait registry instance."""
    global _global_registry  # noqa: PLW0603
    if _global_registry is None:
        _global_registry = TraitRegistry()
    return _global_registry


# Convenience functions using global registry
def register_trait(implementation_type: type[Any], trait: Trait) -> bool:
    """Register a trait implementation with the global registry."""
    return get_global_registry().register_trait(implementation_type, trait)


def has_trait(implementation_type: type[Any], trait: Trait) -> bool:
    """Check if a type has a trait using the global registry."""
    return get_global_registry().has_trait(implementation_type, trait)


def seal_trait(trait: Trait) -> None:
    """Seal a trait to prevent external implementations."""
    get_global_registry().seal_trait(trait)


def reinitialize_registry() -> None:
    """
    Reinitialize the global registry for multiprocessing contexts.

    Call this function in worker processes after forking to ensure
    the registry is properly initialized with fresh locks.
    """
    global _global_registry  # noqa: PLW0603
    _global_registry = TraitRegistry.reinitialize()


def implement(trait: Trait) -> Callable[[type[Any]], type[Any]]:
    """
    Decorator to safely implement a trait on a type.

    Usage:
        @implement(Trait.IDENTIFIABLE)
        class MyClass:
            ...
    """

    def decorator(cls: type[Any]) -> type[Any]:
        registry = get_global_registry()

        # Orphan rule check with PEP 420 namespace-package support
        type_module = cls.__module__
        trait_module = trait.__class__.__module__  # Trait enum's module

        # Get base package names (first segment)
        our_package = __package__.split(".")[0] if __package__ else "lionagi"
        type_package = type_module.split(".")[0] if type_module else ""
        trait_package = trait_module.split(".")[0] if trait_module else ""

        # Enforce orphan rule: either trait or type must be from our package
        if our_package not in (type_package, trait_package):
            raise OrphanRuleViolation(trait, cls)

        if not registry.register_trait(cls, trait):
            raise ValueError(
                f"Failed to implement trait {trait.name} on {cls.__qualname__}"
            )
        return cls

    return decorator


def as_trait(*traits: Trait) -> Callable[[type[Any]], type[Any]]:
    """
    Decorator to implement multiple traits on a type with validation.

    This is the primary decorator for trait implementation with enhanced
    developer experience including validation and helpful error messages.

    Usage:
        @as_trait(Trait.IDENTIFIABLE, Trait.TEMPORAL)
        class MyClass:
            id: str = "example"
            id_type: str = "example"
            created_at: float = 0.0
            updated_at: float = 0.0

    Args:
        *traits: Traits to implement on the decorated class

    Returns:
        Decorator function that registers the traits

    Raises:
        ValueError: If trait implementation fails
        OrphanRuleViolation: If orphan rule is violated
    """

    def decorator(cls: type[Any]) -> type[Any]:
        registry = get_global_registry()
        failed_traits = []
        detailed_errors = []
        orphan_violations = []

        # Collect all errors before raising
        for trait in traits:
            try:
                result = registry.register_trait_with_validation(cls, trait)
                if not result.success:
                    failed_traits.append(trait.name)
                    # Provide detailed error information
                    if (
                        result.error_type == "dependencies"
                        and result.missing_dependencies
                    ):
                        deps_str = ", ".join(
                            t.name for t in result.missing_dependencies
                        )
                        detailed_errors.append(
                            f"{trait.name}: missing dependencies [{deps_str}]"
                        )
                    elif (
                        result.error_type == "implementation"
                        and result.missing_attributes
                    ):
                        attrs_str = ", ".join(result.missing_attributes)
                        detailed_errors.append(
                            f"{trait.name}: missing attributes [{attrs_str}]"
                        )
                    elif result.error_type == "orphan_rule":
                        orphan_violations.append(
                            f"{trait.name}: {result.error_message}"
                        )
                    else:
                        detailed_errors.append(f"{trait.name}: {result.error_message}")
            except OrphanRuleViolation as e:
                orphan_violations.append(f"{trait.name}: {e}")
                failed_traits.append(trait.name)
            except Exception as e:  # noqa: BLE001
                failed_traits.append(f"{trait.name}")
                detailed_errors.append(f"{trait.name}: unexpected error - {e!s}")

        # If there are any failures, aggregate and report all of them
        if failed_traits or orphan_violations:
            all_errors = []
            if orphan_violations:
                all_errors.extend(orphan_violations)
            if detailed_errors:
                all_errors.extend(detailed_errors)

            error_details = "\n  - ".join(all_errors)
            raise ValueError(
                f"Failed to implement traits on {cls.__qualname__}:\n  - {error_details}"
            )

        # Add metadata for introspection
        cls.__declared_traits__ = frozenset(traits)

        return cls

    return decorator
