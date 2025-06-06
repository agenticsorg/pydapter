"""
Tests for error handling in migration registry in pydapter.migrations.registry.
"""

from typing import Any, ClassVar, Optional
from unittest.mock import patch

import pytest
from pydapter.migrations.exceptions import (
    MigrationCreationError,
    MigrationDowngradeError,
    MigrationError,
    MigrationInitError,
    MigrationUpgradeError,
)
from pydapter.migrations.registry import MigrationRegistry


@pytest.fixture
def mock_adapter():
    """Create a mock adapter for testing."""

    class MockAdapter:
        migration_key: ClassVar[str] = "mock"

        @classmethod
        def init_migrations(cls, directory: str, **kwargs) -> None:
            return None

        @classmethod
        def create_migration(
            cls, message: str, autogenerate: bool = True, **kwargs
        ) -> str:
            return "mock_revision"

        @classmethod
        def upgrade(cls, revision: str = "head", **kwargs) -> None:
            return None

        @classmethod
        def downgrade(cls, revision: str, **kwargs) -> None:
            return None

        @classmethod
        def get_current_revision(cls, **kwargs) -> Optional[str]:
            return "mock_revision"

        @classmethod
        def get_migration_history(cls, **kwargs) -> list[dict[str, Any]]:
            return [{"revision": "mock_revision", "message": "mock migration"}]

    return MockAdapter


@pytest.fixture
def populated_registry(mock_adapter):
    """Create a migration registry with mock adapters."""
    registry = MigrationRegistry()
    registry.register(mock_adapter)
    return registry


def test_init_migrations(populated_registry):
    """Test the init_migrations convenience method."""
    with patch.object(populated_registry.get("mock"), "init_migrations") as mock_init:
        # Call the method
        populated_registry.init_migrations("mock", "./migrations")

        # Verify the mock was called with the correct arguments
        mock_init.assert_called_once_with("./migrations")


def test_create_migration(populated_registry):
    """Test the create_migration convenience method."""
    with patch.object(
        populated_registry.get("mock"), "create_migration"
    ) as mock_create:
        # Configure the mock to return a specific value
        mock_create.return_value = "new_revision"

        # Call the method
        result = populated_registry.create_migration(
            "mock", "Test migration", autogenerate=True
        )

        # Verify the result and that the mock was called with the correct arguments
        assert result == "new_revision"
        mock_create.assert_called_once_with("Test migration", True)


def test_upgrade(populated_registry):
    """Test the upgrade convenience method."""
    with patch.object(populated_registry.get("mock"), "upgrade") as mock_upgrade:
        # Call the method
        populated_registry.upgrade("mock", "target_revision")

        # Verify the mock was called with the correct arguments
        mock_upgrade.assert_called_once_with("target_revision")


def test_downgrade(populated_registry):
    """Test the downgrade convenience method."""
    with patch.object(populated_registry.get("mock"), "downgrade") as mock_downgrade:
        # Call the method
        populated_registry.downgrade("mock", "target_revision")

        # Verify the mock was called with the correct arguments
        mock_downgrade.assert_called_once_with("target_revision")


def test_get_current_revision(populated_registry):
    """Test the get_current_revision convenience method."""
    with patch.object(
        populated_registry.get("mock"), "get_current_revision"
    ) as mock_get:
        # Configure the mock to return a specific value
        mock_get.return_value = "current_revision"

        # Call the method
        result = populated_registry.get_current_revision("mock")

        # Verify the result and that the mock was called
        assert result == "current_revision"
        mock_get.assert_called_once()


def test_get_migration_history(populated_registry):
    """Test the get_migration_history convenience method."""
    with patch.object(
        populated_registry.get("mock"), "get_migration_history"
    ) as mock_get:
        # Configure the mock to return a specific value
        history = [{"revision": "rev1", "message": "First migration"}]
        mock_get.return_value = history

        # Call the method
        result = populated_registry.get_migration_history("mock")

        # Verify the result and that the mock was called
        assert result == history
        mock_get.assert_called_once()


