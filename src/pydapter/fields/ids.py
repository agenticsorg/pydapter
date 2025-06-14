import contextlib
from uuid import UUID, uuid4

from pydapter.exceptions import ValidationError
from pydapter.fields.template import FieldTemplate

__all__ = (
    "ID_FROZEN",
    "ID_MUTABLE",
    "ID_NULLABLE",
    "validate_uuid",
    "serialize_uuid",
)


def validate_uuid(v: UUID | str, /, nullable: bool = False) -> UUID | None:
    if not v and nullable:
        return None
    if isinstance(v, UUID):
        return v
    with contextlib.suppress(ValueError):
        return UUID(str(v))
    raise ValidationError("id must be a valid UUID or UUID string")


def serialize_uuid(v: UUID, /) -> str:
    return str(v)


def uuid_validator(v) -> UUID | None:
    return validate_uuid(v)


def nullable_uuid_validator(v) -> UUID | None:
    return validate_uuid(v, nullable=True)


ID_FROZEN = FieldTemplate(
    base_type=UUID,
    default=uuid4,  # Will be treated as default_factory since it's callable
    validator=uuid_validator,
    description="Frozen Unique identifier",
    frozen=True,
)

ID_MUTABLE = FieldTemplate(
    base_type=UUID,
    default=uuid4,  # Will be treated as default_factory since it's callable
    validator=lambda v: validate_uuid(v),
    description="Mutable Unique identifier",
)

ID_NULLABLE = FieldTemplate(
    base_type=UUID,
    nullable=True,
    validator=lambda v: validate_uuid(v, nullable=True),
    description="Nullable Unique identifier",
)
