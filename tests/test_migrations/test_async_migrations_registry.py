"""
Tests for async migration registry in pydapter.migrations.registry.
"""

from typing import Any, ClassVar, Optional
from unittest.mock import AsyncMock, patch

import pytest
from pydapter.exceptions import AdapterNotFoundError, ConfigurationError
from pydapter.migrations.exceptions import (
    MigrationCreationError,
    MigrationDowngradeError,
    MigrationError,
    MigrationInitError,
    MigrationUpgradeError,
)
from pydapter.migrations.registry import AsyncMigrationRegistry


class TestAsyncMigrationRegistry:
    """Test the AsyncMigrationRegistry class."""

    def test_initialization(self):
        """Test initialization of the registry."""
        registry = AsyncMigrationRegistry()
        assert registry._reg == {}

    def test_registration(self):
        """Test registration of async migration adapters."""
        registry = AsyncMigrationRegistry()

        # Create a test adapter
        class TestAsyncAdapter:
            migration_key: ClassVar[str] = "test_async"

            @classmethod
            async def init_migrations(cls, directory: str, **kwargs) -> None:
                return None

            @classmethod
            async def create_migration(
                cls, message: str, autogenerate: bool = True, **kwargs
            ) -> str:
                return "async_revision123"

            @classmethod
            async def upgrade(cls, revision: str = "head", **kwargs) -> None:
                return None

            @classmethod
            async def downgrade(cls, revision: str, **kwargs) -> None:
                return None

            @classmethod
            async def get_current_revision(cls, **kwargs) -> Optional[str]:
                return "async_revision123"

            @classmethod
            async def get_migration_history(cls, **kwargs) -> list[dict[str, Any]]:
                return [
                    {"revision": "async_revision123", "message": "test async migration"}
                ]

        # Register the adapter
        registry.register(TestAsyncAdapter)

        # Check that the adapter is registered
        assert registry.get("test_async") == TestAsyncAdapter

    def test_registration_with_duplicate_key(self):
        """Test registration with a duplicate key."""
        registry = AsyncMigrationRegistry()

        # Create two test adapters with the same key
        class TestAsyncAdapter1:
            migration_key: ClassVar[str] = "test_async"

            @classmethod
            async def init_migrations(cls, directory: str, **kwargs) -> None:
                return None

            @classmethod
            async def create_migration(
                cls, message: str, autogenerate: bool = True, **kwargs
            ) -> str:
                return "async_revision123"

            @classmethod
            async def upgrade(cls, revision: str = "head", **kwargs) -> None:
                return None

            @classmethod
            async def downgrade(cls, revision: str, **kwargs) -> None:
                return None

            @classmethod
            async def get_current_revision(cls, **kwargs) -> Optional[str]:
                return "async_revision123"

            @classmethod
            async def get_migration_history(cls, **kwargs) -> list[dict[str, Any]]:
                return [
                    {"revision": "async_revision123", "message": "test async migration"}
                ]

        class TestAsyncAdapter2:
            migration_key: ClassVar[str] = "test_async"

            @classmethod
            async def init_migrations(cls, directory: str, **kwargs) -> None:
                return None

            @classmethod
            async def create_migration(
                cls, message: str, autogenerate: bool = True, **kwargs
            ) -> str:
                return "async_revision456"

            @classmethod
            async def upgrade(cls, revision: str = "head", **kwargs) -> None:
                return None

            @classmethod
            async def downgrade(cls, revision: str, **kwargs) -> None:
                return None

            @classmethod
            async def get_current_revision(cls, **kwargs) -> Optional[str]:
                return "async_revision456"

            @classmethod
            async def get_migration_history(cls, **kwargs) -> list[dict[str, Any]]:
                return [
                    {"revision": "async_revision456", "message": "test async migration"}
                ]

        # Register the first adapter
        registry.register(TestAsyncAdapter1)

        # Register the second adapter (should overwrite the first)
        registry.register(TestAsyncAdapter2)

        # Check that the second adapter is registered
        adapter = registry.get("test_async")
        assert adapter == TestAsyncAdapter2

    def test_get_nonexistent_adapter(self):
        """Test getting a nonexistent adapter."""
        registry = AsyncMigrationRegistry()

        # Try to get a nonexistent adapter
        with pytest.raises(AdapterNotFoundError) as exc_info:
            registry.get("nonexistent_async")

        assert "No async migration adapter registered for 'nonexistent_async'" in str(
            exc_info.value
        )

    def test_registration_with_invalid_adapter(self):
        """Test registration with an invalid adapter."""
        registry = AsyncMigrationRegistry()

        # Create an invalid adapter (missing migration_key)
        class InvalidAsyncAdapter:
            # Missing migration_key

            @classmethod
            async def init_migrations(cls, directory: str, **kwargs) -> None:
                return None

            @classmethod
            async def create_migration(
                cls, message: str, autogenerate: bool = True, **kwargs
            ) -> str:
                return "async_revision123"

            @classmethod
            async def upgrade(cls, revision: str = "head", **kwargs) -> None:
                return None

            @classmethod
            async def downgrade(cls, revision: str, **kwargs) -> None:
                return None

            @classmethod
            async def get_current_revision(cls, **kwargs) -> Optional[str]:
                return "async_revision123"

            @classmethod
            async def get_migration_history(cls, **kwargs) -> list[dict[str, Any]]:
                return [
                    {"revision": "async_revision123", "message": "test async migration"}
                ]

        # Try to register the invalid adapter
        with pytest.raises(ConfigurationError) as exc_info:
            registry.register(InvalidAsyncAdapter)

        assert "Async migration adapter must define 'migration_key'" in str(
            exc_info.value
        )


