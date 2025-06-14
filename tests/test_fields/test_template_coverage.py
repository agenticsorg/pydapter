"""
Additional tests for FieldTemplate to improve coverage.

Tests edge cases and specific scenarios not covered by main tests.
"""

import threading
from unittest.mock import MagicMock, patch

import pytest

from pydapter.fields.template import (
    _MAX_CACHE_SIZE,
    FieldMeta,
    FieldTemplate,
    ValidationError,
    _annotated_cache,
)


class TestFieldMetaEdgeCases:
    """Test edge cases in FieldMeta."""

    def test_fieldmeta_hash_with_callable(self):
        """Test FieldMeta hashing with callable values."""

        # Callable that is hashable (function)
        def validator(x):
            return x > 0

        meta1 = FieldMeta("validator", validator)
        meta2 = FieldMeta("validator", validator)
        assert hash(meta1) == hash(meta2)

        # Test with different callables
        def other_validator(x):
            return x < 0

        meta3 = FieldMeta("validator", other_validator)
        assert hash(meta1) != hash(meta3)

    def test_fieldmeta_hash_with_unhashable(self):
        """Test FieldMeta hashing with unhashable values."""
        # List is unhashable
        meta1 = FieldMeta("items", [1, 2, 3])
        meta2 = FieldMeta("items", [1, 2, 3])

        # Should use id() for unhashable types
        # Hash will be different even for equal lists
        assert isinstance(hash(meta1), int)
        assert isinstance(hash(meta2), int)

    def test_fieldmeta_eq_with_unhashable(self):
        """Test FieldMeta equality with unhashable values."""
        list1 = [1, 2, 3]
        list2 = [1, 2, 3]
        list3 = [4, 5, 6]

        meta1 = FieldMeta("items", list1)
        meta2 = FieldMeta("items", list2)
        meta3 = FieldMeta("items", list3)

        # Lists are compared by value
        assert meta1 == meta2
        assert meta1 != meta3

    def test_fieldmeta_eq_different_types(self):
        """Test FieldMeta equality with different types."""
        meta = FieldMeta("key", "value")
        assert meta != "not a FieldMeta"
        assert meta != 123
        assert meta is not None

    def test_fieldmeta_special_hash_cases(self):
        """Test FieldMeta hash with various special cases."""
        # None value
        meta_none = FieldMeta("nullable", None)
        assert isinstance(hash(meta_none), int)

        # Complex nested structure
        nested = {"key": [1, 2, {"inner": "value"}]}
        meta_nested = FieldMeta("config", nested)
        assert isinstance(hash(meta_nested), int)


class TestFieldTemplateEdgeCases:
    """Test edge cases in FieldTemplate."""

    def test_annotated_cache_eviction(self):
        """Test cache eviction when cache is full."""
        # Clear cache first
        _annotated_cache.clear()

        # Fill cache beyond limit
        templates = []
        for i in range(_MAX_CACHE_SIZE + 10):
            template = FieldTemplate(str, (FieldMeta(f"key{i}", f"value{i}"),))
            annotated = template.annotated()
            templates.append((template, annotated))

        # Cache should not exceed max size
        assert len(_annotated_cache) <= _MAX_CACHE_SIZE

        # Most recent items should still be in cache
        # Check last few items
        for template, _ in templates[-5:]:
            cache_key = (template.base_type, template.metadata)
            assert cache_key in _annotated_cache

    def test_annotated_cache_race_condition(self):
        """Test cache eviction race condition handling."""
        # This tests the KeyError handling in cache eviction
        # Clear cache
        _annotated_cache.clear()

        # Create a template
        FieldTemplate(str, (FieldMeta("key", "value"),))

        # Mock the cache to simulate race condition
        original_popitem = _annotated_cache.popitem

        call_count = 0

        def mock_popitem(last=True):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call: clear the cache to simulate race
                _annotated_cache.clear()
                raise KeyError("Simulated race condition")
            return original_popitem(last)

        with patch.object(_annotated_cache, "popitem", side_effect=mock_popitem):
            # Fill cache to trigger eviction
            for i in range(_MAX_CACHE_SIZE + 5):
                t = FieldTemplate(str, (FieldMeta(f"k{i}", f"v{i}"),))
                t.annotated()

        # Should handle the race condition gracefully
        assert call_count >= 1

    def test_validate_early_exit(self):
        """Test validate method early exit when no validators."""
        template = FieldTemplate(str, (FieldMeta("description", "test"),))

        # Should exit early without checking metadata
        template.validate("test value")  # Should not raise

    def test_validate_with_unnamed_validator(self):
        """Test validate with validator that has no __name__."""
        # Create validator without __name__
        validator = MagicMock(return_value=False)
        del validator.__name__  # Remove __name__ attribute

        template = FieldTemplate(str, (FieldMeta("validator", validator),))

        with pytest.raises(ValidationError) as exc_info:
            template.validate("test", "field_name")

        # Should use fallback name
        assert "validator_0" in str(exc_info.value)

    def test_field_template_properties(self):
        """Test FieldTemplate property methods."""
        # Test with empty metadata
        template = FieldTemplate(int, ())
        assert template.base_type is int
        assert len(template.metadata) == 0
        assert not template.is_nullable
        assert not template.is_listable

        # Test nullable property
        nullable_template = FieldTemplate(str, (FieldMeta("nullable", True),))
        assert nullable_template.is_nullable

        # Test listable property
        list_template = FieldTemplate(int, (FieldMeta("listable", True),))
        assert list_template.is_listable


class TestThreadSafety:
    """Test thread safety of cache operations."""

    def test_concurrent_cache_access(self):
        """Test concurrent access to annotated cache."""
        _annotated_cache.clear()
        results = []
        errors = []

        def worker(worker_id):
            try:
                for i in range(50):
                    template = FieldTemplate(
                        str, (FieldMeta(f"worker{worker_id}", f"value{i}"),)
                    )
                    annotated = template.annotated()
                    results.append((worker_id, annotated))
            except Exception as e:  # noqa: BLE001
                errors.append(e)

        threads = []
        for i in range(5):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Should have no errors
        assert len(errors) == 0
        # Should have results from all workers
        assert len(results) == 250  # 5 workers * 50 iterations


class TestValidationScenarios:
    """Test various validation scenarios."""

    def test_multiple_validators_partial_failure(self):
        """Test validation with multiple validators where one fails."""

        def validator1(x):
            return x > 0

        def validator2(x):
            return x < 10

        def validator3(x):
            return x % 2 == 0

        template = FieldTemplate(
            int,
            (
                FieldMeta("validator", validator1),
                FieldMeta("validator", validator2),
                FieldMeta("validator", validator3),
            ),
        )

        # Test value that passes first two but fails third
        assert template.is_valid(4) is True  # Passes all
        assert template.is_valid(5) is False  # Fails validator3
        assert template.is_valid(11) is False  # Fails validator2
        assert template.is_valid(-1) is False  # Fails validator1

    def test_validation_error_context(self):
        """Test ValidationError includes proper context."""

        def named_validator(x):
            return x > 0

        template = FieldTemplate(int, (FieldMeta("validator", named_validator),))

        with pytest.raises(ValidationError) as exc_info:
            template.validate(-5, "age_field")

        error = exc_info.value
        assert error.field_name == "age_field"
        assert error.value == -5
        assert error.validator_name == "named_validator"
