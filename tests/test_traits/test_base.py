"""
Tests for trait base definitions and enumerations.

This module tests the core trait enumeration and
TraitDefinition functionality.
"""

import pytest

from pydapter.traits.base import DEFAULT_TRAIT_DEFINITIONS, Trait, TraitDefinition
from pydapter.traits.protocols import Identifiable, Temporal


class TestTraitEnum:
    """Test the Trait enumeration."""

    def test_trait_enum_completeness(self):
        """Test that all expected traits are defined."""
        expected_traits = {
            "IDENTIFIABLE",
            "TEMPORAL",
            "AUDITABLE",
            "HASHABLE",
            "OPERABLE",
            "OBSERVABLE",
            "VALIDATABLE",
            "SERIALIZABLE",
            "COMPOSABLE",
            "EXTENSIBLE",
            "CACHEABLE",
            "INDEXABLE",
            "LAZY",
            "STREAMING",
            "PARTIAL",
            "SECURED",
            "CAPABILITY_AWARE",
        }

        actual_traits = {trait.name for trait in Trait}
        assert actual_traits == expected_traits

    def test_trait_enum_values(self):
        """Test that trait enum values are unique and stable."""
        values = [trait.value for trait in Trait]
        assert len(values) == len(set(values))  # All unique
        assert all(isinstance(val, str) for val in values)  # All strings for stability
        # Verify string values match lowercase names for consistency
        for trait in Trait:
            assert trait.value == trait.name.lower(), (
                f"{trait.name} value should be '{trait.name.lower()}'"
            )

    def test_trait_enum_ordering(self):
        """Test that core traits are properly defined."""
        # Test semantic properties instead of numeric ordering
        core_traits = {
            Trait.IDENTIFIABLE,
            Trait.TEMPORAL,
            Trait.AUDITABLE,
            Trait.HASHABLE,
        }
        behavior_traits = {
            Trait.OPERABLE,
            Trait.OBSERVABLE,
            Trait.VALIDATABLE,
            Trait.SERIALIZABLE,
        }
        composition_traits = {
            Trait.COMPOSABLE,
            Trait.EXTENSIBLE,
            Trait.CACHEABLE,
            Trait.INDEXABLE,
        }
        performance_traits = {Trait.LAZY, Trait.STREAMING, Trait.PARTIAL}
        security_traits = {Trait.SECURED, Trait.CAPABILITY_AWARE}

        # All trait groups should be present
        all_expected = (
            core_traits
            | behavior_traits
            | composition_traits
            | performance_traits
            | security_traits
        )
        all_actual = set(Trait)

        assert all_expected == all_actual, (
            f"Missing traits: {all_expected - all_actual}"
        )

        # Core traits should be distinct from others
        assert core_traits.isdisjoint(behavior_traits)
        assert core_traits.isdisjoint(composition_traits)


class TestTraitDefinition:
    """Test the TraitDefinition dataclass."""

    def test_trait_definition_creation(self):
        """Test creating a basic TraitDefinition."""
        definition = TraitDefinition(
            trait=Trait.IDENTIFIABLE,
            protocol_type=Identifiable,
            implementation_type=object,
            version="1.0.0",
            description="Test definition",
        )

        assert definition.trait == Trait.IDENTIFIABLE
        assert definition.protocol_type == Identifiable
        assert definition.implementation_type is object
        assert definition.version == "1.0.0"
        assert definition.description == "Test definition"
        assert definition.dependencies == frozenset()

    def test_trait_definition_with_dependencies(self):
        """Test TraitDefinition with dependencies."""
        deps = frozenset([Trait.IDENTIFIABLE, Trait.TEMPORAL])

        definition = TraitDefinition(
            trait=Trait.AUDITABLE,
            protocol_type=Identifiable,  # Placeholder
            implementation_type=object,
            dependencies=deps,
        )

        assert definition.dependencies == deps
        assert Trait.IDENTIFIABLE in definition.dependencies
        assert Trait.TEMPORAL in definition.dependencies

    def test_trait_definition_frozen(self):
        """Test that TraitDefinition is immutable."""
        definition = TraitDefinition(
            trait=Trait.IDENTIFIABLE,
            protocol_type=Identifiable,
            implementation_type=object,
        )

        # Should not be able to modify
        with pytest.raises(AttributeError):
            definition.trait = Trait.TEMPORAL

        with pytest.raises(AttributeError):
            definition.version = "2.0.0"

    def test_weak_reference_setup(self):
        """Test that weak reference is properly set up."""

        class TestImpl:
            pass

        definition = TraitDefinition(
            trait=Trait.IDENTIFIABLE,
            protocol_type=Identifiable,
            implementation_type=TestImpl,
        )

        # Weak reference should be alive initially
        assert definition.is_alive
        assert definition._weak_impl_ref() is TestImpl

        # Test that weak reference exists (we can't reliably test GC timing)
        assert hasattr(definition, "_weak_impl_ref")
        assert definition._weak_impl_ref is not None

    def test_validate_dependencies_success(self):
        """Test successful dependency validation."""
        definition = TraitDefinition(
            trait=Trait.AUDITABLE,
            protocol_type=Identifiable,  # Placeholder
            implementation_type=object,
            dependencies=frozenset([Trait.IDENTIFIABLE, Trait.TEMPORAL]),
        )

        # Available traits include dependencies
        available = {Trait.IDENTIFIABLE, Trait.TEMPORAL, Trait.AUDITABLE}
        result = definition.validate_dependencies(available)

        assert result is True

    def test_validate_dependencies_failure(self):
        """Test failed dependency validation."""
        definition = TraitDefinition(
            trait=Trait.AUDITABLE,
            protocol_type=Identifiable,  # Placeholder
            implementation_type=object,
            dependencies=frozenset([Trait.IDENTIFIABLE, Trait.TEMPORAL]),
        )

        # Available traits missing some dependencies
        available = {Trait.IDENTIFIABLE}  # Missing TEMPORAL
        result = definition.validate_dependencies(available)

        assert result is False

    def test_get_dependency_graph(self):
        """Test dependency graph generation."""
        deps = frozenset([Trait.IDENTIFIABLE, Trait.TEMPORAL])
        definition = TraitDefinition(
            trait=Trait.AUDITABLE,
            protocol_type=Identifiable,  # Placeholder
            implementation_type=object,
            dependencies=deps,
        )

        graph = definition.get_dependency_graph()

        assert Trait.AUDITABLE in graph
        assert graph[Trait.AUDITABLE] == deps

    def test_default_values(self):
        """Test that default values are properly set."""
        definition = TraitDefinition(
            trait=Trait.IDENTIFIABLE,
            protocol_type=Identifiable,
            implementation_type=object,
        )

        assert definition.dependencies == frozenset()
        assert definition.version == "1.0.0"
        assert definition.description == ""
        assert definition.registration_time == 0.0
        assert definition.validation_checks == 0


