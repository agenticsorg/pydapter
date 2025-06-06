from pydantic import BaseModel
from pydantic_core import PydanticUndefined
from pydapter.exceptions import ValidationError
from pydapter.fields.types import Field, Undefined

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


PARAMS = Field(
    name="params",
    annotation=dict,
    default_factory=dict,
    validator=lambda cls, v: validate_model_to_params(v),
    validator_kwargs={"mode": "before"},
    immutable=True,
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


PARAM_TYPE = Field(
    name="param_type",
    annotation=type,  # Simplified annotation to avoid GenericAlias issues
    validator=lambda cls, v: validate_model_to_type(v),
    validator_kwargs={"mode": "before"},
    immutable=True,
)

PARAM_TYPE_NULLABLE = Field(
    name="param_type_nullable",
    annotation=type,  # Simplified annotation to avoid UnionType issues
    default=None,
    validator=lambda cls, v: validate_model_to_type(v, nullable=True),
    validator_kwargs={"mode": "before"},
    immutable=True,
)
