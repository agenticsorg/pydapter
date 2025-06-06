"""
Tests for base migration adapter classes in pydapter.migrations.base.
"""

import os
from typing import Any, ClassVar, Optional

import pytest
from pydapter.migrations.base import (
    AsyncMigrationAdapter,
    BaseMigrationAdapter,
    SyncMigrationAdapter,
)
from pydapter.migrations.exceptions import MigrationError


class TestBaseMigrationAdapter:
    """Test the BaseMigrationAdapter class."""

    def test_initialization(self):
        """Test initialization of the base adapter."""

        # Create a concrete subclass for testing
        class ConcreteMigrationAdapter(BaseMigrationAdapter):
            migration_key: ClassVar[str] = "test"

        # Initialize the adapter
        adapter = ConcreteMigrationAdapter(
            connection_string="postgresql://user:pass@localhost/db",
            models_module="test_module",
        )

        # Check initialization
        assert adapter.connection_string == "postgresql://user:pass@localhost/db"
        assert adapter.models_module == "test_module"
        assert adapter._initialized is False
        assert adapter._migrations_dir is None

    def test_ensure_directory(self, tmpdir):
        """Test the _ensure_directory method."""

        # Create a concrete subclass for testing
        class ConcreteMigrationAdapter(BaseMigrationAdapter):
            migration_key: ClassVar[str] = "test"

        # Initialize the adapter
        adapter = ConcreteMigrationAdapter(connection_string="test")

        # Create a test directory path
        test_dir = os.path.join(tmpdir, "migrations")

        # Ensure the directory exists
        adapter._ensure_directory(test_dir)

        # Check that the directory was created
        assert os.path.exists(test_dir)
        assert os.path.isdir(test_dir)

        # Calling again should not raise an error
        adapter._ensure_directory(test_dir)

    def test_check_initialized(self):
        """Test the _check_initialized method."""

        # Create a concrete subclass for testing
        class ConcreteMigrationAdapter(BaseMigrationAdapter):
            migration_key: ClassVar[str] = "test"

        # Initialize the adapter
        adapter = ConcreteMigrationAdapter(connection_string="test")

        # Check that an error is raised if not initialized
        with pytest.raises(MigrationError) as exc_info:
            adapter._check_initialized()

        assert "Migrations have not been initialized" in str(exc_info.value)

        # Set initialized to True
        adapter._initialized = True

        # Should not raise an error now
        adapter._check_initialized()


class TestSyncMigrationAdapter:
    """Test the SyncMigrationAdapter class."""

    def test_abstract_methods(self):
        """Test that abstract methods raise NotImplementedError."""

        # Create a concrete subclass for testing
        class ConcreteSyncAdapter(SyncMigrationAdapter):
            migration_key: ClassVar[str] = "test_sync"

        # Check that abstract methods raise NotImplementedError
        with pytest.raises(NotImplementedError):
            ConcreteSyncAdapter.init_migrations("test_dir")

        with pytest.raises(NotImplementedError):
            ConcreteSyncAdapter.create_migration("test migration")

        with pytest.raises(NotImplementedError):
            ConcreteSyncAdapter.upgrade()

        with pytest.raises(NotImplementedError):
            ConcreteSyncAdapter.downgrade("revision")

        with pytest.raises(NotImplementedError):
            ConcreteSyncAdapter.get_current_revision()

        with pytest.raises(NotImplementedError):
            ConcreteSyncAdapter.get_migration_history()


class TestAsyncMigrationAdapter:
    """Test the AsyncMigrationAdapter class."""

    @pytest.mark.asyncio
    async def test_abstract_methods(self):
        """Test that abstract methods raise NotImplementedError."""

        # Create a concrete subclass for testing
        class ConcreteAsyncAdapter(AsyncMigrationAdapter):
            migration_key: ClassVar[str] = "test_async"

        # Check that abstract methods raise NotImplementedError
        with pytest.raises(NotImplementedError):
            await ConcreteAsyncAdapter.init_migrations("test_dir")

        with pytest.raises(NotImplementedError):
            await ConcreteAsyncAdapter.create_migration("test migration")

        with pytest.raises(NotImplementedError):
            await ConcreteAsyncAdapter.upgrade()

        with pytest.raises(NotImplementedError):
            await ConcreteAsyncAdapter.downgrade("revision")

        with pytest.raises(NotImplementedError):
            await ConcreteAsyncAdapter.get_current_revision()

        with pytest.raises(NotImplementedError):
            await ConcreteAsyncAdapter.get_migration_history()


