"""
Additional tests for TraitRegistry to improve coverage.

This module tests edge cases and error conditions not covered
by the main test file.
"""

import warnings
from unittest.mock import MagicMock, patch

import pytest

from pydapter.traits import Trait, TraitRegistry, as_trait
from pydapter.traits.registry import (
    OrphanRuleViolation,
    PerformanceWarning,
    ValidationResult,
    get_global_registry,
)


class TestRegistryEdgeCases:
    """Test edge cases in TraitRegistry."""

    def setup_method(self):
        """Set up fresh registry for each test."""
        TraitRegistry._instance = None
        self.registry = TraitRegistry()

    def teardown_method(self):
        """Clean up after each test."""
        # Force reset of the singleton instance
        TraitRegistry._instance = None
        # Clear any mocks or patches that might persist
        import gc

        gc.collect()

    def test_reset_singleton(self):
        """Test resetting singleton instance."""
        registry1 = TraitRegistry()
        TraitRegistry.reset()
        registry2 = TraitRegistry()
        assert registry1 is not registry2

    def test_orphan_rule_violation_exception(self):
        """Test OrphanRuleViolation exception details."""

        class ExternalType:
            __module__ = "external.module"

        exc = OrphanRuleViolation(Trait.IDENTIFIABLE, ExternalType)
        exc_str = str(exc)
        assert "external.module" in exc_str
        assert "ExternalType" in exc_str
        assert "IDENTIFIABLE" in exc_str

    def test_register_trait_with_validation_orphan_rule(self):
        """Test register_trait_with_validation with orphan rule violation."""
        # Temporarily modify the validation to simulate orphan rule violation
        original_validate = self.registry._validate_orphan_rule

        def mock_validate(impl_type, trait):
            return False

        self.registry._validate_orphan_rule = mock_validate

        class LocalType:
            @property
            def id(self):
                return "test"

            @property
            def id_type(self):
                return "test"

        result = self.registry.register_trait_with_validation(
            LocalType, Trait.IDENTIFIABLE
        )

        assert result.success is False
        assert result.error_type == "orphan_rule"
        assert "external type" in result.error_message

        # Restore original
        self.registry._validate_orphan_rule = original_validate

    def test_register_trait_with_validation_missing_definition(self):
        """Test register_trait_with_validation with missing trait definition."""

        class TestClass:
            pass

        # Create a trait without definition
        mock_trait = MagicMock()
        mock_trait.name = "MOCK_TRAIT"

        # Temporarily clear the definition
        original_defs = self.registry._trait_definitions.copy()
        self.registry._trait_definitions.clear()

        result = self.registry.register_trait_with_validation(
            TestClass, Trait.IDENTIFIABLE
        )

        assert result.success is False
        assert result.error_type == "implementation"
        assert "No definition found" in result.error_message

        # Restore
        self.registry._trait_definitions = original_defs

    def test_validate_trait_implementation_detailed_no_protocol(self):
        """Test _validate_trait_implementation_detailed with no protocol type."""

        class TestClass:
            pass

        # Temporarily modify trait definition
        original_def = self.registry._trait_definitions.get(Trait.IDENTIFIABLE)
        self.registry._trait_definitions[Trait.IDENTIFIABLE] = MagicMock(
            protocol_type=None
        )

        result = self.registry._validate_trait_implementation_detailed(
            TestClass, Trait.IDENTIFIABLE
        )

        assert result["valid"] is False
        assert "No protocol type defined" in result["error"]

        # Restore
        if original_def:
            self.registry._trait_definitions[Trait.IDENTIFIABLE] = original_def

    def test_validate_trait_implementation_detailed_exception(self):
        """Test _validate_trait_implementation_detailed with exception."""

        class FaultyClass:
            @property
            def id(self):
                raise RuntimeError("Property error")

            @property
            def id_type(self):
                return "faulty"

        # Mock the _get_required_attributes to raise an exception
        original_get_attrs = self.registry._get_required_attributes

        def mock_get_attrs(trait):
            raise AttributeError("Test exception")

        self.registry._get_required_attributes = mock_get_attrs

        try:
            result = self.registry._validate_trait_implementation_detailed(
                FaultyClass, Trait.IDENTIFIABLE
            )

            assert result["valid"] is False
            assert "Validation error" in result["error"]
        finally:
            self.registry._get_required_attributes = original_get_attrs

    def test_cleanup_weak_reference_with_weakref(self):
        """Test _cleanup_weak_reference with actual weakref object."""
        import weakref

        class TempClass:
            pass

        # Register a class
        type_id = id(TempClass)
        weak_ref = weakref.ref(TempClass)
        self.registry._weak_references[type_id] = weak_ref
        self.registry._type_id_mapping[TempClass] = type_id

        # Call cleanup with the weakref (simulating callback)
        self.registry._cleanup_weak_reference(weak_ref)

        # Should be cleaned up
        assert type_id not in self.registry._weak_references

    def test_performance_warning_emission(self):
        """Test that performance warnings are emitted correctly."""

        class SlowClass:
            @property
            def id(self):
                return "slow"

            @property
            def id_type(self):
                return "slow"

        # Mock perf_counter to simulate slow registration
        with patch("time.perf_counter") as mock_time:
            # Start time, then add 150μs (exceeds 100μs threshold)
            mock_time.side_effect = [0.0, 0.00015]

            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                result = self.registry.register_trait(SlowClass, Trait.IDENTIFIABLE)

                assert result is True
                # Check if performance warning was issued
                perf_warnings = [
                    warning
                    for warning in w
                    if issubclass(warning.category, PerformanceWarning)
                ]
                assert len(perf_warnings) > 0
                assert "exceeding" in str(perf_warnings[0].message)

    def test_as_trait_decorator_with_errors(self):
        """Test as_trait decorator with various error conditions."""

        # Test with missing attributes
        with pytest.raises(ValueError) as exc_info:

            @as_trait(Trait.IDENTIFIABLE)
            class MissingAttrs:
                pass

        assert "missing attributes" in str(exc_info.value)
        assert "id, id_type" in str(exc_info.value)

        # Test with missing dependencies
        with pytest.raises(ValueError) as exc_info:

            @as_trait(Trait.AUDITABLE)  # Requires IDENTIFIABLE and TEMPORAL
            class MissingDeps:
                @property
                def created_by(self):
                    return "user"

                @property
                def updated_by(self):
                    return "user"

        # AUDITABLE requires both its own attributes and dependency attributes
        assert "missing attributes" in str(exc_info.value)

    def test_as_trait_decorator_orphan_rule(self):
        """Test as_trait decorator with orphan rule violation."""
        # Get global registry and mock the orphan rule check
        from pydapter.traits import get_global_registry

        global_registry = get_global_registry()
        original_validate = global_registry._validate_orphan_rule

        def mock_validate(impl_type, trait):
            if impl_type.__name__ == "OrphanTest":
                return False
            return True

        global_registry._validate_orphan_rule = mock_validate

        try:
            with pytest.raises(ValueError) as exc_info:

                @as_trait(Trait.IDENTIFIABLE)
                class OrphanTest:
                    @property
                    def id(self):
                        return "test"

                    @property
                    def id_type(self):
                        return "test"

            assert "Failed to implement traits" in str(
                exc_info.value
            ) or "Cannot implement external trait" in str(exc_info.value)
        finally:
            # Always restore
            global_registry._validate_orphan_rule = original_validate

    def test_as_trait_decorator_unexpected_error(self):
        """Test as_trait decorator with unexpected exception."""
        from pydapter.traits import get_global_registry

        # Get the global registry instance
        global_registry = get_global_registry()

        # Store original method
        original_method = global_registry.register_trait_with_validation

        # Mock the method to raise an error
        def mock_register(*args, **kwargs):
            raise RuntimeError("Unexpected error")

        global_registry.register_trait_with_validation = mock_register

        try:
            with pytest.raises(ValueError) as exc_info:

                @as_trait(Trait.IDENTIFIABLE)
                class TestClass:
                    @property
                    def id(self):
                        return "test"

                    @property
                    def id_type(self):
                        return "test"

            assert "unexpected error" in str(exc_info.value)
        finally:
            # Always restore original method
            global_registry.register_trait_with_validation = original_method

    def test_get_required_attributes_unknown_trait(self):
        """Test _get_required_attributes with unknown trait."""
        # Create a mock trait that's not in the known list
        mock_trait = MagicMock()
        mock_trait.name = "UNKNOWN"

        attrs = self.registry._get_required_attributes(mock_trait)
        assert attrs == []

    def test_validate_dependencies_with_deps(self):
        """Test validate_dependencies with actual dependencies."""

        class BaseClass:
            @property
            def id(self):
                return "base"

            @property
            def id_type(self):
                return "base"

        class DependentClass:
            @property
            def id(self):
                return "dep"

            @property
            def id_type(self):
                return "dep"

            @property
            def created_at(self):
                return 0.0

            @property
            def updated_at(self):
                return 0.0

        # Register base trait
        self.registry.register_trait(BaseClass, Trait.IDENTIFIABLE)

        # Test with satisfied dependencies
        is_valid, missing = self.registry.validate_dependencies(
            BaseClass, {Trait.IDENTIFIABLE}
        )
        assert is_valid is True
        assert len(missing) == 0

    def test_has_trait_attribute_error(self):
        """Test has_trait when type has __getattr__ that raises."""

        class FaultyType:
            def __getattr__(self, name):
                raise AttributeError(f"No attribute {name}")

        # Default "registered" mode returns False for unregistered types
        result = self.registry.has_trait(FaultyType, Trait.IDENTIFIABLE)
        assert result is False  # Not registered

        # Protocol mode would check isinstance (but FaultyType doesn't satisfy protocol)
        result_protocol = self.registry.has_trait(
            FaultyType, Trait.IDENTIFIABLE, source="protocol"
        )
        assert result_protocol is False  # Doesn't satisfy Identifiable protocol

    def test_cleanup_failed_registration_partial_state(self):
        """Test _cleanup_failed_registration with partial registration."""

        class TestClass:
            pass

        # Simulate partial registration
        type_id = id(TestClass)
        self.registry._trait_implementations[TestClass] = {Trait.IDENTIFIABLE}
        self.registry._implementation_registry[(Trait.IDENTIFIABLE, TestClass)] = (
            MagicMock()
        )
        self.registry._type_id_mapping[TestClass] = type_id
        self.registry._weak_references[type_id] = MagicMock()

        # Cleanup
        self.registry._cleanup_failed_registration(TestClass, Trait.IDENTIFIABLE)

        # Verify cleanup
        assert TestClass not in self.registry._trait_implementations
        assert (
            Trait.IDENTIFIABLE,
            TestClass,
        ) not in self.registry._implementation_registry
        assert TestClass not in self.registry._type_id_mapping

    def test_global_registry_functions(self):
        """Test global registry helper functions."""
        # Test seal_trait
        from pydapter.traits.registry import seal_trait

        seal_trait(Trait.SECURED)
        assert Trait.SECURED in get_global_registry()._sealed_traits

    def test_validation_result_dataclass(self):
        """Test ValidationResult dataclass initialization."""
        result = ValidationResult(
            success=False,
            error_type="test",
            error_message="Test error",
            missing_dependencies={Trait.IDENTIFIABLE},
            missing_attributes=["id", "id_type"],
            performance_warning="Too slow",
        )

        assert result.success is False
        assert result.error_type == "test"
        assert result.error_message == "Test error"
        assert Trait.IDENTIFIABLE in result.missing_dependencies
        assert "id" in result.missing_attributes
        assert result.performance_warning == "Too slow"


