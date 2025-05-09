import pytest
from sqlalchemy import Boolean, Float, Integer, String

from pydapter.model_adapters.type_registry import TypeRegistry


def test_register_and_get_sql_type():
    """Test registering and retrieving SQL types."""
    # Clear existing registrations for this test
    original_py_to_sql = TypeRegistry._PY_TO_SQL.copy()
    original_sql_to_py = TypeRegistry._SQL_TO_PY.copy()

    try:
        TypeRegistry._PY_TO_SQL = {}
        TypeRegistry._SQL_TO_PY = {}

        # Register a type mapping
        TypeRegistry.register(
            python_type=int,
            sql_type_factory=lambda: Integer(),
        )

        # Get the SQL type
        sql_type_factory = TypeRegistry.get_sql_type(int)
        assert sql_type_factory is not None
        assert isinstance(sql_type_factory(), Integer)

        # Get the Python type
        py_type = TypeRegistry.get_python_type(Integer())
        assert py_type is int
    finally:
        # Restore original registrations
        TypeRegistry._PY_TO_SQL = original_py_to_sql
        TypeRegistry._SQL_TO_PY = original_sql_to_py


def test_register_with_converters():
    """Test registering type mappings with converters."""
    # Clear existing registrations for this test
    original_py_to_sql = TypeRegistry._PY_TO_SQL.copy()
    original_sql_to_py = TypeRegistry._SQL_TO_PY.copy()
    original_py_to_sql_converters = TypeRegistry._PY_TO_SQL_CONVERTERS.copy()
    original_sql_to_py_converters = TypeRegistry._SQL_TO_PY_CONVERTERS.copy()

    try:
        TypeRegistry._PY_TO_SQL = {}
        TypeRegistry._SQL_TO_PY = {}
        TypeRegistry._PY_TO_SQL_CONVERTERS = {}
        TypeRegistry._SQL_TO_PY_CONVERTERS = {}

        # Register a type mapping with converters
        TypeRegistry.register(
            python_type=bool,
            sql_type_factory=lambda: String(1),
            python_to_sql=lambda x: "Y" if x else "N",
            sql_to_python=lambda x: x == "Y",
        )

        # Convert Python to SQL
        sql_value = TypeRegistry.convert_to_sql(True, bool)
        assert sql_value == "Y"

        # Convert SQL to Python
        py_value = TypeRegistry.convert_to_python("Y", String(1))
        assert py_value is True
    finally:
        # Restore original registrations
        TypeRegistry._PY_TO_SQL = original_py_to_sql
        TypeRegistry._SQL_TO_PY = original_sql_to_py
        TypeRegistry._PY_TO_SQL_CONVERTERS = original_py_to_sql_converters
        TypeRegistry._SQL_TO_PY_CONVERTERS = original_sql_to_py_converters


def test_get_sql_type_inheritance():
    """Test getting SQL type for a subclass."""
    # Clear existing registrations for this test
    original_py_to_sql = TypeRegistry._PY_TO_SQL.copy()

    try:
        TypeRegistry._PY_TO_SQL = {}

        # Register a type mapping for a base class
        class Base:
            pass

        class Derived(Base):
            pass

        TypeRegistry.register(
            python_type=Base,
            sql_type_factory=lambda: String(),
        )

        # Get the SQL type for the derived class
        sql_type_factory = TypeRegistry.get_sql_type(Derived)
        assert sql_type_factory is not None
        assert isinstance(sql_type_factory(), String)
    finally:
        # Restore original registrations
        TypeRegistry._PY_TO_SQL = original_py_to_sql


def test_get_python_type_inheritance():
    """Test getting Python type for a subclass of SQL type."""
    # Clear existing registrations for this test
    original_sql_to_py = TypeRegistry._SQL_TO_PY.copy()

    try:
        TypeRegistry._SQL_TO_PY = {}

        # Create a custom SQL type
        class CustomInteger(Integer):
            pass

        # Register a type mapping
        TypeRegistry.register(
            python_type=int,
            sql_type_factory=lambda: Integer(),
        )

        # Get the Python type for the custom SQL type
        py_type = TypeRegistry.get_python_type(CustomInteger())
        assert py_type is int
    finally:
        # Restore original registrations
        TypeRegistry._SQL_TO_PY = original_sql_to_py
