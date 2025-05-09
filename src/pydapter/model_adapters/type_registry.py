"""
Type registry for mapping between Python and SQL types.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional, TypeVar

T = TypeVar("T")


class TypeRegistry:
    """Registry for type mappings between Python and SQL types."""

    _PY_TO_SQL: Dict[type, Callable[[], Any]] = {}
    _SQL_TO_PY: Dict[type, type] = {}
    _PY_TO_SQL_CONVERTERS: Dict[type, Callable[[Any], Any]] = {}
    _SQL_TO_PY_CONVERTERS: Dict[type, Callable[[Any], Any]] = {}

    @classmethod
    def register(
        cls,
        python_type: type,
        sql_type_factory: Callable[[], Any],
        python_to_sql: Optional[Callable[[Any], Any]] = None,
        sql_to_python: Optional[Callable[[Any], Any]] = None,
    ) -> None:
        """
        Register a type mapping between Python and SQL types.

        Args:
            python_type: The Python type to map from/to.
            sql_type_factory: A factory function that creates the corresponding SQL type.
            python_to_sql: Optional function to convert from Python to SQL value.
            sql_to_python: Optional function to convert from SQL to Python value.
        """
        cls._PY_TO_SQL[python_type] = sql_type_factory
        sql_type = sql_type_factory()
        cls._SQL_TO_PY[type(sql_type)] = python_type

        if python_to_sql:
            cls._PY_TO_SQL_CONVERTERS[python_type] = python_to_sql
        if sql_to_python:
            cls._SQL_TO_PY_CONVERTERS[type(sql_type)] = sql_to_python

    @classmethod
    def get_sql_type(cls, python_type: type) -> Optional[Callable[[], Any]]:
        """
        Get the SQL type factory for a Python type.

        Args:
            python_type: The Python type to get the SQL type for.

        Returns:
            A factory function that creates the corresponding SQL type, or None if not found.
        """
        if python_type in cls._PY_TO_SQL:
            return cls._PY_TO_SQL[python_type]

        # Try to find a compatible type
        for registered_type, sql_type in cls._PY_TO_SQL.items():
            try:
                if isinstance(python_type, type) and issubclass(
                    python_type, registered_type
                ):
                    return sql_type
            except TypeError:
                # Skip parameterized generics that can't be used with issubclass
                continue

        return None

    @classmethod
    def get_python_type(cls, sql_type: Any) -> Optional[type]:
        """
        Get the Python type for an SQL type.

        Args:
            sql_type: The SQL type to get the Python type for.

        Returns:
            The corresponding Python type, or None if not found.
        """
        sql_type_class = type(sql_type)
        if sql_type_class in cls._SQL_TO_PY:
            return cls._SQL_TO_PY[sql_type_class]

        # Try to find a compatible type
        for registered_type, py_type in cls._SQL_TO_PY.items():
            if isinstance(sql_type, registered_type):
                return py_type

        return None

    @classmethod
    def convert_to_sql(cls, value: Any, python_type: type) -> Any:
        """
        Convert a Python value to an SQL value.

        Args:
            value: The Python value to convert.
            python_type: The Python type of the value.

        Returns:
            The converted SQL value.
        """
        if value is None:
            return None

        converter = cls._PY_TO_SQL_CONVERTERS.get(python_type)
        if converter:
            return converter(value)

        # Try to find a compatible converter
        for registered_type, conv in cls._PY_TO_SQL_CONVERTERS.items():
            if isinstance(python_type, type) and issubclass(
                python_type, registered_type
            ):
                return conv(value)

        # No converter found, return as is
        return value

    @classmethod
    def convert_to_python(cls, value: Any, sql_type: Any) -> Any:
        """
        Convert an SQL value to a Python value.

        Args:
            value: The SQL value to convert.
            sql_type: The SQL type of the value.

        Returns:
            The converted Python value.
        """
        if value is None:
            return None

        sql_type_class = type(sql_type)
        converter = cls._SQL_TO_PY_CONVERTERS.get(sql_type_class)
        if converter:
            return converter(value)

        # Try to find a compatible converter
        for registered_type, conv in cls._SQL_TO_PY_CONVERTERS.items():
            if isinstance(sql_type, registered_type):
                return conv(value)

        # No converter found, return as is
        return value