@pytest.fixture
def error_raising_adapter():
    """Create a mock adapter that raises exceptions."""

    class ErrorRaisingAdapter:
        migration_key: ClassVar[str] = "error"

        @classmethod
        def init_migrations(cls, directory: str, **kwargs) -> None:
            raise RuntimeError("Init error")

        @classmethod
        def create_migration(
            cls, message: str, autogenerate: bool = True, **kwargs
        ) -> str:
            raise RuntimeError("Creation error")

        @classmethod
        def upgrade(cls, revision: str = "head", **kwargs) -> None:
            raise RuntimeError("Upgrade error")

        @classmethod
        def downgrade(cls, revision: str, **kwargs) -> None:
            raise RuntimeError("Downgrade error")

        @classmethod
        def get_current_revision(cls, **kwargs) -> Optional[str]:
            raise RuntimeError("Revision error")

        @classmethod
        def get_migration_history(cls, **kwargs) -> list[dict[str, Any]]:
            raise RuntimeError("History error")

    return ErrorRaisingAdapter


@pytest.fixture
def error_registry(error_raising_adapter):
    """Create a migration registry with error-raising adapters."""
    registry = MigrationRegistry()
    registry.register(error_raising_adapter)
    return registry


def test_init_migrations_error(error_registry):
    """Test error handling in init_migrations convenience method."""
    with pytest.raises(MigrationInitError) as exc_info:
        error_registry.init_migrations("error", "./migrations")

    assert "Failed to initialize migrations for 'error'" in str(exc_info.value)
    assert exc_info.value.adapter == "error"
    assert exc_info.value.directory == "./migrations"
    assert "Init error" in str(exc_info.value.original_error)


def test_create_migration_error(error_registry):
    """Test error handling in create_migration convenience method."""
    with pytest.raises(MigrationCreationError) as exc_info:
        error_registry.create_migration(
            "error", "Test error migration", autogenerate=True
        )

    assert "Failed to create migration for 'error'" in str(exc_info.value)
    assert exc_info.value.adapter == "error"
    assert exc_info.value.message_text == "Test error migration"
    assert exc_info.value.autogenerate is True
    assert "Creation error" in str(exc_info.value.original_error)


def test_upgrade_error(error_registry):
    """Test error handling in upgrade convenience method."""
    with pytest.raises(MigrationUpgradeError) as exc_info:
        error_registry.upgrade("error", "target_revision")

    assert "Failed to upgrade migrations for 'error'" in str(exc_info.value)
    assert exc_info.value.adapter == "error"
    assert exc_info.value.revision == "target_revision"
    assert "Upgrade error" in str(exc_info.value.original_error)


def test_downgrade_error(error_registry):
    """Test error handling in downgrade convenience method."""
    with pytest.raises(MigrationDowngradeError) as exc_info:
        error_registry.downgrade("error", "target_revision")

    assert "Failed to downgrade migrations for 'error'" in str(exc_info.value)
    assert exc_info.value.adapter == "error"
    assert exc_info.value.revision == "target_revision"
    assert "Downgrade error" in str(exc_info.value.original_error)


def test_get_current_revision_error(error_registry):
    """Test error handling in get_current_revision convenience method."""
    with pytest.raises(MigrationError) as exc_info:
        error_registry.get_current_revision("error")

    assert "Failed to get current revision for 'error'" in str(exc_info.value)
    assert exc_info.value.adapter == "error"
    assert "Revision error" in str(exc_info.value.original_error)


def test_get_migration_history_error(error_registry):
    """Test error handling in get_migration_history convenience method."""
    with pytest.raises(MigrationError) as exc_info:
        error_registry.get_migration_history("error")

    assert "Failed to get migration history for 'error'" in str(exc_info.value)
    assert exc_info.value.adapter == "error"
    assert "History error" in str(exc_info.value.original_error)