class TestImplementedSyncAdapter:
    """Test a fully implemented synchronous migration adapter."""

    def test_implemented_adapter(self):
        """Test a fully implemented adapter."""

        # Create a concrete implementation
        class ImplementedSyncAdapter(SyncMigrationAdapter):
            migration_key: ClassVar[str] = "implemented_sync"

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

        # Check that the adapter works
        assert ImplementedSyncAdapter.migration_key == "implemented_sync"
        assert ImplementedSyncAdapter.create_migration("test") == "revision123"
        assert ImplementedSyncAdapter.get_current_revision() == "revision123"
        assert len(ImplementedSyncAdapter.get_migration_history()) == 1


class TestImplementedAsyncAdapter:
    """Test a fully implemented asynchronous migration adapter."""

    @pytest.mark.asyncio
    async def test_implemented_adapter(self):
        """Test a fully implemented async adapter."""

        # Create a concrete implementation
        class ImplementedAsyncAdapter(AsyncMigrationAdapter):
            migration_key: ClassVar[str] = "implemented_async"

            @classmethod
            async def init_migrations(cls, directory: str, **kwargs) -> None:
                return None

            @classmethod
            async def create_migration(
                cls, message: str, autogenerate: bool = True, **kwargs
            ) -> str:
                return "revision123"

            @classmethod
            async def upgrade(cls, revision: str = "head", **kwargs) -> None:
                return None

            @classmethod
            async def downgrade(cls, revision: str, **kwargs) -> None:
                return None

            @classmethod
            async def get_current_revision(cls, **kwargs) -> Optional[str]:
                return "revision123"

            @classmethod
            async def get_migration_history(cls, **kwargs) -> list[dict[str, Any]]:
                return [{"revision": "revision123", "message": "test migration"}]

        # Check that the adapter works
        assert ImplementedAsyncAdapter.migration_key == "implemented_async"
        assert await ImplementedAsyncAdapter.create_migration("test") == "revision123"
        assert await ImplementedAsyncAdapter.get_current_revision() == "revision123"
        assert len(await ImplementedAsyncAdapter.get_migration_history()) == 1


class TestMigrationAdapterInstantiation:
    """Test instantiation of migration adapters."""

    def test_adapter_instantiation(self):
        """Test instantiation of migration adapters."""

        # Create a concrete implementation
        class TestAdapter(BaseMigrationAdapter):
            migration_key: ClassVar[str] = "test_adapter"

        # Test instantiation with required parameters
        adapter = TestAdapter(connection_string="sqlite:///test.db")
        assert adapter.connection_string == "sqlite:///test.db"
        assert adapter.models_module is None

        # Test instantiation with all parameters
        adapter = TestAdapter(
            connection_string="sqlite:///test.db",
            models_module="test_module",
        )
        assert adapter.connection_string == "sqlite:///test.db"
        assert adapter.models_module == "test_module"

        # Set migrations directory manually
        adapter._migrations_dir = "migrations"
        assert adapter._migrations_dir == "migrations"

    def test_adapter_initialization_with_directory(self, tmpdir):
        """Test initialization of migration adapters with directory."""

        # Create a concrete implementation that tracks initialization
        class TestAdapter(BaseMigrationAdapter):
            migration_key: ClassVar[str] = "test_adapter"
            initialized: ClassVar[bool] = False

            @classmethod
            def init_migrations(cls, directory: str, **kwargs) -> None:
                cls.initialized = True
                return None

            def initialize_migrations(self, directory: str, **kwargs) -> None:
                self.__class__.initialized = True
                self._initialized = True
                self._migrations_dir = directory
                return None

        # Create a test directory
        test_dir = os.path.join(tmpdir, "migrations")
        os.makedirs(test_dir, exist_ok=True)

        # Initialize the adapter
        adapter = TestAdapter(
            connection_string="sqlite:///test.db",
        )

        # Set migrations directory manually
        adapter._migrations_dir = test_dir

        # Check that the adapter is initialized
        assert adapter._migrations_dir == test_dir
        assert adapter._initialized is False  # Not initialized yet

        # Initialize the migrations
        adapter.initialize_migrations(test_dir)
        assert TestAdapter.initialized is True
        assert adapter._initialized is True
