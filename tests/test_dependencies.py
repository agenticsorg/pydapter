import importlib
from importlib.util import find_spec

import pytest
from pydapter.utils.dependencies import (
    check_dependency,
    check_migrations_dependencies,
    check_migrations_sql_dependencies,
)


def test_check_dependency_installed():
    """Test check_dependency with an installed package."""
    # This should not raise an exception
    check_dependency("importlib", "test")


def test_check_dependency_not_installed():
    """Test check_dependency with a non-existent package."""
    # This should raise an ImportError
    with pytest.raises(ImportError) as excinfo:
        check_dependency("non_existent_package_12345", "test")

    # Check that the error message contains the expected text
    assert (
        "The 'test' feature requires the 'non_existent_package_12345' package"
        in str(excinfo.value)
    )
    assert "pip install pydapter[test]" in str(excinfo.value)


def test_migrations_dependencies():
    """Test check_migrations_dependencies."""
    # This should not raise an exception as migrations core has no additional dependencies
    check_migrations_dependencies()


def test_migrations_sql_dependencies():
    """Test check_migrations_sql_dependencies."""
    # If sqlalchemy and alembic are installed, this should not raise an exception
    if find_spec("sqlalchemy") is not None and find_spec("alembic") is not None:
        check_migrations_sql_dependencies()
    else:
        # If either package is not installed, this should raise an ImportError
        with pytest.raises(ImportError):
            check_migrations_sql_dependencies()


def test_lazy_import_protocols():
    """Test lazy import of protocols."""
    # Try importing a protocol
    try:
        importlib.import_module("pydapter.protocols")
        # If we get here, the import succeeded
        assert True
    except ImportError:
        # If typing_extensions is not installed, this should fail
        assert find_spec("typing_extensions") is None


def test_lazy_import_migrations():
    """Test lazy import of migrations."""
    # Try importing a migration class
    try:
        importlib.import_module("pydapter.migrations")
        # If we get here, the import succeeded
        assert True
    except ImportError:
        # This should not fail as migrations core has no additional dependencies
        assert False, "Migration import failed unexpectedly"


def test_lazy_import_migrations_sql():
    """Test lazy import of SQL migrations."""
    # Try importing a SQL migration class
    try:
        importlib.import_module("pydapter.migrations.sql")
        # If we get here, the import succeeded
        assert True
    except ImportError:
        # If sqlalchemy or alembic is not installed, this should fail
        assert find_spec("sqlalchemy") is None or find_spec("alembic") is None
