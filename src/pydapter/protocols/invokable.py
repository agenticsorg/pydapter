import asyncio
from asyncio.log import logger
from collections.abc import Callable
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from pydantic import PrivateAttr
from pydapter.fields.execution import Execution, ExecutionStatus

from .utils import validate_model_to_dict


@runtime_checkable
class Invokable(Protocol):
    """An object that can be invoked with a request"""

    request: dict | None
    execution: Execution
    _handler: Callable | None
    _handler_args: tuple[Any, ...]
    _handler_kwargs: dict[str, Any]


class InvokableMixin:
    """An executable can be invoked with a request"""

    _handler: Callable | None = PrivateAttr(None)
    _handler_args: tuple[Any, ...] = PrivateAttr(())
    _handler_kwargs: dict[str, Any] = PrivateAttr({})

    if TYPE_CHECKING:
        request: dict | None
        execution: Execution

    @property
    def has_invoked(self) -> bool:
        return self.execution.status in [
            ExecutionStatus.COMPLETED,
            ExecutionStatus.FAILED,
        ]

    async def _invoke(self):
        if self._handler is None:
            raise ValueError("Event invoke function is not set.")
        if asyncio.iscoroutinefunction(self._handler):
            return await self._handler(*self._handler_args, **self._handler_kwargs)
        return self._handler(*self._handler_args, **self._handler_kwargs)

    async def invoke(self) -> None:
        start = asyncio.get_event_loop().time()
        response = None
        e1 = None

        try:
            # Use the endpoint as a context manager
            response = await self._invoke()

        except asyncio.CancelledError as ce:
            e1 = ce
            logger.warning("invoke() canceled by external request.")
            raise
        except Exception as ex:
            e1 = ex  # type: ignore

        finally:
            self.execution.duration = asyncio.get_event_loop().time() - start
            if response is None and e1 is not None:
                self.execution.error = str(e1)
                self.execution.status = ExecutionStatus.FAILED
                logger.error(f"invoke() failed for event {str(self.id)[:6]}...")
            else:
                self.execution.response_obj = response
                self.execution.response = validate_model_to_dict(response)
                self.execution.status = ExecutionStatus.COMPLETED
            self.execution.updated_at = datetime.now(tz=timezone.utc)
