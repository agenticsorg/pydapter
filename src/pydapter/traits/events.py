"""
Event trait and utilities.

This module provides the Event class and related functionality,
migrated from the protocols system to the traits system.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import datetime, timezone
from functools import wraps
from typing import Any

from pydantic import BaseModel, JsonValue

from pydapter.fields import (
    DATETIME,
    EMBEDDING,
    EXECUTION,
    ID_FROZEN,
    PARAMS,
    create_model,
)
from pydapter.fields.template import FieldTemplate

# Base event fields using the new field system
BASE_EVENT_FIELDS = {
    "id": ID_FROZEN,
    "created_at": DATETIME,
    "updated_at": DATETIME,
    "embedding": EMBEDDING,
    "execution": EXECUTION,
    "request": PARAMS,
    "content": FieldTemplate(
        base_type=JsonValue,
        description="Content of the event",
        nullable=True,
        default=None,
    ),
    "event_type": FieldTemplate(
        base_type=str,
        description="Type of the event",
        nullable=True,
        default=None,
        validator=lambda x: x or "Event",
    ),
    "sha256": FieldTemplate(
        base_type=str,
        description="SHA256 hash of the event content",
        nullable=True,
        default=None,
    ),
}


# Create base Event model
Event = create_model(
    "Event",
    fields=BASE_EVENT_FIELDS,
)


def as_event(
    func: Callable[..., Any] | None = None,
    *,
    event_type: str | None = None,
    capture_result: bool = True,
    capture_args: bool = True,
) -> Callable[..., Any]:
    """
    Decorator to convert function calls into Event objects.

    This decorator wraps functions to automatically create Event objects
    that capture function calls, arguments, and results.

    Args:
        func: The function to decorate
        event_type: Type of event to create (defaults to function name)
        capture_result: Whether to capture the function result
        capture_args: Whether to capture function arguments

    Returns:
        Decorated function that creates Event objects

    Example:
        >>> @as_event(event_type="calculation")
        ... def add(a: int, b: int) -> int:
        ...     return a + b
        ...
        >>> result = add(2, 3)  # Creates an Event object
        >>> result
        5
    """

    def decorator(f: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(f)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Create event data
            event_data = {
                "event_type": event_type or f.__name__,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }

            if capture_args:
                event_data["request"] = {
                    "args": list(args),  # Convert to list for JSON serialization
                    "kwargs": kwargs,
                }

            # Execute function
            try:
                result = f(*args, **kwargs)

                if capture_result:
                    # Handle different result types
                    if isinstance(result, BaseModel):
                        event_data["content"] = result.model_dump()
                    elif hasattr(result, "__dict__"):
                        event_data["content"] = vars(result)
                    else:
                        event_data["content"] = result

                # Create event
                event = Event(**event_data)

                # Store event on result if possible
                if hasattr(result, "__dict__") and not isinstance(
                    result, (str, int, float, bool, list, dict)
                ):
                    try:
                        result.__event__ = event
                    except (AttributeError, TypeError):
                        pass  # Some objects don't allow attribute assignment

                return result

            except Exception as e:
                event_data["content"] = {
                    "error": str(e),
                    "type": type(e).__name__,
                }
                event = Event(**event_data)
                raise

        # Handle async functions
        @wraps(f)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            # Similar to sync wrapper but async
            event_data = {
                "event_type": event_type or f.__name__,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }

            if capture_args:
                event_data["request"] = {
                    "args": list(args),
                    "kwargs": kwargs,
                }

            try:
                result = await f(*args, **kwargs)

                if capture_result:
                    if isinstance(result, BaseModel):
                        event_data["content"] = result.model_dump()
                    elif hasattr(result, "__dict__"):
                        event_data["content"] = vars(result)
                    else:
                        event_data["content"] = result

                event = Event(**event_data)

                if hasattr(result, "__dict__") and not isinstance(
                    result, (str, int, float, bool, list, dict)
                ):
                    try:
                        result.__event__ = event
                    except (AttributeError, TypeError):
                        pass

                return result

            except Exception as e:
                event_data["content"] = {
                    "error": str(e),
                    "type": type(e).__name__,
                }
                event = Event(**event_data)
                raise

        # Return appropriate wrapper
        if asyncio.iscoroutinefunction(f):
            return async_wrapper
        else:
            return wrapper

    # Handle being called with or without parentheses
    if func is None:
        return decorator
    else:
        return decorator(func)


# Create specialized event types
LogEvent = create_model(
    "LogEvent",
    fields={
        **BASE_EVENT_FIELDS,
        "level": FieldTemplate(
            base_type=str,
            description="Log level",
            default="INFO",
        ),
        "logger": FieldTemplate(
            base_type=str,
            description="Logger name",
            nullable=True,
        ),
    },
)

MetricEvent = create_model(
    "MetricEvent",
    fields={
        **BASE_EVENT_FIELDS,
        "metric_name": FieldTemplate(
            base_type=str,
            description="Name of the metric",
        ),
        "value": FieldTemplate(
            base_type=float,
            description="Metric value",
        ),
        "unit": FieldTemplate(
            base_type=str,
            description="Unit of measurement",
            nullable=True,
        ),
        "tags": FieldTemplate(
            base_type=str,
            description="Metric tags",
            listable=True,
            default=list,
        ),
    },
)


__all__ = [
    "Event",
    "as_event",
    "BASE_EVENT_FIELDS",
    "LogEvent",
    "MetricEvent",
]
