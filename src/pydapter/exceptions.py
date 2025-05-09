"""
pydapter.exceptions - Custom exception hierarchy for pydapter.
"""

from typing import Any, Optional

PYDAPTER_PYTHON_ERRORS = (KeyError, ImportError, AttributeError, ValueError)


class AdapterError(Exception):
    """Base exception for all pydapter errors."""

    def __init__(self, message: str, **context: Any):
        super().__init__(message)
        self.message = message
        self.context = context

    def __str__(self) -> str:
        context_str = ", ".join(f"{k}={v!r}" for k, v in self.context.items())
        if context_str:
            return f"{self.message} ({context_str})"
        return self.message


class ValidationError(AdapterError):
    """Exception raised when data validation fails."""

    def __init__(self, message: str, data: Optional[Any] = None, **context: Any):
        super().__init__(message, **context)
        self.data = data


class TypeConversionError(ValidationError):
    """Exception raised when type conversion fails."""

    def __init__(
        self,
        message: str,
        source_type: Optional[type] = None,
        target_type: Optional[type] = None,
        field_name: Optional[str] = None,
        model_name: Optional[str] = None,
        **context: Any,
    ):
        super().__init__(message, **context)
        self.source_type = source_type
        self.target_type = target_type
        self.field_name = field_name
        self.model_name = model_name


class ParseError(AdapterError):
    """Exception raised when data parsing fails."""

    def __init__(self, message: str, source: Optional[str] = None, **context: Any):
        super().__init__(message, **context)
        self.source = source


class ConnectionError(AdapterError):
    """Exception raised when a connection to a data source fails."""

    def __init__(
        self,
        message: str,
        adapter: Optional[str] = None,
        url: Optional[str] = None,
        **context: Any,
    ):
        super().__init__(message, **context)
        self.adapter = adapter
        self.url = url


class QueryError(AdapterError):
    """Exception raised when a query to a data source fails."""

    def __init__(
        self,
        message: str,
        query: Optional[Any] = None,
        adapter: Optional[str] = None,
        **context: Any,
    ):
        super().__init__(message, **context)
        self.query = query
        self.adapter = adapter


class ResourceError(AdapterError):
    """Exception raised when a resource (file, database, etc.) cannot be accessed."""

    def __init__(self, message: str, resource: Optional[str] = None, **context: Any):
        super().__init__(message, **context)
        self.resource = resource


class ConfigurationError(AdapterError):
    """Exception raised when adapter configuration is invalid."""

    def __init__(
        self, message: str, config: Optional[dict[str, Any]] = None, **context: Any
    ):
        super().__init__(message, **context)
        self.config = config


class AdapterNotFoundError(AdapterError):
    """Exception raised when an adapter is not found."""

    def __init__(self, message: str, obj_key: Optional[str] = None, **context: Any):
        super().__init__(message, **context)
        self.obj_key = obj_key
