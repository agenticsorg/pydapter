from pydantic import BaseModel
from pydantic_core import PydanticUndefined

from pydapter.exceptions import ValidationError
from pydapter.fields.template import FieldTemplate
from pydapter.fields.types import Undefined

__all__ = (
    "PARAMS",
    "PARAM_TYPE",
    "PARAM_TYPE_NULLABLE",
)


def validate_model_to_params(v, /) -> dict:
    if v in [None, {}, [], Undefined, PydanticUndefined]:
        return {}
    if isinstance(v, dict):
        return v
    if isinstance(v, BaseModel):
        return v.model_dump()
    raise ValidationError(
        "Invalid params input, must be a dictionary or BaseModel instance"
    )


PARAMS = FieldTemplate(
    base_type=dict,
    default=dict,
    validator=lambda v: validate_model_to_params(v),
    description="Parameters dictionary or BaseModel instance",
)


def validate_model_to_type(v, /, nullable: bool = False) -> type | None:
    if not v:
        if nullable:
            return None
        raise ValidationError("Model type cannot be None or empty")
    if v is BaseModel:
        return v
    if isinstance(v, type) and issubclass(v, BaseModel):
        return v
    if isinstance(v, BaseModel):
        return v.__class__
    raise ValidationError(
        "Invalid model type, must be a pydantic class or BaseModel instance"
    )


PARAM_TYPE = FieldTemplate(
    base_type=type,
    validator=lambda v: validate_model_to_type(v),
    description="Pydantic model type",
)

PARAM_TYPE_NULLABLE = FieldTemplate(
    base_type=type,
    nullable=True,
    validator=lambda v: validate_model_to_type(v, nullable=True),
    description="Optional Pydantic model type",
)
