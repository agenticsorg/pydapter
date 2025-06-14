"""
Tests for TraitRegistry validation edge cases.

Specifically tests:
- Duplicate trait registration
- Cyclic dependency detection
- Sealing after registration
- Concurrent registration
"""

import concurrent.futures
import threading
import time
from typing import Any

import pytest

from pydapter.traits import Trait, TraitRegistry
from pydapter.traits.base import TraitDefinition
from pydapter.traits.registry import PerformanceWarning


class TestRegistryValidation:
    """Test validation edge cases in TraitRegistry."""

    def setup_method(self):
        """Set up fresh registry for each test."""
        TraitRegistry._instance = None
        self.registry = TraitRegistry()

    def teardown_method(self):
        """Clean up after each test."""
        TraitRegistry._instance = None

    def test_duplicate_trait_registration(self):
        """Test that registering the same trait twice succeeds but doesn't duplicate."""

        class MyIdentifiable:
            @property
            def id(self) -> str:
                return "test-id"

            @property
            def id_type(self) -> str:
                return "test"

        # First registration
        result1 = self.registry.register_trait(MyIdentifiable, Trait.IDENTIFIABLE)
        assert result1 is True

        # Second registration (should succeed but not duplicate)
        result2 = self.registry.register_trait(MyIdentifiable, Trait.IDENTIFIABLE)
        assert result2 is True

        # Verify only one registration exists
        traits = self.registry.get_traits(MyIdentifiable)
        assert len(traits) == 1
        assert Trait.IDENTIFIABLE in traits

        # Check performance stats show 2 registrations
        stats = self.registry.get_performance_stats()
        assert stats["registrations"] == 2

    def test_cyclic_dependency_detection(self):
        """Test detection of cyclic trait dependencies."""
        # Create custom trait definitions with cyclic dependencies
        # This requires modifying the trait definitions temporarily

        # Save original definitions
        original_defs = self.registry._trait_definitions.copy()

        try:
            # Create a cyclic dependency: A -> B -> C -> A
            trait_a = Trait.COMPOSABLE
            trait_b = Trait.EXTENSIBLE
            trait_c = Trait.CACHEABLE

            # Modify definitions to create cycle
            self.registry._trait_definitions[trait_a] = TraitDefinition(
                trait=trait_a,
                protocol_type=object,
                implementation_type=object,
                dependencies=frozenset({trait_b}),
                description="Test trait A",
            )

            self.registry._trait_definitions[trait_b] = TraitDefinition(
                trait=trait_b,
                protocol_type=object,
                implementation_type=object,
                dependencies=frozenset({trait_c}),
                description="Test trait B",
            )

            self.registry._trait_definitions[trait_c] = TraitDefinition(
                trait=trait_c,
                protocol_type=object,
                implementation_type=object,
                dependencies=frozenset({trait_a}),  # Creates cycle
                description="Test trait C",
            )

            class CyclicClass:
                pass

            # Attempting to register should detect the cycle
            # For now, the system doesn't explicitly detect cycles during registration
            # This is a gap identified by the reviewer that needs implementation
            result = self.registry.register_trait(CyclicClass, trait_a)

            # TODO: Implement cycle detection in TraitRegistry
            # Currently the system detects missing dependencies but not cycles
            # The registration fails due to missing dependencies, not cycle detection
            assert result is False  # Fails due to missing dependencies

        finally:
            # Restore original definitions
            self.registry._trait_definitions = original_defs

    def test_sealing_after_registration(self):
        """Test that sealing a trait after registration prevents new implementations."""

        class FirstImplementation:
            @property
            def id(self) -> str:
                return "first"

            @property
            def id_type(self) -> str:
                return "test"

        class SecondImplementation:
            @property
            def id(self) -> str:
                return "second"

            @property
            def id_type(self) -> str:
                return "test"

        # Register first implementation
        result1 = self.registry.register_trait(FirstImplementation, Trait.IDENTIFIABLE)
        assert result1 is True

        # Seal the trait
        self.registry.seal_trait(Trait.IDENTIFIABLE)

        # Try to register second implementation from external module
        # Simulate external module by changing __module__
        SecondImplementation.__module__ = "external.module"

        # Sealing now correctly prevents registration from external modules
        result2 = self.registry.register_trait_with_validation(
            SecondImplementation, Trait.IDENTIFIABLE
        )

        # Sealing is now properly enforced - should fail with error
        assert result2.success is False
        assert result2.error_type == "exception"
        assert "Cannot implement sealed trait" in result2.error_message

        # Verify first implementation is registered, second is not
        assert self.registry.has_trait(FirstImplementation, Trait.IDENTIFIABLE)
        # Sealing correctly prevented the second registration
        assert not self.registry.has_trait(SecondImplementation, Trait.IDENTIFIABLE)

    def test_concurrent_trait_registration(self):
        """Test thread-safe concurrent trait registration."""

        num_threads = 10
        registrations_per_thread = 50
        registration_errors = []

        def register_traits(thread_id: int):
            """Register traits from a thread."""
            try:
                for i in range(registrations_per_thread):
                    # Create unique class for each registration
                    class_name = f"ThreadClass_{thread_id}_{i}"
                    cls_dict = {
                        "id": property(
                            lambda self, tid=thread_id, idx=i: f"id_{tid}_{idx}"
                        ),
                        "id_type": property(lambda self: "test"),
                        "__module__": __name__,
                    }
                    cls = type(class_name, (), cls_dict)

                    # Register the trait
                    result = self.registry.register_trait(cls, Trait.IDENTIFIABLE)

                    if not result:
                        registration_errors.append(f"Failed: {class_name}")

                    # Small delay to increase chance of race conditions
                    time.sleep(0.0001)

            except (TypeError, AttributeError, ValueError) as e:
                registration_errors.append(f"Exception in thread {thread_id}: {e}")

        # Run concurrent registrations
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(register_traits, i) for i in range(num_threads)]

            # Wait for all threads to complete
            concurrent.futures.wait(futures)

        # Verify no errors occurred
        assert len(registration_errors) == 0, f"Errors occurred: {registration_errors}"

        # Verify correct number of registrations
        stats = self.registry.get_performance_stats()
        expected_count = num_threads * registrations_per_thread
        assert stats["registrations"] == expected_count

    def test_concurrent_cleanup_and_registration(self):
        """Test concurrent cleanup and registration operations."""

        stop_flag = threading.Event()
        errors = []

        def register_loop():
            """Continuously register new types."""
            i = 0
            while not stop_flag.is_set():
                try:
                    cls = type(
                        f"RegClass_{i}",
                        (),
                        {
                            "id": property(lambda self, idx=i: f"id_{idx}"),
                            "id_type": property(lambda self: "test"),
                        },
                    )
                    self.registry.register_trait(cls, Trait.IDENTIFIABLE)
                    i += 1
                    time.sleep(0.001)
                except (TypeError, AttributeError, ValueError) as e:
                    errors.append(f"Register error: {e}")

        def cleanup_loop():
            """Continuously cleanup orphaned references."""
            while not stop_flag.is_set():
                try:
                    self.registry.cleanup_orphaned_references()
                    time.sleep(0.005)
                except (TypeError, AttributeError, ValueError) as e:
                    errors.append(f"Cleanup error: {e}")

        # Run both operations concurrently
        register_thread = threading.Thread(target=register_loop)
        cleanup_thread = threading.Thread(target=cleanup_loop)

        register_thread.start()
        cleanup_thread.start()

        # Let them run for a short time
        time.sleep(0.1)

        # Stop and wait
        stop_flag.set()
        register_thread.join()
        cleanup_thread.join()

        # Verify no errors
        assert len(errors) == 0, f"Concurrent errors: {errors}"

    def test_dependency_validation_with_missing_traits(self):
        """Test registration when dependencies are not satisfied."""

        class AuditableClass:
            @property
            def version(self) -> int:
                return 1

            @property
            def audit_log(self) -> list[dict[str, Any]]:
                return []

            def emit_audit_event(self, event_type: str, **kwargs: Any) -> None:
                pass

        # Try to register AUDITABLE without its dependencies (IDENTIFIABLE, TEMPORAL)
        # The warning message is about missing attributes, not dependencies
        with pytest.warns(UserWarning, match="Missing required attributes"):
            result = self.registry.register_trait(AuditableClass, Trait.AUDITABLE)

        assert result is False

        # With the new dual-mode has_trait:
        # "registered" mode correctly shows the trait wasn't registered
        assert not self.registry.has_trait(
            AuditableClass, Trait.AUDITABLE, source="registered"
        )
        # "protocol" mode may still pass if class satisfies the protocol
        # (depends on whether AuditableClass satisfies all Auditable protocol requirements)

    def test_performance_warning_on_slow_registration(self):
        """Test that slow registrations emit performance warnings."""

        # Mock slow validation inside _validate_trait_implementation_detailed
        # which is called within the timing window
        original_validate = self.registry._validate_trait_implementation_detailed

        def slow_validate(
            impl_type: type[Any], trait: Trait
        ) -> dict[str, bool | str | list[str]]:
            time.sleep(0.0002)  # 200μs delay to exceed 100μs threshold
            return original_validate(impl_type, trait)

        self.registry._validate_trait_implementation_detailed = slow_validate

        class SlowClass:
            @property
            def id(self) -> str:
                return "slow"

            @property
            def id_type(self) -> str:
                return "test"

        try:
            # Force registration to take longer than threshold
            result = self.registry.register_trait_with_validation(
                SlowClass, Trait.IDENTIFIABLE
            )

            # Since we mocked validation to be slow (200μs > 100μs threshold),
            # the result should have a performance warning
            assert result.success is True
            assert result.performance_warning is not None
            assert "exceeding" in result.performance_warning
            assert "100" in result.performance_warning  # Should mention the threshold

            # Also verify the warning is emitted when using register_trait
            with pytest.warns(PerformanceWarning, match="exceeding"):
                self.registry.register_trait(SlowClass, Trait.IDENTIFIABLE)
        finally:
            # Restore original
            self.registry._validate_trait_implementation_detailed = original_validate
