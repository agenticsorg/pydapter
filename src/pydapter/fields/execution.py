from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict
from pydantic import Field as PydanticField
from pydantic import field_validator

from pydapter.exceptions import ValidationError
from pydapter.fields.params import validate_model_to_params
from pydapter.fields.template import FieldTemplate

__all__ = ("EXECUTION",)


class ExecutionStatus(str, Enum):
    """Status states for tracking action execution progress."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Execution(BaseModel):
    """Represents the execution state of an event."""

    model_config = ConfigDict(
        use_enum_values=True,
        arbitrary_types_allowed=True,
    )
    duration: float | None = None
    response: dict | None = None
    status: ExecutionStatus = ExecutionStatus.PENDING
    error: str | None = None
    response_obj: Any = PydanticField(None, exclude=True)
    updated_at: datetime | None = PydanticField(
        default_factory=lambda: datetime.now(tz=timezone.utc),
        exclude=True,
    )

    @field_validator("response", mode="before")
    def _validate_response(cls, v: BaseModel | dict | None):
        return validate_model_to_params(v)

    def validate_response(self):
        if self.response is None and self.response_obj is None:
            raise ValidationError("Response and response_obj are both None")
        if not isinstance(self.response, dict):
            self.response = validate_model_to_params(self.response_obj)


EXECUTION = FieldTemplate(
    base_type=Execution,
    default=Execution,
    validator=lambda v: v or Execution(),
    description="Execution state of an event",
)
