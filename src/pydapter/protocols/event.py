import asyncio
import json
from collections.abc import Callable
from datetime import datetime, timezone
from functools import wraps
from typing import Any

from pydantic import JsonValue

from pydapter.async_core import AsyncAdapter
from pydapter.core import Adapter
from pydapter.fields import (
    DATETIME,
    EMBEDDING,
    EXECUTION,
    ID_FROZEN,
    PARAMS,
    Embedding,
    create_model,
)
from pydapter.fields.template import FieldTemplate
from pydapter.protocols.base_model import BasePydapterModel
from pydapter.protocols.cryptographical import CryptographicalMixin
from pydapter.protocols.embeddable import EmbeddableMixin
from pydapter.protocols.identifiable import IdentifiableMixin
from pydapter.protocols.invokable import InvokableMixin
from pydapter.protocols.temporal import TemporalMixin
from pydapter.protocols.types import Log

BASE_EVENT_FIELDS = {
    "id": ID_FROZEN,
    "created_at": DATETIME,
    "updated_at": DATETIME,
    "embedding": EMBEDDING,
    "execution": EXECUTION,
    "request": PARAMS,
    "content": FieldTemplate(
        base_type=JsonValue,  # JsonValue can be str, dict, list, etc.
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
        description="SHA256 hash of the content",
        nullable=True,
        default=None,
    ),
}

_BaseEvent = create_model(
    model_name="BaseEvent",
    doc="Base event model of Pydapter protocol",
    fields=BASE_EVENT_FIELDS,
    base=BasePydapterModel,
)


class Event(
    _BaseEvent,
    IdentifiableMixin,
    InvokableMixin,
    TemporalMixin,
    EmbeddableMixin,
    CryptographicalMixin,
):
    def __init__(
        self,
        handler: Callable,
        handler_arg: tuple[Any, ...],
        handler_kwargs: dict[str, Any],
        **data,
    ):
        super().__init__(**data)
        self._handler = handler
        self._handler_args = handler_arg
        self._handler_kwargs = handler_kwargs

    def update_timestamp(self):
        if self.execution.updated_at is not None:
            if self.updated_at is None:
                self.updated_at = self.execution.updated_at
            elif self.updated_at < self.execution.updated_at:
                self.updated_at = self.execution.updated_at
        else:
            self.updated_at = datetime.now(tz=timezone.utc)

    def to_log(self, event_type: str | None = None, hash_content: bool = False) -> Log:
        """Convert the event to a log entry."""
        # Use provided event_type or fall back to the event's event_type or class name
        log_event_type = (
            event_type or getattr(self, "event_type", None) or type(self).__name__
        )

        # Prepare content - use existing content or create from request/response
        if self.content is not None:
            content = (
                self.content
                if isinstance(self.content, str)
                else json.dumps(self.content)
            )
        else:
            content_dict = {
                "request": self.request,
                "response": self.execution.response,
            }
            content = json.dumps(content_dict)
            # Set the content on the event so it can be hashed
            self.content = content

        # Hash content if requested
        sha256_value = None
        if hash_content:
            self.hash_content()
            sha256_value = getattr(self, "sha256", None)

        # Create metadata
        metadata = {
            "execution_status": (
                self.execution.status.value
                if hasattr(self.execution.status, "value")
                else str(self.execution.status)
            ),
            "execution_duration": self.execution.duration,
        }

        if self.execution.error:
            metadata["error"] = self.execution.error

        return Log(
            id=str(self.id),
            event_type=log_event_type,
            content=content,
            embedding=self.embedding if self.embedding else [],  # Default to empty list
            metadata=metadata,
            created_at=self.created_at.isoformat() if self.created_at else None,
            updated_at=self.updated_at.isoformat() if self.updated_at else None,
            duration=self.execution.duration,
            status=(
                self.execution.status.value
                if hasattr(self.execution.status, "value")
                else str(self.execution.status)
            ),
            error=self.execution.error,
            sha256=sha256_value,
        )


# overall needs more logging
def as_event(
    *,
    event_type: str | None = None,
    request_arg: str | None = None,
    embed_content: bool = False,
    embed_function: Callable[..., Embedding] | None = None,
    adapt: bool = False,
    adapter: type[Adapter | AsyncAdapter] | None = None,
    content_parser: Callable | None = None,
    strict_content: bool = False,
    **kw,
):
    """
    - event_type, for example, "api_call", "message", "task", etc.
    - request_arg, the name of the request argument in the function signature
        (will be passed to the event as part of content if content_function is not provided)
    - embed_content, if True, the content will be embedded using the embed_function
    - embed_function, a function that takes the content and returns an embedding
    - adapt, if True, the event will be adapted to the specified adapter
    - adapter, the adapter class to adapt the event to
    - content_function, a function that takes the response_obj and returns the content
        (if not provided, the content {"request": request, "response": response})
        where response is a dict representation of the response object
    **kw, additional keyword arguments to pass to the adapter
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Event:
            request_obj = kwargs.get(request_arg) if request_arg else None
            if len(args) > 2 and hasattr(args[0], "__class__"):
                args = args[1:]
            request_obj = args[0] if request_obj is None else request_obj
            event = Event(
                handler=func,
                handler_arg=list(args),
                handler_kwargs=kwargs,
                event_type=event_type,
                request=request_obj,
            )
            try:
                await event.invoke()

                if content_parser is not None:
                    try:
                        event.content = content_parser(event.execution.response_obj)
                    except Exception as e:
                        if strict_content:
                            event.updated_at = datetime.now(tz=timezone.utc)
                            event.content = None
                            event.execution.error = str(e)
                            event.execution.status = event.execution.FAILED
                            event.execution.response = None
                            return event

                        event.content = {
                            "request": event.request,
                            "response": event.execution.response,
                        }

                if embed_content and embed_function is not None:
                    content = (
                        json.dumps(event.content)
                        if not isinstance(event.content, str)
                        else event.content
                    )
                    if content is None:
                        # need some logging here
                        return event

                    embed_response = None
                    try:
                        if asyncio.iscoroutinefunction(embed_function):
                            embed_response = await embed_function(content)
                        else:
                            embed_response = embed_function(content)
                    except Exception:
                        # some logging on embedding failure
                        pass

                    # Check if the response is already a valid embedding (list of floats)
                    if isinstance(embed_response, list) and all(
                        isinstance(x, (int, float)) for x in embed_response
                    ):
                        event.embedding = embed_response
                    else:
                        # Try to parse the response
                        try:
                            event.embedding = EmbeddableMixin.parse_embedding_response(
                                embed_response
                            )
                        except Exception:
                            # some logging on embedding parsing failure
                            pass

            except Exception:
                # do some logging on the mighty catch all failure
                pass

            finally:
                if adapt and adapter is not None:
                    try:
                        await adapter.to_obj(event.to_log(event_type=event_type), **kw)
                    except Exception:
                        # logging here
                        pass

            return event

        return wrapper

    return decorator
