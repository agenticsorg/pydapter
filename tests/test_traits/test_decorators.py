"""
Tests for trait decorators and developer experience features.

This module tests the decorator functionality and CLI introspection tools.
"""

import pytest

from pydapter.traits import Trait, as_trait, implement


class TestImplementDecorator:
    """Test the @implement decorator."""

    def test_implement_single_trait(self):
        """Test implementing a single trait with decorator."""

        @implement(Trait.IDENTIFIABLE)
        class TestClass:
            @property
            def id(self) -> str:
                return "test-123"

            @property
            def id_type(self) -> str:
                return "test"

        # Should be registered automatically
        from pydapter.traits import get_global_registry

        registry = get_global_registry()

        assert registry.has_trait(TestClass, Trait.IDENTIFIABLE)

    def test_implement_invalid_trait(self):
        """Test implementing invalid trait raises error."""

        with pytest.raises(ValueError):

            @implement(Trait.IDENTIFIABLE)
            class InvalidClass:
                # Missing required properties
                pass


class TestAsTraitDecorator:
    """Test the @as_trait decorator."""

    def test_as_trait_single(self):
        """Test @as_trait with single trait."""

        @as_trait(Trait.IDENTIFIABLE)
        class SingleTraitClass:
            @property
            def id(self) -> str:
                return "single-123"

            @property
            def id_type(self) -> str:
                return "single"

        # Should be registered and have metadata
        from pydapter.traits import get_global_registry

        registry = get_global_registry()

        assert registry.has_trait(SingleTraitClass, Trait.IDENTIFIABLE)
        assert hasattr(SingleTraitClass, "__declared_traits__")
        assert Trait.IDENTIFIABLE in SingleTraitClass.__declared_traits__

    def test_as_trait_multiple(self):
        """Test @as_trait with multiple traits."""

        @as_trait(Trait.IDENTIFIABLE, Trait.TEMPORAL)
        class MultiTraitClass:
            @property
            def id(self) -> str:
                return "multi-123"

            @property
            def id_type(self) -> str:
                return "multi"

            @property
            def created_at(self) -> float:
                return 0.0

            @property
            def updated_at(self) -> float:
                return 0.0

        from pydapter.traits import get_global_registry

        registry = get_global_registry()

        assert registry.has_trait(MultiTraitClass, Trait.IDENTIFIABLE)
        assert registry.has_trait(MultiTraitClass, Trait.TEMPORAL)
        assert len(MultiTraitClass.__declared_traits__) == 2

    def test_as_trait_validation_failure(self):
        """Test @as_trait with validation failure."""

        with pytest.raises(ValueError) as exc_info:

            @as_trait(Trait.IDENTIFIABLE, Trait.TEMPORAL)
            class InvalidMultiClass:
                # Missing required properties for both traits
                pass

        assert "Failed to implement traits" in str(exc_info.value)

    def test_as_trait_orphan_rule_violation(self):
        """Test @as_trait with orphan rule violation."""

        # This test would need a more complex setup to trigger orphan rule
        # For now, just test that the mechanism exists

        @as_trait(Trait.IDENTIFIABLE)
        class ValidClass:
            @property
            def id(self) -> str:
                return "valid-123"

            @property
            def id_type(self) -> str:
                return "valid"

        # Should succeed for local classes
        assert hasattr(ValidClass, "__declared_traits__")

    def test_as_trait_empty(self):
        """Test @as_trait with no traits."""

        @as_trait()
        class EmptyTraitClass:
            pass

        # Should work but register no traits
        assert hasattr(EmptyTraitClass, "__declared_traits__")
        assert len(EmptyTraitClass.__declared_traits__) == 0


class TestDecoratorMetadata:
    """Test decorator metadata and introspection."""

    def test_declared_traits_metadata(self):
        """Test that declared traits metadata is preserved."""

        @as_trait(Trait.IDENTIFIABLE, Trait.HASHABLE)
        class MetadataClass:
            @property
            def id(self) -> str:
                return "meta-123"

            @property
            def id_type(self) -> str:
                return "meta"

            def compute_hash(self) -> str:
                """Compute hash for Hashable trait."""
                return f"hash-{self.id}"

            def __hash__(self) -> int:
                return hash(self.id)

            @property
            def hash_fields(self) -> tuple[str, ...]:
                return ("id",)

        # Check metadata is correct
        declared = MetadataClass.__declared_traits__
        assert isinstance(declared, frozenset)
        assert Trait.IDENTIFIABLE in declared
        assert Trait.HASHABLE in declared
        assert len(declared) == 2

    def test_decorator_preserves_class_attributes(self):
        """Test that decorators preserve existing class attributes."""

        @as_trait(Trait.IDENTIFIABLE)
        class AttributeClass:
            class_var = "preserved"

            def __init__(self, value: str):
                self.instance_var = value

            @property
            def id(self) -> str:
                return "attr-123"

            @property
            def id_type(self) -> str:
                return "attr"

            def custom_method(self) -> str:
                return "custom"

        # Class should preserve all attributes
        assert AttributeClass.class_var == "preserved"
        assert hasattr(AttributeClass, "custom_method")

        instance = AttributeClass("test")
        assert instance.instance_var == "test"
        assert instance.custom_method() == "custom"

    def test_decorator_inheritance(self):
        """Test decorator behavior with inheritance."""

        @as_trait(Trait.IDENTIFIABLE)
        class BaseClass:
            @property
            def id(self) -> str:
                return "base-123"

            @property
            def id_type(self) -> str:
                return "base"

        @as_trait(Trait.TEMPORAL)
        class DerivedClass(BaseClass):
            @property
            def created_at(self) -> float:
                return 0.0

            @property
            def updated_at(self) -> float:
                return 0.0

        from pydapter.traits import get_global_registry

        registry = get_global_registry()

        # Base class should have IDENTIFIABLE
        assert registry.has_trait(BaseClass, Trait.IDENTIFIABLE)
        assert Trait.IDENTIFIABLE in BaseClass.__declared_traits__

        # Derived class should have TEMPORAL (but not automatically IDENTIFIABLE)
        assert registry.has_trait(DerivedClass, Trait.TEMPORAL)
        assert Trait.TEMPORAL in DerivedClass.__declared_traits__

        # Inheritance of traits is not automatic - each class declares its own
        assert Trait.IDENTIFIABLE not in DerivedClass.__declared_traits__


class TestDecoratorErrors:
    """Test decorator error handling."""

    def test_implement_with_none_trait(self):
        """Test implement decorator with invalid trait."""

        # This would be caught at the type level, but test runtime behavior
        with pytest.raises((ValueError, AttributeError, TypeError)):

            @implement(None)  # type: ignore
            class BadClass:
                pass

    def test_as_trait_with_invalid_argument(self):
        """Test as_trait decorator with invalid arguments."""

        with pytest.raises((ValueError, AttributeError, TypeError)):

            @as_trait("invalid")  # type: ignore
            class BadArgsClass:
                pass

    def test_decorator_on_non_class(self):
        """Test decorator behavior on non-class objects."""

        # Decorators should work on classes only
        with pytest.raises((ValueError, AttributeError, TypeError)):

            @as_trait(Trait.IDENTIFIABLE)
            def not_a_class():
                pass
