"""
Tests for TraitComposer functionality.

This module tests the algebraic trait composition system with
LRU caching for fast model generation.
"""

import pytest

from pydapter.traits import (
    Trait,
    TraitComposer,
    TraitComposition,
    compose,
    create_trait_composition,
    generate_model,
)
from pydapter.traits.composer import CompositionError


class TestTraitComposition:
    """Test TraitComposition algebraic operations."""

    def test_composition_creation(self):
        """Test creating trait compositions."""
        composition = TraitComposition(
            traits=frozenset([Trait.IDENTIFIABLE, Trait.TEMPORAL])
        )

        assert Trait.IDENTIFIABLE in composition.traits
        assert Trait.TEMPORAL in composition.traits
        assert len(composition.traits) == 2

    def test_composition_union(self):
        """Test trait composition union (+) operation."""
        comp1 = TraitComposition(traits=frozenset([Trait.IDENTIFIABLE]))
        comp2 = TraitComposition(traits=frozenset([Trait.TEMPORAL]))

        result = comp1 + comp2

        assert Trait.IDENTIFIABLE in result.traits
        assert Trait.TEMPORAL in result.traits
        assert len(result.traits) == 2

    def test_composition_union_with_trait(self):
        """Test composition union with individual trait."""
        comp = TraitComposition(traits=frozenset([Trait.IDENTIFIABLE]))

        result = comp + Trait.TEMPORAL

        assert Trait.IDENTIFIABLE in result.traits
        assert Trait.TEMPORAL in result.traits
        assert len(result.traits) == 2

    def test_composition_intersection(self):
        """Test trait composition intersection (&) operation."""
        comp1 = TraitComposition(traits=frozenset([Trait.IDENTIFIABLE, Trait.TEMPORAL]))
        comp2 = TraitComposition(traits=frozenset([Trait.IDENTIFIABLE, Trait.HASHABLE]))

        result = comp1 & comp2

        assert Trait.IDENTIFIABLE in result.traits
        assert Trait.TEMPORAL not in result.traits
        assert Trait.HASHABLE not in result.traits
        assert len(result.traits) == 1

    def test_composition_or_operator(self):
        """Test composition | operator (alias for +)."""
        comp1 = TraitComposition(traits=frozenset([Trait.IDENTIFIABLE]))
        comp2 = TraitComposition(traits=frozenset([Trait.TEMPORAL]))

        result = comp1 | comp2

        assert Trait.IDENTIFIABLE in result.traits
        assert Trait.TEMPORAL in result.traits
        assert len(result.traits) == 2

    def test_composition_hash_and_equality(self):
        """Test composition hashing for caching."""
        comp1 = TraitComposition(traits=frozenset([Trait.IDENTIFIABLE, Trait.TEMPORAL]))
        comp2 = TraitComposition(traits=frozenset([Trait.TEMPORAL, Trait.IDENTIFIABLE]))

        # Same traits in different order should have same hash
        assert hash(comp1) == hash(comp2)

        # Can be used in sets/dicts
        composition_set = {comp1, comp2}
        assert len(composition_set) == 1

    def test_composition_id_generation(self):
        """Test deterministic composition ID generation."""
        comp = TraitComposition(traits=frozenset([Trait.TEMPORAL, Trait.IDENTIFIABLE]))

        # Should be sorted alphabetically
        assert comp.composition_id == "IDENTIFIABLE+TEMPORAL"

    def test_composition_string_representation(self):
        """Test composition string representation."""
        comp = TraitComposition(traits=frozenset([Trait.IDENTIFIABLE, Trait.TEMPORAL]))

        repr_str = repr(comp)
        assert "TraitComposition" in repr_str
        assert "IDENTIFIABLE" in repr_str
        assert "TEMPORAL" in repr_str

    def test_composition_validation(self):
        """Test composition validation."""
        # Simple composition without dependencies should be valid
        comp = TraitComposition(traits=frozenset([Trait.IDENTIFIABLE]))

        # For now, all compositions are valid (no complex dependencies defined)
        assert comp.is_valid()

    def test_composition_with_dependencies(self):
        """Test composition dependency resolution."""
        comp = TraitComposition(traits=frozenset([Trait.IDENTIFIABLE]))

        # Adding dependencies should work
        with_deps = comp.with_dependencies()
        assert Trait.IDENTIFIABLE in with_deps.traits


