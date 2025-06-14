import contextlib
from datetime import datetime, timezone

from pydapter.exceptions import ValidationError
from pydapter.fields.template import FieldTemplate

__all__ = (
    "DATETIME",
    "DATETIME_NULLABLE",
    "validate_datetime",
    "datetime_serializer",
)


def validate_datetime(
    v: datetime | str,
    /,
    nullable: bool = False,
) -> datetime | None:
    if not v and nullable:
        return None
    if isinstance(v, datetime):
        return v
    if isinstance(v, str):
        with contextlib.suppress(ValueError):
            return datetime.fromisoformat(v)
    raise ValidationError(
        "Invalid datetime format, must be ISO 8601 or datetime object"
    )


def datetime_serializer(v: datetime, /) -> str:
    return v.isoformat()


def datetime_validator(v):
    return validate_datetime(v)


def nullable_datetime_validator(v):
    return validate_datetime(v, nullable=True)


DATETIME = FieldTemplate(
    base_type=datetime,
    default=lambda: datetime.now(tz=timezone.utc),  # Will be treated as default_factory
    validator=datetime_validator,
    description="Datetime field with timezone awareness",
)

DATETIME_NULLABLE = FieldTemplate(
    base_type=datetime,
    nullable=True,
    validator=nullable_datetime_validator,
    description="Nullable datetime field",
)