@pytest.fixture
def mock_async_adapter():
    """Create a mock async adapter for testing."""

    class MockAsyncAdapter:
        migration_key: ClassVar[str] = "mock_async"

        @classmethod
        async def init_migrations(cls, directory: str, **kwargs) -> None:
            return None

        @classmethod
        async def create_migration(
            cls, message: str, autogenerate: bool = True, **kwargs
        ) -> str:
            return "mock_async_revision"

        @classmethod
        async def upgrade(cls, revision: str = "head", **kwargs) -> None:
            return None

        @classmethod
        async def downgrade(cls, revision: str, **kwargs) -> None:
            return None

        @classmethod
        async def get_current_revision(cls, **kwargs) -> Optional[str]:
            return "mock_async_revision"

        @classmethod
        async def get_migration_history(cls, **kwargs) -> list[dict[str, Any]]:
            return [
                {"revision": "mock_async_revision", "message": "mock async migration"}
            ]

    return MockAsyncAdapter


@pytest.fixture
def populated_async_registry(mock_async_adapter):
    """Create an async migration registry with mock adapters."""
    registry = AsyncMigrationRegistry()
    registry.register(mock_async_adapter)
    return registry


@pytest.mark.asyncio
async def test_async_init_migrations(populated_async_registry):
    """Test the init_migrations convenience method."""
    with patch.object(
        populated_async_registry.get("mock_async"), "init_migrations"
    ) as mock_init:
        # Configure the mock to return a coroutine
        mock_init.return_value = AsyncMock()

        # Call the method
        await populated_async_registry.init_migrations(
            "mock_async", "./async_migrations"
        )

        # Verify the mock was called with the correct arguments
        mock_init.assert_called_once_with("./async_migrations")


@pytest.mark.asyncio
async def test_async_create_migration(populated_async_registry):
    """Test the create_migration convenience method."""
    with patch.object(
        populated_async_registry.get("mock_async"), "create_migration"
    ) as mock_create:
        # Configure the mock to return a coroutine that resolves to the value
        mock_create.return_value = "new_async_revision"

        # Call the method
        result = await populated_async_registry.create_migration(
            "mock_async", "Test async migration", autogenerate=True
        )

        # Verify the result and that the mock was called with the correct arguments
        assert result == "new_async_revision"
        mock_create.assert_called_once_with("Test async migration", True)


@pytest.mark.asyncio
async def test_async_upgrade(populated_async_registry):
    """Test the upgrade convenience method."""
    with patch.object(
        populated_async_registry.get("mock_async"), "upgrade"
    ) as mock_upgrade:
        # Configure the mock to return a coroutine
        mock_upgrade.return_value = AsyncMock()

        # Call the method
        await populated_async_registry.upgrade("mock_async", "target_revision")

        # Verify the mock was called with the correct arguments
        mock_upgrade.assert_called_once_with("target_revision")


@pytest.mark.asyncio
async def test_async_downgrade(populated_async_registry):
    """Test the downgrade convenience method."""
    with patch.object(
        populated_async_registry.get("mock_async"), "downgrade"
    ) as mock_downgrade:
        # Configure the mock to return a coroutine
        mock_downgrade.return_value = AsyncMock()

        # Call the method
        await populated_async_registry.downgrade("mock_async", "target_revision")

        # Verify the mock was called with the correct arguments
        mock_downgrade.assert_called_once_with("target_revision")


@pytest.mark.asyncio
async def test_async_get_current_revision(populated_async_registry):
    """Test the get_current_revision convenience method."""
    with patch.object(
        populated_async_registry.get("mock_async"), "get_current_revision"
    ) as mock_get:
        # Configure the mock to return a coroutine that resolves to the value
        mock_get.return_value = "current_async_revision"

        # Call the method
        result = await populated_async_registry.get_current_revision("mock_async")

        # Verify the result and that the mock was called
        assert result == "current_async_revision"
        mock_get.assert_called_once()