class TestRegistryValidation:
    """Test validation-specific functionality."""

    def setup_method(self):
        """Set up fresh registry for each test."""
        TraitRegistry._instance = None
        self.registry = TraitRegistry()

    def test_get_required_attributes_auditable(self):
        """Test _get_required_attributes for AUDITABLE trait."""
        attrs = self.registry._get_required_attributes(Trait.AUDITABLE)
        assert "id" in attrs
        assert "created_by" in attrs
        assert "updated_by" in attrs

    def test_validate_trait_implementation_basic_structure(self):
        """Test _validate_trait_implementation with basic class structure."""

        class BasicClass:
            pass

        # Should pass for non-specific traits
        result = self.registry._validate_trait_implementation(
            BasicClass, Trait.HASHABLE
        )
        assert result is True

    def test_validate_trait_implementation_type_error(self):
        """Test _validate_trait_implementation with TypeError."""

        class BadClass:
            __dict__ = property(lambda self: raise_(TypeError()))

        def raise_(exc):
            raise exc

        result = self.registry._validate_trait_implementation(
            BadClass, Trait.IDENTIFIABLE
        )
        assert result is False

    def test_missing_attributes_with_methods(self):
        """Test validation with missing methods (like Hashable.compute_hash)."""

        class MissingMethod:
            pass

        result = self.registry._validate_trait_implementation_detailed(
            MissingMethod, Trait.HASHABLE
        )
        assert result["valid"] is False
        assert "compute_hash" in result["missing_attributes"]
        assert "methods" in result["error"]
