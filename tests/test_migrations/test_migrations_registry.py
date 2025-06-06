"""
Tests for migration registry in pydapter.migrations.registry.
"""

from typing import Any, ClassVar, Optional

import pytest
from pydapter.exceptions import AdapterNotFoundError, ConfigurationError
from pydapter.migrations.protocols import MigrationProtocol
from pydapter.migrations.registry import MigrationRegistry


class TestMigrationRegistry:
    """Test the MigrationRegistry class."""

    def test_initialization(self):
        """Test initialization of the registry."""
        registry = MigrationRegistry()
        assert registry._reg == {}

    def test_registration(self):
        """Test registration of migration adapters."""
        registry = MigrationRegistry()

        # Create a test adapter
        class TestAdapter:
            migration_key: ClassVar[str] = "test"

            @classmethod
            def init_migrations(cls, directory: str, **kwargs) -> None:
                return None

            @classmethod
            def create_migration(
                cls, message: str, autogenerate: bool = True, **kwargs
            ) -> str:
                return "revision123"

            @classmethod
            def upgrade(cls, revision: str = "head", **kwargs) -> None:
                return None

            @classmethod
            def downgrade(cls, revision: str, **kwargs) -> None:
                return None

            @classmethod
            def get_current_revision(cls, **kwargs) -> Optional[str]:
                return "revision123"

            @classmethod
            def get_migration_history(cls, **kwargs) -> list[dict[str, Any]]:
                return [{"revision": "revision123", "message": "test migration"}]

        # Register the adapter
        registry.register(TestAdapter)

        # Check that the adapter is registered
        assert registry.get("test") == TestAdapter

    def test_registration_with_duplicate_key(self):
        """Test registration with a duplicate key."""
        registry = MigrationRegistry()

        # Create two test adapters with the same key
        class TestAdapter1:
            migration_key: ClassVar[str] = "test"

            @classmethod
            def init_migrations(cls, directory: str, **kwargs) -> None:
                return None

            @classmethod
            def create_migration(
                cls, message: str, autogenerate: bool = True, **kwargs
            ) -> str:
                return "revision123"

            @classmethod
            def upgrade(cls, revision: str = "head", **kwargs) -> None:
                return None

            @classmethod
            def downgrade(cls, revision: str, **kwargs) -> None:
                return None

            @classmethod
            def get_current_revision(cls, **kwargs) -> Optional[str]:
                return "revision123"

            @classmethod
            def get_migration_history(cls, **kwargs) -> list[dict[str, Any]]:
                return [{"revision": "revision123", "message": "test migration"}]

        class TestAdapter2:
            migration_key: ClassVar[str] = "test"

            @classmethod
            def init_migrations(cls, directory: str, **kwargs) -> None:
                return None

            @classmethod
            def create_migration(
                cls, message: str, autogenerate: bool = True, **kwargs
            ) -> str:
                return "revision456"

            @classmethod
            def upgrade(cls, revision: str = "head", **kwargs) -> None:
                return None

            @classmethod
            def downgrade(cls, revision: str, **kwargs) -> None:
                return None

            @classmethod
            def get_current_revision(cls, **kwargs) -> Optional[str]:
                return "revision456"

            @classmethod
            def get_migration_history(cls, **kwargs) -> list[dict[str, Any]]:
                return [{"revision": "revision456", "message": "test migration"}]

        # Register the first adapter
        registry.register(TestAdapter1)

        # Register the second adapter (should overwrite the first)
        registry.register(TestAdapter2)

        # Check that the second adapter is registered
        adapter = registry.get("test")
        assert adapter == TestAdapter2
        assert adapter.get_current_revision() == "revision456"

    def test_get_nonexistent_adapter(self):
        """Test getting a nonexistent adapter."""
        registry = MigrationRegistry()

        # Try to get a nonexistent adapter
        with pytest.raises(AdapterNotFoundError) as exc_info:
            registry.get("nonexistent")

        assert "No migration adapter registered for 'nonexistent'" in str(
            exc_info.value
        )

    def test_get_all_adapters(self):
        """Test getting all registered adapters."""
        registry = MigrationRegistry()

        # Create test adapters
        class TestAdapter1:
            migration_key: ClassVar[str] = "test1"

            @classmethod
            def init_migrations(cls, directory: str, **kwargs) -> None:
                return None

            @classmethod
            def create_migration(
                cls, message: str, autogenerate: bool = True, **kwargs
            ) -> str:
                return "revision123"

            @classmethod
            def upgrade(cls, revision: str = "head", **kwargs) -> None:
                return None

            @classmethod
            def downgrade(cls, revision: str, **kwargs) -> None:
                return None

            @classmethod
            def get_current_revision(cls, **kwargs) -> Optional[str]:
                return "revision123"

            @classmethod
            def get_migration_history(cls, **kwargs) -> list[dict[str, Any]]:
                return [{"revision": "revision123", "message": "test migration"}]

        class TestAdapter2:
            migration_key: ClassVar[str] = "test2"

            @classmethod
            def init_migrations(cls, directory: str, **kwargs) -> None:
                return None

            @classmethod
            def create_migration(
                cls, message: str, autogenerate: bool = True, **kwargs
            ) -> str:
                return "revision456"

            @classmethod
            def upgrade(cls, revision: str = "head", **kwargs) -> None:
                return None

            @classmethod
            def downgrade(cls, revision: str, **kwargs) -> None:
                return None

            @classmethod
            def get_current_revision(cls, **kwargs) -> Optional[str]:
                return "revision456"

            @classmethod
            def get_migration_history(cls, **kwargs) -> list[dict[str, Any]]:
                return [{"revision": "revision456", "message": "test migration"}]

        # Register the adapters
        registry.register(TestAdapter1)
        registry.register(TestAdapter2)

        # Get adapters
        adapter1 = registry.get("test1")
        adapter2 = registry.get("test2")
        assert adapter1 == TestAdapter1
        assert adapter2 == TestAdapter2

    def test_registration_with_invalid_adapter(self):
        """Test registration with an invalid adapter."""
        registry = MigrationRegistry()

        # Create an invalid adapter (missing migration_key)
        class InvalidAdapter:
            # Missing migration_key

            @classmethod
            def init_migrations(cls, directory: str, **kwargs) -> None:
                return None

            @classmethod
            def create_migration(
                cls, message: str, autogenerate: bool = True, **kwargs
            ) -> str:
                return "revision123"

            @classmethod
            def upgrade(cls, revision: str = "head", **kwargs) -> None:
                return None

            @classmethod
            def downgrade(cls, revision: str, **kwargs) -> None:
                return None

            @classmethod
            def get_current_revision(cls, **kwargs) -> Optional[str]:
                return "revision123"

            @classmethod
            def get_migration_history(cls, **kwargs) -> list[dict[str, Any]]:
                return [{"revision": "revision123", "message": "test migration"}]

        # Try to register the invalid adapter
        with pytest.raises(ConfigurationError) as exc_info:
            registry.register(InvalidAdapter)

        assert "Migration adapter must define 'migration_key'" in str(exc_info.value)

    def test_singleton_behavior(self):
        """Test that the registry behaves like a singleton."""
        registry1 = MigrationRegistry()
        registry2 = MigrationRegistry()

        # Create a test adapter
        class TestAdapter:
            migration_key: ClassVar[str] = "test"

            @classmethod
            def init_migrations(cls, directory: str, **kwargs) -> None:
                return None

            @classmethod
            def create_migration(
                cls, message: str, autogenerate: bool = True, **kwargs
            ) -> str:
                return "revision123"

            @classmethod
            def upgrade(cls, revision: str = "head", **kwargs) -> None:
                return None

            @classmethod
            def downgrade(cls, revision: str, **kwargs) -> None:
                return None

            @classmethod
            def get_current_revision(cls, **kwargs) -> Optional[str]:
                return "revision123"

            @classmethod
            def get_migration_history(cls, **kwargs) -> list[dict[str, Any]]:
                return [{"revision": "revision123", "message": "test migration"}]

        # Register the adapter with the first registry
        registry1.register(TestAdapter)

        # Check that the adapter is registered in the first registry
        assert registry1.get("test") == TestAdapter

        # Register the adapter with the second registry
        registry2.register(TestAdapter)
        assert registry2.get("test") == TestAdapter

    def test_protocol_compliance(self):
        """Test that registered adapters comply with the MigrationProtocol."""
        registry = MigrationRegistry()

        # Create a test adapter that complies with the protocol
        class CompliantAdapter:
            migration_key: ClassVar[str] = "compliant"

            @classmethod
            def init_migrations(cls, directory: str, **kwargs) -> None:
                return None

            @classmethod
            def create_migration(
                cls, message: str, autogenerate: bool = True, **kwargs
            ) -> str:
                return "revision123"

            @classmethod
            def upgrade(cls, revision: str = "head", **kwargs) -> None:
                return None

            @classmethod
            def downgrade(cls, revision: str, **kwargs) -> None:
                return None

            @classmethod
            def get_current_revision(cls, **kwargs) -> Optional[str]:
                return "revision123"

            @classmethod
            def get_migration_history(cls, **kwargs) -> list[dict[str, Any]]:
                return [{"revision": "revision123", "message": "test migration"}]

        # Register the adapter
        registry.register(CompliantAdapter)

        # Check that the adapter complies with the protocol
        adapter = registry.get("compliant")
        assert isinstance(adapter(), MigrationProtocol)

    def test_clear_registry(self):
        """Test clearing the registry."""
        registry = MigrationRegistry()

        # Create a test adapter
        class TestAdapter:
            migration_key: ClassVar[str] = "test"

            @classmethod
            def init_migrations(cls, directory: str, **kwargs) -> None:
                return None

            @classmethod
            def create_migration(
                cls, message: str, autogenerate: bool = True, **kwargs
            ) -> str:
                return "revision123"

            @classmethod
            def upgrade(cls, revision: str = "head", **kwargs) -> None:
                return None

            @classmethod
            def downgrade(cls, revision: str, **kwargs) -> None:
                return None

            @classmethod
            def get_current_revision(cls, **kwargs) -> Optional[str]:
                return "revision123"

            @classmethod
            def get_migration_history(cls, **kwargs) -> list[dict[str, Any]]:
                return [{"revision": "revision123", "message": "test migration"}]

        # Register the adapter
        registry.register(TestAdapter)

        # Verify the adapter is registered
        adapter = registry.get("test")
        assert adapter == TestAdapter

        # Create a new registry
        new_registry = MigrationRegistry()

        # Verify the adapter is not in the new registry

        # Try to get the adapter from the new registry
        with pytest.raises(AdapterNotFoundError):
            new_registry.get("test")
