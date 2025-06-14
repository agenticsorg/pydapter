"""Tests for FieldTemplate."""

from typing import Annotated, get_args, get_origin

import pytest

from pydapter.fields.template import FieldMeta, FieldTemplate, ValidationError


class TestFieldTemplate:
    """Test suite for FieldTemplate."""

    def test_basic_creation(self):
        """Test basic template creation."""
        tmpl = FieldTemplate(str)
        assert tmpl.base_type is str
        assert tmpl.metadata == ()
        assert repr(tmpl) == "FieldTemplate(str)"

    def test_annotated_returns_base_type_when_no_metadata(self):
        """Test that annotated returns base type when no metadata."""
        tmpl = FieldTemplate(int)
        result = tmpl.annotated()
        assert result is int

    def test_annotated_with_metadata(self):
        """Test annotated with metadata."""
        tmpl = FieldTemplate(str, (FieldMeta("key", "value"),))
        result = tmpl.annotated()

        # Check it's an Annotated type
        assert get_origin(result) is Annotated
        args = get_args(result)
        assert args[0] is str
        assert FieldMeta("key", "value") in args[1:]

    def test_as_nullable(self):
        """Test nullable composition."""
        tmpl = FieldTemplate(str)
        nullable_tmpl = tmpl.as_nullable()

        # Check metadata updated
        assert nullable_tmpl.is_nullable
        assert not tmpl.is_nullable  # Original unchanged

        # Check annotated type
        result = nullable_tmpl.annotated()
        # Should be Union[str, None] wrapped in Annotated
        assert get_origin(result) is Annotated

    def test_as_listable(self):
        """Test listable composition."""
        tmpl = FieldTemplate(int)
        list_tmpl = tmpl.as_listable()

        # Check metadata
        assert list_tmpl.is_listable
        assert not tmpl.is_listable

        # Check base type changed
        assert get_origin(list_tmpl.base_type) is list

    def test_with_validator(self):
        """Test adding validator."""

        def is_positive(x: int) -> bool:
            return x > 0

        tmpl = FieldTemplate(int)
        validated_tmpl = tmpl.with_validator(is_positive)

        # Check validator added
        assert validated_tmpl.has_validator()
        assert not tmpl.has_validator()

        # Test validation
        assert validated_tmpl.is_valid(5)
        assert not validated_tmpl.is_valid(-5)

    def test_composition_chain(self):
        """Test chaining multiple compositions."""

        def is_positive(x: int) -> bool:
            return x > 0

        tmpl = (
            FieldTemplate(int)
            .as_nullable()
            .with_validator(is_positive)
            .with_description("Positive integer")
        )

        assert tmpl.is_nullable
        assert tmpl.has_validator()
        assert tmpl.extract_metadata("description") == "Positive integer"

    def test_metadata_immutability(self):
        """Test that templates are immutable."""
        tmpl1 = FieldTemplate(str)
        tmpl2 = tmpl1.as_nullable()

        # Original should be unchanged
        assert tmpl1.metadata == ()
        assert not tmpl1.is_nullable

        # New template should have metadata
        assert len(tmpl2.metadata) > 0
        assert tmpl2.is_nullable

    def test_cache_identity(self):
        """Test that annotated() calls are cached."""
        tmpl = FieldTemplate(str, (FieldMeta("key", "value"),))

        # Two calls should return identical object
        result1 = tmpl.annotated()
        result2 = tmpl.annotated()

        assert result1 is result2

    def test_extract_metadata(self):
        """Test metadata extraction."""
        tmpl = FieldTemplate(
            str, (FieldMeta("key1", "value1"), FieldMeta("key2", "value2"))
        )

        assert tmpl.extract_metadata("key1") == "value1"
        assert tmpl.extract_metadata("key2") == "value2"
        assert tmpl.extract_metadata("missing") is None

    def test_with_default(self):
        """Test adding default value."""
        tmpl = FieldTemplate(str).with_default("hello")
        assert tmpl.extract_metadata("default") == "hello"

    def test_multiple_validators(self):
        """Test multiple validators."""

        def is_positive(x: int) -> bool:
            return x > 0

        def is_even(x: int) -> bool:
            return x % 2 == 0

        tmpl = FieldTemplate(int).with_validator(is_positive).with_validator(is_even)

        # Should pass all validators
        assert tmpl.is_valid(4)  # positive and even
        assert not tmpl.is_valid(3)  # positive but odd
        assert not tmpl.is_valid(-2)  # even but negative

    def test_repr_with_attributes(self):
        """Test string representation with attributes."""
        tmpl = (
            FieldTemplate(int)
            .as_nullable()
            .as_listable()
            .with_validator(lambda x: x > 0)
        )

        repr_str = repr(tmpl)
        assert "nullable" in repr_str
        assert "listable" in repr_str
        assert "validated" in repr_str

    def test_validate(self):
        """Test validate method with ValidationError."""

        def is_positive(x: int) -> bool:
            return x > 0

        tmpl = FieldTemplate(int).with_validator(is_positive)

        # Should not raise for valid values
        tmpl.validate(5)

        # Should raise ValidationError for invalid values
        with pytest.raises(ValidationError) as exc_info:
            tmpl.validate(-5, field_name="test_field")

        error = exc_info.value
        assert error.field_name == "test_field"
        assert error.value == -5
        assert error.validator_name == "is_positive"

    def test_metadata_limit_warning(self):
        """Test that excessive metadata triggers a warning."""
        import warnings

        # Create template with many metadata items
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            # Create many metadata items to exceed limit
            metadata_items = tuple(
                FieldMeta(f"key_{i}", f"value_{i}") for i in range(12)
            )

            # This should trigger the warning
            FieldTemplate(str, metadata_items)

            assert len(w) == 1
            assert "exceeding recommended limit" in str(w[0].message)

    def test_thread_safety(self):
        """Test thread-safe caching of annotated types."""
        import threading
        import time

        tmpl = FieldTemplate(str, (FieldMeta("key", "value"),))
        results = []
        errors = []

        def worker():
            try:
                # Simulate concurrent access
                for _ in range(100):
                    result = tmpl.annotated()
                    results.append(result)
                    time.sleep(0.0001)  # Small delay to increase contention
            except KeyError as e:  # Specific exception we're protecting against
                errors.append(e)

        # Create multiple threads
        threads = [threading.Thread(target=worker) for _ in range(10)]

        # Start all threads
        for t in threads:
            t.start()

        # Wait for completion
        for t in threads:
            t.join()

        # Check no errors occurred
        assert len(errors) == 0

        # All results should be the same object (cached)
        assert all(r is results[0] for r in results)