class TestTraitComposer:
    """Test TraitComposer functionality."""

    def setup_method(self):
        """Set up fresh composer for each test."""
        TraitComposer.reset()
        self.composer = TraitComposer.get_instance()

    def test_composer_singleton(self):
        """Test composer singleton pattern."""
        composer1 = TraitComposer.get_instance()
        composer2 = TraitComposer.get_instance()

        assert composer1 is composer2

    def test_compose_multiple_traits(self):
        """Test composing multiple traits."""
        composition = self.composer.compose(Trait.IDENTIFIABLE, Trait.TEMPORAL)

        assert Trait.IDENTIFIABLE in composition.traits
        assert Trait.TEMPORAL in composition.traits
        assert len(composition.traits) == 2

    def test_compose_with_compositions(self):
        """Test composing with existing compositions."""
        comp1 = TraitComposition(traits=frozenset([Trait.IDENTIFIABLE]))
        comp2 = TraitComposition(traits=frozenset([Trait.TEMPORAL]))

        result = self.composer.compose(comp1, comp2)

        assert Trait.IDENTIFIABLE in result.traits
        assert Trait.TEMPORAL in result.traits
        assert len(result.traits) == 2

    def test_compose_invalid_type(self):
        """Test composing with invalid types."""
        with pytest.raises(CompositionError):
            self.composer.compose("invalid")

    def test_model_generation_basic(self):
        """Test basic model generation."""
        composition = TraitComposition(traits=frozenset([Trait.IDENTIFIABLE]))

        model_class = self.composer.generate_model(composition)

        assert model_class is not None
        assert hasattr(model_class, "__traits__")
        assert Trait.IDENTIFIABLE in model_class.__traits__
        assert hasattr(model_class, "__composition__")

    def test_model_generation_caching(self):
        """Test model generation caching."""
        composition = TraitComposition(traits=frozenset([Trait.IDENTIFIABLE]))

        # Generate same model twice
        model1 = self.composer.generate_model(composition)
        model2 = self.composer.generate_model(composition)

        # Should be the same class (cached)
        assert model1 is model2

    def test_model_generation_multiple_traits(self):
        """Test generating model with multiple traits."""
        composition = TraitComposition(
            traits=frozenset([Trait.IDENTIFIABLE, Trait.TEMPORAL])
        )

        model_class = self.composer.generate_model(composition)

        assert model_class is not None
        assert len(model_class.__traits__) == 2
        assert Trait.IDENTIFIABLE in model_class.__traits__
        assert Trait.TEMPORAL in model_class.__traits__

    def test_cache_statistics(self):
        """Test cache statistics tracking."""
        composition = TraitComposition(traits=frozenset([Trait.IDENTIFIABLE]))

        # Initial stats
        stats = self.composer.get_cache_stats()
        initial_misses = stats["cache_misses"]

        # Generate model (cache miss)
        self.composer.generate_model(composition)
        stats = self.composer.get_cache_stats()
        assert stats["cache_misses"] == initial_misses + 1

        # Generate same model (cache hit)
        self.composer.generate_model(composition)
        stats = self.composer.get_cache_stats()
        assert stats["cache_hits"] >= 1

    def test_clear_cache(self):
        """Test cache clearing."""
        composition = TraitComposition(traits=frozenset([Trait.IDENTIFIABLE]))

        # Generate model and check cache
        self.composer.generate_model(composition)
        stats = self.composer.get_cache_stats()
        assert stats["cache_size"] > 0

        # Clear cache
        self.composer.clear_cache()
        stats = self.composer.get_cache_stats()
        assert stats["cache_size"] == 0
        assert stats["generations"] == 0


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_compose_function(self):
        """Test global compose function."""
        composition = compose(Trait.IDENTIFIABLE, Trait.TEMPORAL)

        assert Trait.IDENTIFIABLE in composition.traits
        assert Trait.TEMPORAL in composition.traits

    def test_generate_model_function(self):
        """Test global generate_model function."""
        composition = create_trait_composition(Trait.IDENTIFIABLE)

        model_class = generate_model(composition)

        assert model_class is not None
        assert Trait.IDENTIFIABLE in model_class.__traits__

    def test_create_trait_composition_function(self):
        """Test create_trait_composition function."""
        composition = create_trait_composition(Trait.IDENTIFIABLE, Trait.TEMPORAL)

        assert isinstance(composition, TraitComposition)
        assert Trait.IDENTIFIABLE in composition.traits
        assert Trait.TEMPORAL in composition.traits


class TestCompositionPerformance:
    """Test composition performance characteristics."""

    def setup_method(self):
        """Set up fresh composer for performance tests."""
        TraitComposer.reset()
        self.composer = TraitComposer.get_instance()

    def test_model_generation_speed(self):
        """Test that model generation completes in reasonable time."""
        composition = TraitComposition(traits=frozenset([Trait.IDENTIFIABLE]))

        # Should complete without throwing performance warnings in tests
        model_class = self.composer.generate_model(composition)
        assert model_class is not None

    def test_cache_effectiveness(self):
        """Test cache effectiveness with repeated operations."""
        compositions = [
            TraitComposition(traits=frozenset([Trait.IDENTIFIABLE])),
            TraitComposition(traits=frozenset([Trait.TEMPORAL])),
            TraitComposition(traits=frozenset([Trait.IDENTIFIABLE, Trait.TEMPORAL])),
        ]

        # Generate models multiple times
        for _ in range(3):
            for comp in compositions:
                self.composer.generate_model(comp)

        stats = self.composer.get_cache_stats()

        # Should have good hit ratio after repeated operations
        assert stats["cache_hits"] > 0
        assert stats["hit_ratio"] > 0.5  # At least 50% hits


