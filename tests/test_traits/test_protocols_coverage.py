"""
Additional tests for protocol implementations to improve coverage.

This module tests concrete implementations and edge cases in protocols.py
that aren't covered by the main test file.
"""

import time

from pydapter.traits.protocols import Hashable, Identifiable, Operable, Temporal


class TestProtocolImplementations:
    """Test concrete implementations in protocol classes."""

    def test_identifiable_same_identity(self):
        """Test Identifiable.same_identity method."""

        class MyIdentifiable:
            id = "test-123"
            id_type = "test"

            def same_identity(self, other: object) -> bool:
                return Identifiable.same_identity(self, other)

        obj1 = MyIdentifiable()
        obj2 = MyIdentifiable()
        obj3 = MyIdentifiable()
        obj3.id = "different-123"

        assert obj1.same_identity(obj2) is True
        assert obj1.same_identity(obj3) is False
        assert obj1.same_identity("not-identifiable") is False

    def test_temporal_age_seconds(self):
        """Test Temporal.age_seconds method."""

        class MyTemporal:
            def __init__(self):
                self.created_at = time.time() - 10.0  # 10 seconds ago
                self.updated_at = time.time()

            def age_seconds(self) -> float:
                return Temporal.age_seconds(self)

            def is_modified(self) -> bool:
                return Temporal.is_modified(self)

        obj = MyTemporal()
        age = obj.age_seconds()
        assert 9.9 < age < 10.1  # Allow for small timing variations
        assert obj.is_modified() is True  # updated_at > created_at

    def test_hashable_verify_hash_stability(self):
        """Test Hashable.verify_hash_stability method."""

        class MyHashable:
            @property
            def hash_fields(self) -> tuple[str, ...]:
                return ("id", "value")

            def __hash__(self) -> int:
                return hash("stable-hash")

            def verify_hash_stability(self) -> bool:
                return Hashable.verify_hash_stability(self)

        class UnstableHashable:
            counter = 0

            @property
            def hash_fields(self) -> tuple[str, ...]:
                return ("counter",)

            def __hash__(self) -> int:
                self.counter += 1
                return hash(f"hash-{self.counter}")

            def verify_hash_stability(self) -> bool:
                return Hashable.verify_hash_stability(self)

        stable = MyHashable()
        assert stable.verify_hash_stability() is True

        unstable = UnstableHashable()
        assert unstable.verify_hash_stability() is False

    def test_operable_supports_operation(self):
        """Test Operable.supports_operation method."""

        class MyOperable:
            def apply_operation(self, operation: str, **kwargs):
                if operation == "supported":
                    return "result"
                raise NotImplementedError

            def get_supported_operations(self) -> list[str]:
                return ["supported", "another"]

            def supports_operation(self, operation: str) -> bool:
                return Operable.supports_operation(self, operation)

        obj = MyOperable()
        assert obj.supports_operation("supported") is True
        assert obj.supports_operation("unsupported") is False


class TestProtocolEdgeCases:
    """Test edge cases and error conditions in protocols."""

    def test_identifiable_same_identity_without_id(self):
        """Test same_identity with objects missing id attribute."""

        class PartialIdentifiable:
            id_type = "test"

            def same_identity(self, other: object) -> bool:
                return Identifiable.same_identity(self, other)

        obj = PartialIdentifiable()
        assert obj.same_identity(obj) is False