@pytest.mark.asyncio
async def test_async_get_migration_history(populated_async_registry):
    """Test the get_migration_history convenience method."""
    with patch.object(
        populated_async_registry.get("mock_async"), "get_migration_history"
    ) as mock_get:
        # Configure the mock to return a coroutine that resolves to the value
        history = [{"revision": "async_rev1", "message": "First async migration"}]
        mock_get.return_value = history

        # Call the method
        result = await populated_async_registry.get_migration_history("mock_async")

        # Verify the result and that the mock was called
        assert result == history
        mock_get.assert_called_once()


@pytest.fixture
def error_raising_async_adapter():
    """Create a mock async adapter that raises exceptions."""

    class ErrorRaisingAsyncAdapter:
        migration_key: ClassVar[str] = "error_async"

        @classmethod
        async def init_migrations(cls, directory: str, **kwargs) -> None:
            raise RuntimeError("Async init error")

        @classmethod
        async def create_migration(
            cls, message: str, autogenerate: bool = True, **kwargs
        ) -> str:
            raise RuntimeError("Async creation error")

        @classmethod
        async def upgrade(cls, revision: str = "head", **kwargs) -> None:
            raise RuntimeError("Async upgrade error")

        @classmethod
        async def downgrade(cls, revision: str, **kwargs) -> None:
            raise RuntimeError("Async downgrade error")

        @classmethod
        async def get_current_revision(cls, **kwargs) -> Optional[str]:
            raise RuntimeError("Async revision error")

        @classmethod
        async def get_migration_history(cls, **kwargs) -> list[dict[str, Any]]:
            raise RuntimeError("Async history error")

    return ErrorRaisingAsyncAdapter


@pytest.fixture
def error_async_registry(error_raising_async_adapter):
    """Create an async migration registry with error-raising adapters."""
    registry = AsyncMigrationRegistry()
    registry.register(error_raising_async_adapter)
    return registry


@pytest.mark.asyncio
async def test_async_init_migrations_error(error_async_registry):
    """Test error handling in init_migrations convenience method."""
    with pytest.raises(MigrationInitError) as exc_info:
        await error_async_registry.init_migrations("error_async", "./async_migrations")

    assert "Failed to initialize async migrations for 'error_async'" in str(
        exc_info.value
    )
    assert exc_info.value.adapter == "error_async"
    assert exc_info.value.directory == "./async_migrations"
    assert "Async init error" in str(exc_info.value.original_error)


@pytest.mark.asyncio
async def test_async_create_migration_error(error_async_registry):
    """Test error handling in create_migration convenience method."""
    with pytest.raises(MigrationCreationError) as exc_info:
        await error_async_registry.create_migration(
            "error_async", "Test error migration", autogenerate=True
        )

    assert "Failed to create async migration for 'error_async'" in str(exc_info.value)
    assert exc_info.value.adapter == "error_async"
    assert exc_info.value.message_text == "Test error migration"
    assert exc_info.value.autogenerate is True
    assert "Async creation error" in str(exc_info.value.original_error)


@pytest.mark.asyncio
async def test_async_upgrade_error(error_async_registry):
    """Test error handling in upgrade convenience method."""
    with pytest.raises(MigrationUpgradeError) as exc_info:
        await error_async_registry.upgrade("error_async", "target_revision")

    assert "Failed to upgrade async migrations for 'error_async'" in str(exc_info.value)
    assert exc_info.value.adapter == "error_async"
    assert exc_info.value.revision == "target_revision"
    assert "Async upgrade error" in str(exc_info.value.original_error)


@pytest.mark.asyncio
async def test_async_downgrade_error(error_async_registry):
    """Test error handling in downgrade convenience method."""
    with pytest.raises(MigrationDowngradeError) as exc_info:
        await error_async_registry.downgrade("error_async", "target_revision")

    assert "Failed to downgrade async migrations for 'error_async'" in str(
        exc_info.value
    )
    assert exc_info.value.adapter == "error_async"
    assert exc_info.value.revision == "target_revision"
    assert "Async downgrade error" in str(exc_info.value.original_error)


@pytest.mark.asyncio
async def test_async_get_current_revision_error(error_async_registry):
    """Test error handling in get_current_revision convenience method."""
    with pytest.raises(MigrationError) as exc_info:
        await error_async_registry.get_current_revision("error_async")

    assert "Failed to get current async revision for 'error_async'" in str(
        exc_info.value
    )
    assert exc_info.value.adapter == "error_async"
    assert "Async revision error" in str(exc_info.value.original_error)


@pytest.mark.asyncio
async def test_async_get_migration_history_error(error_async_registry):
    """Test error handling in get_migration_history convenience method."""
    with pytest.raises(MigrationError) as exc_info:
        await error_async_registry.get_migration_history("error_async")

    assert "Failed to get async migration history for 'error_async'" in str(
        exc_info.value
    )
    assert exc_info.value.adapter == "error_async"
    assert "Async history error" in str(exc_info.value.original_error)