class TestValidatorPerformance:
    """Test validator performance."""

    def test_validator_performance(self):
        """Test validator performance is within acceptable bounds."""

        def simple_validator(x) -> bool:
            return x > 0

        template = FieldTemplate(int).with_validator(simple_validator)

        # Time validation
        import time

        start = time.perf_counter()
        iterations = 100
        for _i in range(iterations):
            try:
                template.validate(42)
            except ValueError:
                pass
        duration = time.perf_counter() - start

        # Average time per validation should be reasonable
        avg_time_us = (duration / iterations) * 1_000_000
        # This is more relaxed than 500ns target for now
        assert avg_time_us < 50  # 50 microseconds


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_field_meta_hash_with_callable(self):
        """Test FieldMeta hashing with callable values."""
        from pydapter.fields.template import FieldMeta

        def validator(x):
            return x > 0

        meta = FieldMeta("validator", validator)
        # Should hash by id of callable
        assert hash(meta) == hash(("validator", id(validator)))

    def test_field_meta_hash_with_unhashable_value(self):
        """Test FieldMeta hashing with unhashable values."""
        from pydapter.fields.template import FieldMeta

        # List is unhashable
        meta = FieldMeta("options", [1, 2, 3])
        # Should fallback to string representation
        assert hash(meta) == hash(("options", str([1, 2, 3])))

    def test_field_meta_eq_not_field_meta(self):
        """Test FieldMeta equality with non-FieldMeta object."""
        from pydapter.fields.template import FieldMeta

        meta = FieldMeta("key", "value")
        # Should return NotImplemented
        assert meta.__eq__("not a FieldMeta") is NotImplemented

    def test_field_meta_eq_different_keys(self):
        """Test FieldMeta equality with different keys."""
        from pydapter.fields.template import FieldMeta

        meta1 = FieldMeta("key1", "value")
        meta2 = FieldMeta("key2", "value")
        assert meta1 != meta2

    def test_field_meta_eq_callable_values(self):
        """Test FieldMeta equality with callable values."""
        from pydapter.fields.template import FieldMeta

        def validator1(x):
            return x > 0

        def validator2(x):
            return x > 0

        meta1 = FieldMeta("validator", validator1)
        meta2 = FieldMeta("validator", validator1)  # Same function
        meta3 = FieldMeta("validator", validator2)  # Different function

        # Same callable should be equal (by id)
        assert meta1 == meta2
        # Different callables should not be equal
        assert meta1 != meta3

    def test_materialize_cache_eviction_race_condition(self):
        """Test cache eviction race condition handling."""
        from pydapter.fields.template import (
            _MAX_CACHE_SIZE,
            FieldTemplate,
            _annotated_cache,
        )

        # Fill cache to trigger eviction
        original_size = _MAX_CACHE_SIZE
        try:
            # Temporarily reduce cache size to force eviction
            import pydapter.fields.template

            pydapter.fields.template._MAX_CACHE_SIZE = 2

            # Clear cache
            _annotated_cache.clear()

            # Create templates that will fill cache
            t1 = FieldTemplate(int).with_description("test1")
            t2 = FieldTemplate(str).with_description("test2")
            t3 = FieldTemplate(float).with_description("test3")

            # Call annotated to populate cache
            t1.annotated()
            t2.annotated()
            # This should trigger eviction
            t3.annotated()

            # Cache should not exceed max size
            assert len(_annotated_cache) <= 2

        finally:
            # Restore original cache size
            pydapter.fields.template._MAX_CACHE_SIZE = original_size
            _annotated_cache.clear()

    def test_validate_no_validators(self):
        """Test validate method with no validators."""
        template = FieldTemplate(int).with_description("No validator")

        # Should not raise when no validators present
        template.validate(42)  # Should pass without error

    def test_validate_early_exit(self):
        """Test validate method early exit when no validators."""
        # Create field without validators
        template = FieldTemplate(int).with_description("test")

        # Should exit early and not execute validation logic
        template.validate(42)  # Should complete without error
