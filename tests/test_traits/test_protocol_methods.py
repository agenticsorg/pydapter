"""Tests for protocol method implementations."""

from unittest.mock import Mock

from pydapter.traits.protocols import Identifiable, Operable, Temporal


class TestProtocolMethods:
    """Test protocol method implementations and contracts."""

    def test_identifiable_same_identity(self):
        """Test Identifiable.same_identity method."""
        # Create mock identifiable objects
        obj1 = Mock()
        obj1.id = "test-123"
        obj1.id_type = "test"

        obj2 = Mock()
        obj2.id = "test-123"
        obj2.id_type = "test"

        obj3 = Mock()
        obj3.id = "different-456"
        obj3.id_type = "test"

        # Test same identity
        assert Identifiable.same_identity(obj1, obj2)

        # Test different identity
        assert not Identifiable.same_identity(obj1, obj3)

        # Test with object missing attributes
        obj_no_attrs = Mock(spec=[])
        assert not Identifiable.same_identity(obj1, obj_no_attrs)

    def test_temporal_age_seconds(self):
        """Test Temporal.age_seconds method."""
        import time

        obj = Mock()
        obj.created_at = time.time() - 100  # 100 seconds ago

        age = Temporal.age_seconds(obj)
        assert 99 <= age <= 101  # Allow for timing variations

    def test_temporal_is_modified(self):
        """Test Temporal.is_modified method."""
        obj = Mock()
        obj.created_at = 1000.0
        obj.updated_at = 1500.0

        assert Temporal.is_modified(obj)

        obj.updated_at = 1000.0
        assert not Temporal.is_modified(obj)

    def test_hashable_verify_hash_stability(self):
        """Test Hashable.verify_hash_stability method."""

        # Create a simple hashable class
        class StableHashable:
            def __hash__(self):
                return 12345

            def verify_hash_stability(self):
                hash1 = hash(self)
                hash2 = hash(self)
                return hash1 == hash2

        obj = StableHashable()
        assert obj.verify_hash_stability()

        # Test unstable hash
        class UnstableHashable:
            def __init__(self):
                self.call_count = 0

            def __hash__(self):
                self.call_count += 1
                return self.call_count

            def verify_hash_stability(self):
                hash1 = hash(self)
                hash2 = hash(self)
                return hash1 == hash2

        unstable_obj = UnstableHashable()
        assert not unstable_obj.verify_hash_stability()

    def test_operable_supports_operation(self):
        """Test Operable.supports_operation method."""
        obj = Mock()
        obj.get_supported_operations.return_value = ["create", "update", "delete"]

        assert Operable.supports_operation(obj, "create")
        assert not Operable.supports_operation(obj, "invalid")


class TestIdentifiableProtocol:
    """Test Identifiable protocol methods."""

    def create_identifiable(self, id_val="test-123", id_type="test"):
        """Create mock identifiable object."""
        obj = Mock()
        obj.id = id_val
        obj.id_type = id_type
        return obj

    def test_same_identity_equal(self):
        """Test same_identity with equal objects."""
        obj1 = self.create_identifiable()
        obj2 = self.create_identifiable()

        result = Identifiable.same_identity(obj1, obj2)
        assert result is True

    def test_same_identity_different_id(self):
        """Test same_identity with different IDs."""
        obj1 = self.create_identifiable("id1")
        obj2 = self.create_identifiable("id2")

        result = Identifiable.same_identity(obj1, obj2)
        assert result is False

    def test_same_identity_different_type(self):
        """Test same_identity with different ID types."""
        obj1 = self.create_identifiable(id_type="type1")
        obj2 = self.create_identifiable(id_type="type2")

        result = Identifiable.same_identity(obj1, obj2)
        assert result is False

    def test_same_identity_missing_attrs(self):
        """Test same_identity with missing attributes."""
        obj1 = self.create_identifiable()
        obj2 = Mock(spec=[])  # No attributes

        result = Identifiable.same_identity(obj1, obj2)
        assert result is False


class TestTemporalProtocol:
    """Test Temporal protocol methods."""

    def create_temporal(self, created=1000.0, updated=1500.0):
        """Create mock temporal object."""
        obj = Mock()
        obj.created_at = created
        obj.updated_at = updated
        return obj

    def test_age_seconds(self):
        """Test age_seconds calculation."""
        import time

        current_time = time.time()
        obj = self.create_temporal(created=current_time - 60)  # 1 minute ago

        age = Temporal.age_seconds(obj)
        assert 59 <= age <= 61  # Allow for timing variations

    def test_is_modified_true(self):
        """Test is_modified returns True for modified objects."""
        obj = self.create_temporal(created=1000.0, updated=2000.0)
        assert Temporal.is_modified(obj) is True

    def test_is_modified_false(self):
        """Test is_modified returns False for unmodified objects."""
        obj = self.create_temporal(created=1000.0, updated=1000.0)
        assert Temporal.is_modified(obj) is False

    def test_is_modified_older_update(self):
        """Test is_modified with update time before creation (edge case)."""
        obj = self.create_temporal(created=2000.0, updated=1000.0)
        assert Temporal.is_modified(obj) is False


class TestHashableProtocol:
    """Test Hashable protocol methods."""

    def test_verify_hash_stability_stable(self):
        """Test verify_hash_stability with stable hash."""

        class StableClass:
            def __hash__(self):
                return 42

            def verify_hash_stability(self):
                hash1 = hash(self)
                hash2 = hash(self)
                return hash1 == hash2

        obj = StableClass()
        result = obj.verify_hash_stability()
        assert result is True

    def test_verify_hash_stability_unstable(self):
        """Test verify_hash_stability with unstable hash."""

        class UnstableClass:
            def __init__(self):
                self.count = 0

            def __hash__(self):
                self.count += 1
                return self.count

            def verify_hash_stability(self):
                hash1 = hash(self)
                hash2 = hash(self)
                return hash1 == hash2

        obj = UnstableClass()
        result = obj.verify_hash_stability()
        assert result is False


class TestOperableProtocol:
    """Test Operable protocol methods."""

    def create_operable(self, operations=None):
        """Create mock operable object."""
        if operations is None:
            operations = ["create", "read", "update", "delete"]

        obj = Mock()
        obj.get_supported_operations.return_value = operations
        return obj

    def test_supports_operation_exists(self):
        """Test supports_operation with existing operation."""
        obj = self.create_operable()
        assert Operable.supports_operation(obj, "create") is True

    def test_supports_operation_missing(self):
        """Test supports_operation with missing operation."""
        obj = self.create_operable()
        assert Operable.supports_operation(obj, "invalid") is False

    def test_supports_operation_empty_list(self):
        """Test supports_operation with empty operations list."""
        obj = self.create_operable(operations=[])
        assert Operable.supports_operation(obj, "create") is False