@pytest.fixture
def migration_error_adapter():
    """Create a mock adapter that raises MigrationError exceptions."""

    class MigrationErrorAdapter:
        migration_key: ClassVar[str] = "migration_error"

        @classmethod
        def init_migrations(cls, directory: str, **kwargs) -> None:
            raise MigrationInitError(
                "Direct init error", directory=directory, adapter="migration_error"
            )

        @classmethod
        def create_migration(
            cls, message: str, autogenerate: bool = True, **kwargs
        ) -> str:
            raise MigrationCreationError(
                "Direct creation error",
                message_text=message,
                autogenerate=autogenerate,
                adapter="migration_error",
            )

        @classmethod
        def upgrade(cls, revision: str = "head", **kwargs) -> None:
            raise MigrationUpgradeError(
                "Direct upgrade error", revision=revision, adapter="migration_error"
            )

        @classmethod
        def downgrade(cls, revision: str, **kwargs) -> None:
            raise MigrationDowngradeError(
                "Direct downgrade error", revision=revision, adapter="migration_error"
            )

        @classmethod
        def get_current_revision(cls, **kwargs) -> Optional[str]:
            raise MigrationError("Direct revision error", adapter="migration_error")

        @classmethod
        def get_migration_history(cls, **kwargs) -> list[dict[str, Any]]:
            raise MigrationError("Direct history error", adapter="migration_error")

    return MigrationErrorAdapter


@pytest.fixture
def migration_error_registry(migration_error_adapter):
    """Create a migration registry with MigrationError-raising adapters."""
    registry = MigrationRegistry()
    registry.register(migration_error_adapter)
    return registry


def test_init_migrations_migration_error(migration_error_registry):
    """Test handling of MigrationError in init_migrations convenience method."""
    with pytest.raises(MigrationInitError) as exc_info:
        migration_error_registry.init_migrations("migration_error", "./migrations")

    assert "Direct init error" in str(exc_info.value)
    assert exc_info.value.adapter == "migration_error"
    assert exc_info.value.directory == "./migrations"


def test_create_migration_migration_error(migration_error_registry):
    """Test handling of MigrationError in create_migration convenience method."""
    with pytest.raises(MigrationCreationError) as exc_info:
        migration_error_registry.create_migration(
            "migration_error", "Test migration error", autogenerate=True
        )

    assert "Direct creation error" in str(exc_info.value)
    assert exc_info.value.adapter == "migration_error"
    assert exc_info.value.message_text == "Test migration error"
    assert exc_info.value.autogenerate is True


def test_upgrade_migration_error(migration_error_registry):
    """Test handling of MigrationError in upgrade convenience method."""
    with pytest.raises(MigrationUpgradeError) as exc_info:
        migration_error_registry.upgrade("migration_error", "target_revision")

    assert "Direct upgrade error" in str(exc_info.value)
    assert exc_info.value.adapter == "migration_error"
    assert exc_info.value.revision == "target_revision"


def test_downgrade_migration_error(migration_error_registry):
    """Test handling of MigrationError in downgrade convenience method."""
    with pytest.raises(MigrationDowngradeError) as exc_info:
        migration_error_registry.downgrade("migration_error", "target_revision")

    assert "Direct downgrade error" in str(exc_info.value)
    assert exc_info.value.adapter == "migration_error"
    assert exc_info.value.revision == "target_revision"


def test_get_current_revision_migration_error(migration_error_registry):
    """Test handling of MigrationError in get_current_revision convenience method."""
    with pytest.raises(MigrationError) as exc_info:
        migration_error_registry.get_current_revision("migration_error")

    assert "Direct revision error" in str(exc_info.value)
    assert exc_info.value.adapter == "migration_error"


def test_get_migration_history_migration_error(migration_error_registry):
    """Test handling of MigrationError in get_migration_history convenience method."""
    with pytest.raises(MigrationError) as exc_info:
        migration_error_registry.get_migration_history("migration_error")

    assert "Direct history error" in str(exc_info.value)
    assert exc_info.value.adapter == "migration_error"