class TestDefaultTraitDefinitions:
    """Test the default trait definitions."""

    def test_default_definitions_exist(self):
        """Test that default definitions exist for all traits."""
        # Should have definitions for all traits
        for trait in Trait:
            assert trait in DEFAULT_TRAIT_DEFINITIONS

            definition = DEFAULT_TRAIT_DEFINITIONS[trait]
            assert isinstance(definition, TraitDefinition)
            assert definition.trait == trait

    def test_default_definitions_have_protocols(self):
        """Test that default definitions have protocol types."""
        for _trait, definition in DEFAULT_TRAIT_DEFINITIONS.items():
            assert definition.protocol_type is not None
            assert hasattr(definition.protocol_type, "__instancecheck__")
            assert hasattr(definition.protocol_type, "__subclasscheck__")

    def test_specific_default_definitions(self):
        """Test specific default definitions."""
        # Test Identifiable
        id_def = DEFAULT_TRAIT_DEFINITIONS[Trait.IDENTIFIABLE]
        assert id_def.protocol_type == Identifiable
        assert id_def.trait == Trait.IDENTIFIABLE

        # Test Temporal
        temporal_def = DEFAULT_TRAIT_DEFINITIONS[Trait.TEMPORAL]
        assert temporal_def.protocol_type == Temporal
        assert temporal_def.trait == Trait.TEMPORAL

    def test_default_definitions_consistency(self):
        """Test that default definitions are consistent."""
        for trait, definition in DEFAULT_TRAIT_DEFINITIONS.items():
            # All should have same implementation type (placeholder)
            assert definition.implementation_type is object

            # Dependencies should be properly defined (some traits have dependencies)
            assert isinstance(definition.dependencies, frozenset)

            # Validate specific trait dependencies from research spec
            if trait == Trait.AUDITABLE:
                assert Trait.IDENTIFIABLE in definition.dependencies
                assert Trait.TEMPORAL in definition.dependencies
            elif trait == Trait.CAPABILITY_AWARE:
                assert Trait.SECURED in definition.dependencies
                assert Trait.IDENTIFIABLE in definition.dependencies

            # All should have default version
            assert definition.version == "1.0.0"

            # All should have descriptions
            assert len(definition.description) > 0
            assert trait.name.lower() in definition.description.lower()


class TestTraitDefinitionPerformance:
    """Test performance aspects of TraitDefinition."""

    def test_trait_definition_memory_efficiency(self):
        """Test that TraitDefinition uses slots for memory efficiency."""
        definition = TraitDefinition(
            trait=Trait.IDENTIFIABLE,
            protocol_type=Identifiable,
            implementation_type=object,
        )

        # Should not have __dict__ due to slots
        assert not hasattr(definition, "__dict__")

    def test_dependency_validation_performance(self):
        """Test that dependency validation is fast."""
        import time

        # Create definition with many dependencies
        all_traits = set(Trait)
        many_deps = frozenset(list(all_traits)[:10])  # First 10 traits

        definition = TraitDefinition(
            trait=Trait.AUDITABLE,
            protocol_type=Identifiable,  # Placeholder
            implementation_type=object,
            dependencies=many_deps,
        )

        # Test validation performance
        available_traits = all_traits

        start = time.perf_counter()
        for _ in range(1000):
            result = definition.validate_dependencies(available_traits)
            assert result is True

        duration = time.perf_counter() - start
        avg_time = (duration / 1000) * 1_000_000  # μs

        # Should be very fast
        assert avg_time < 10.0, f"Average validation time: {avg_time:.2f}μs"

    def test_weak_reference_overhead(self):
        """Test that weak reference setup has minimal overhead."""
        import time

        class TestClass:
            pass

        # Measure creation time with weak references
        start = time.perf_counter()

        for _ in range(1000):
            definition = TraitDefinition(
                trait=Trait.IDENTIFIABLE,
                protocol_type=Identifiable,
                implementation_type=TestClass,
            )
            assert definition.is_alive

        duration = time.perf_counter() - start
        avg_time = (duration / 1000) * 1_000_000  # μs

        # Should be fast even with weak reference setup
        assert avg_time < 50.0, f"Average creation time: {avg_time:.2f}μs"
