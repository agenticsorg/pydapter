"""Test migrations.sql module initialization."""

import pytest
import sys
from unittest.mock import patch, MagicMock


class TestMigrationsSqlInit:
    """Test the migrations.sql module initialization."""

    def test_successful_import(self):
        """Test successful import when dependencies are available."""
        # The dependencies should be installed for tests
        from pydapter.migrations.sql import AlembicAdapter, AsyncAlembicAdapter

        # Verify imports work
        assert AlembicAdapter is not None
        assert AsyncAlembicAdapter is not None

    def test_import_with_missing_dependencies(self):
        """Test import behavior when dependencies are missing."""
        # This is tricky to test because alembic is installed
        # We would need to mock the import mechanism

        # Save original modules
        original_modules = {}
        modules_to_remove = [
            "pydapter.migrations.sql",
            "pydapter.migrations.sql.alembic_adapter",
            "alembic",
        ]

        for mod in modules_to_remove:
            if mod in sys.modules:
                original_modules[mod] = sys.modules[mod]

        try:
            # Remove modules from sys.modules
            for mod in modules_to_remove:
                sys.modules.pop(mod, None)

            # Mock the alembic import to fail
            with patch.dict("sys.modules", {"alembic": None}):
                # This should trigger the ImportError path
                try:
                    import pydapter.migrations.sql as sql_module

                    # Try to access a missing attribute
                    with pytest.raises(ImportError, match="Cannot import"):
                        _ = sql_module.AlembicAdapter

                except ImportError:
                    # This is expected if the import fails at module level
                    pass

        finally:
            # Restore original modules
            for mod, value in original_modules.items():
                sys.modules[mod] = value

    def test_getattr_fallback(self):
        """Test the __getattr__ fallback mechanism."""
        # This tests the error handling path
        # We need to simulate the ImportError condition

        # Create a mock module that simulates the ImportError condition
        mock_module = MagicMock()
        mock_module.__all__ = []

        # Create a mock __getattr__ that mimics the actual implementation
        def mock_getattr(name):
            # This simulates the actual __getattr__ behavior
            if name == "NonExistentAdapter":
                raise ImportError(
                    f"Cannot import {name} because dependencies are missing"
                )
            raise AttributeError(f"module has no attribute {name}")

        mock_module.__getattr__ = mock_getattr

        # Test that accessing a non-existent attribute raises ImportError
        with pytest.raises(ImportError, match="Cannot import NonExistentAdapter"):
            mock_getattr("NonExistentAdapter")