class TestCompositionErrors:
    """Test error handling in composition."""

    def test_missing_protocols(self):
        """Test handling of compositions with missing protocols."""
        # This test depends on the trait definitions having proper protocols
        # For now, all our traits should have protocols, so this should work
        composition = TraitComposition(traits=frozenset([Trait.IDENTIFIABLE]))

        composer = TraitComposer.get_instance()
        model_class = composer.generate_model(composition)
        assert model_class is not None

    def test_invalid_trait_type_in_compose(self):
        """Test composer with invalid trait type."""
        composer = TraitComposer.get_instance()

        with pytest.raises(CompositionError):
            composer.compose("invalid_trait")  # String instead of Trait

    def test_composition_with_dependencies(self):
        """Test composition including dependencies."""
        composition = TraitComposition(traits=frozenset([Trait.IDENTIFIABLE]))

        # Test with_dependencies method
        full_composition = composition.with_dependencies()
        assert isinstance(full_composition, TraitComposition)
        assert Trait.IDENTIFIABLE in full_composition.traits

    def test_composition_missing_dependencies(self):
        """Test getting missing dependencies."""
        composition = TraitComposition(traits=frozenset([Trait.IDENTIFIABLE]))

        missing = composition.get_missing_dependencies()
        assert isinstance(missing, frozenset)

    def test_composition_validation(self):
        """Test composition validation."""
        composition = TraitComposition(traits=frozenset([Trait.IDENTIFIABLE]))

        # Should be valid (no missing dependencies for IDENTIFIABLE)
        assert composition.is_valid() is True

    def test_composition_algebraic_operations(self):
        """Test algebraic operations on compositions."""
        comp1 = TraitComposition(traits=frozenset([Trait.IDENTIFIABLE]))
        comp2 = TraitComposition(traits=frozenset([Trait.TEMPORAL]))

        # Test union
        union = comp1 + comp2
        assert Trait.IDENTIFIABLE in union.traits
        assert Trait.TEMPORAL in union.traits

        # Test intersection
        intersection = comp1 & comp2
        assert len(intersection.traits) == 0  # No common traits

        # Test or operator (alias for union)
        or_result = comp1 | comp2
        assert or_result.traits == union.traits

    def test_composition_with_single_trait(self):
        """Test composition operations with single traits."""
        comp = TraitComposition(traits=frozenset([Trait.IDENTIFIABLE]))

        # Add single trait
        new_comp = comp + Trait.TEMPORAL
        assert Trait.TEMPORAL in new_comp.traits

        # Intersect with single trait
        intersect = comp & Trait.IDENTIFIABLE
        assert Trait.IDENTIFIABLE in intersect.traits

    def test_composition_string_representation(self):
        """Test composition string representation."""
        comp = TraitComposition(traits=frozenset([Trait.IDENTIFIABLE, Trait.TEMPORAL]))

        repr_str = repr(comp)
        assert "TraitComposition" in repr_str
        assert "IDENTIFIABLE" in repr_str or "TEMPORAL" in repr_str

    def test_composition_hash_stability(self):
        """Test composition hash stability."""
        comp1 = TraitComposition(traits=frozenset([Trait.IDENTIFIABLE]))
        comp2 = TraitComposition(traits=frozenset([Trait.IDENTIFIABLE]))

        assert hash(comp1) == hash(comp2)

    def test_composer_singleton_reset(self):
        """Test composer singleton reset."""
        composer1 = TraitComposer.get_instance()
        TraitComposer.reset()
        composer2 = TraitComposer.get_instance()

        # Should be different instances after reset
        assert composer1 is not composer2

    def test_composer_cache_management(self):
        """Test composer cache management."""
        composer = TraitComposer.get_instance()

        # Generate a model to populate cache
        composition = TraitComposition(traits=frozenset([Trait.IDENTIFIABLE]))
        composer.generate_model(composition)

        # Get initial stats
        stats_before = composer.get_cache_stats()
        assert stats_before["cache_size"] > 0

        # Clear cache
        composer.clear_cache()

        # Stats should show empty cache
        stats_after = composer.get_cache_stats()
        assert stats_after["cache_size"] == 0
        assert stats_after["generations"] == 0
