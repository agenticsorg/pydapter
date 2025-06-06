"""
Tests for migration exceptions in pydapter.migrations.exceptions.
"""

import pytest
from pydapter.migrations.exceptions import (
    MigrationCreationError,
    MigrationDowngradeError,
    MigrationError,
    MigrationInitError,
    MigrationNotFoundError,
    MigrationUpgradeError,
)


class TestMigrationExceptions:
    """Test the migration exception classes."""

    def test_migration_error_base_class(self):
        """Test the base MigrationError class."""
        # Create a MigrationError
        error = MigrationError("Test error message")

        # Check that it's an Exception
        assert isinstance(error, Exception)

        # Check the error message
        assert str(error) == "Test error message"

    def test_migration_not_found_error(self):
        """Test the MigrationNotFoundError class."""
        # Create a MigrationNotFoundError
        error = MigrationNotFoundError("Migration not found", revision="rev123")

        # Check that it's a MigrationError
        assert isinstance(error, MigrationError)

        # Check the error attributes
        assert "Migration not found" in str(error)
        assert error.revision == "rev123"

    def test_migration_init_error(self):
        """Test the MigrationInitError class."""
        # Create a MigrationInitError
        error = MigrationInitError("Failed to initialize migrations")

        # Check that it's a MigrationError
        assert isinstance(error, MigrationError)

        # Check the error message
        assert "Failed to initialize migrations" in str(error)

    def test_migration_creation_error(self):
        """Test the MigrationCreationError class."""
        # Create a MigrationCreationError
        error = MigrationCreationError("Failed to create migration")

        # Check that it's a MigrationError
        assert isinstance(error, MigrationError)

        # Check the error message
        assert "Failed to create migration" in str(error)

    def test_migration_upgrade_error(self):
        """Test the MigrationUpgradeError class."""
        # Create a MigrationUpgradeError
        error = MigrationUpgradeError("Failed to upgrade")

        # Check that it's a MigrationError
        assert isinstance(error, MigrationError)

        # Check the error message
        assert "Failed to upgrade" in str(error)

    def test_migration_downgrade_error(self):
        """Test the MigrationDowngradeError class."""
        # Create a MigrationDowngradeError
        error = MigrationDowngradeError("Failed to downgrade")

        # Check that it's a MigrationError
        assert isinstance(error, MigrationError)

        # Check the error message
        assert "Failed to downgrade" in str(error)

    def test_migration_error_with_cause(self):
        """Test MigrationError with a cause."""
        # Create a MigrationError with an original error message
        error = MigrationError("Migration failed", original_error="Original error")

        # Check the error message
        assert "Migration failed" in str(error)
        assert "original_error='Original error'" in str(error)

    def test_migration_init_error_with_cause(self):
        """Test MigrationInitError with a cause."""
        # Create a MigrationInitError with an original error message
        error = MigrationInitError(
            "Failed to initialize migrations",
            directory="/tmp",
            original_error="Directory not found",
        )

        # Check the error message
        assert "Failed to initialize migrations" in str(error)
        assert error.directory == "/tmp"
        assert "original_error='Directory not found'" in str(error)

    def test_migration_error_inheritance(self):
        """Test the inheritance hierarchy of migration exceptions."""
        # Create instances of each exception type
        base_error = MigrationError("Base error")
        init_error = MigrationInitError("Init error")
        creation_error = MigrationCreationError("Creation error")
        upgrade_error = MigrationUpgradeError("Upgrade error")
        downgrade_error = MigrationDowngradeError("Downgrade error")
        not_found_error = MigrationNotFoundError("Not found error")

        # Check the inheritance hierarchy
        assert isinstance(base_error, Exception)
        assert isinstance(init_error, MigrationError)
        assert isinstance(creation_error, MigrationError)
        assert isinstance(upgrade_error, MigrationError)
        assert isinstance(downgrade_error, MigrationError)
        assert isinstance(not_found_error, MigrationError)

    def test_raising_migration_errors(self):
        """Test raising migration exceptions."""
        # Test raising MigrationError
        with pytest.raises(MigrationError) as exc_info:
            raise MigrationError("Test error")
        assert str(exc_info.value) == "Test error"

        # Test raising MigrationInitError
        with pytest.raises(MigrationInitError) as exc_info:
            raise MigrationInitError("Init error")
        assert "Init error" in str(exc_info.value)

        # Test raising MigrationCreationError
        with pytest.raises(MigrationCreationError) as exc_info:
            raise MigrationCreationError("Creation error")
        assert "Creation error" in str(exc_info.value)

    def test_catching_migration_errors(self):
        """Test catching migration exceptions."""
        # Test catching MigrationError
        try:
            raise MigrationError("Test error")
        except MigrationError as e:
            assert str(e) == "Test error"

        # Test catching MigrationInitError as MigrationError
        try:
            raise MigrationInitError("Init error")
        except MigrationError as e:
            assert "Init error" in str(e)

        # Test catching MigrationCreationError as MigrationError
        try:
            raise MigrationCreationError("Creation error")
        except MigrationError as e:
            assert "Creation error" in str(e)

    def test_migration_error_with_nested_cause(self):
        """Test MigrationError with a nested cause."""
        # Create a MigrationError with an intermediate error message
        error = MigrationError("Migration failed", original_error="Intermediate error")

        # Check the error message
        assert "Migration failed" in str(error)
        assert "original_error='Intermediate error'" in str(error)

    def test_custom_migration_error_subclass(self):
        """Test creating a custom MigrationError subclass."""

        # Define a custom MigrationError subclass
        class CustomMigrationError(MigrationError):
            """Custom migration error."""

            def __init__(self, message, custom_info=None, **context):
                super().__init__(message, **context)
                self.custom_info = custom_info

        # Create an instance of the custom error
        error = CustomMigrationError("Custom error", custom_info="Extra info")

        # Check that it's a MigrationError
        assert isinstance(error, MigrationError)

        # Check the error message
        assert "Custom error" in str(error)

        # Check the custom attribute
        assert error.custom_info == "Extra info"
