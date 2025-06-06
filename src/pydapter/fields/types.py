from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any, Literal

from pydantic import BaseModel
from pydantic import Field as PydanticField
from pydantic import create_model as create_pydantic_model
from pydantic import field_validator
from pydantic.fields import FieldInfo
from pydapter.exceptions import ValidationError

__all__ = (
    "Field",
    "Undefined",
    "UndefinedType",
    "create_model",
    "ID",
    "Embedding",
    "Metadata",
)


ID = uuid.UUID
Embedding = list[float]
Metadata = dict


class UndefinedType:
    __slots__ = ("undefined",)

    def __init__(self) -> None:
        self.undefined = True

    def __bool__(self) -> Literal[False]:
        return False

    def __deepcopy__(self, memo):
        # Ensure UNDEFINED is universal
        return self

    def __repr__(self) -> Literal["UNDEFINED"]:
        return "UNDEFINED"


Undefined = UndefinedType()


class Field:
    """Field descriptor for Pydantic models."""

    __slots__ = (
        "name",
        "annotation",
        "default",
        "default_factory",
        "title",
        "description",
        "examples",
        "exclude",
        "frozen",
        "validator",
        "validator_kwargs",
        "alias",
        "extra_info",
        "immutable",
    )

    def __init__(
        self,
        name: str,
        annotation: type | UndefinedType = Undefined,
        default: Any = Undefined,
        default_factory: Callable | UndefinedType = Undefined,
        title: str | UndefinedType = Undefined,
        description: str | UndefinedType = Undefined,
        examples: list | UndefinedType = Undefined,
        exclude: bool | UndefinedType = Undefined,
        frozen: bool | UndefinedType = Undefined,
        validator: Callable | UndefinedType = Undefined,
        validator_kwargs: dict[Any, Any] | UndefinedType = Undefined,
        alias: str | UndefinedType = Undefined,
        immutable: bool = False,
        **extra_info: Any,
    ):
        """Initialize a field descriptor."""
        if default is not Undefined and default_factory is not Undefined:
            raise ValueError("Cannot have both default and default_factory")

        self.name = name
        self.annotation = annotation if annotation is not Undefined else Any
        self.default = default
        self.default_factory = default_factory
        self.title = title
        self.description = description
        self.examples = examples
        self.exclude = exclude
        self.frozen = frozen
        self.validator = validator
        self.validator_kwargs = validator_kwargs
        self.alias = alias
        self.extra_info = extra_info
        self.immutable = immutable

    def _to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "annotation": self.annotation,
            "default": self.default,
            "default_factory": self.default_factory,
            "title": self.title,
            "description": self.description,
            "examples": self.examples,
            "exclude": self.exclude,
            "frozen": self.frozen,
            "validator": self.validator,
            "validator_kwargs": self.validator_kwargs,
            "alias": self.alias,
            **self.extra_info,
        }

    @property
    def field_info(self) -> FieldInfo:
        params = {
            "default": self.default,
            "default_factory": self.default_factory,
            "title": self.title,
            "description": self.description,
            "examples": self.examples,
            "exclude": self.exclude,
            "frozen": self.frozen,
            "alias": self.alias,
            **self.extra_info,
        }
        field_obj: FieldInfo = PydanticField(**{
            k: v for k, v in params.items() if v is not Undefined
        })
        field_obj.annotation = (
            self.annotation if self.annotation is not Undefined else None
        )  # type: ignore[assignment]
        return field_obj

    @property
    def field_validator(self) -> dict[str, Callable] | None:
        if self.validator is Undefined:
            return None
        kwargs: dict[Any, Any] = (
            {} if self.validator_kwargs is Undefined else self.validator_kwargs  # type: ignore[assignment]
        )
        return {
            f"{self.name}_field_validator": field_validator(self.name, **kwargs)(
                self.validator
            )
        }

    def __hash__(self) -> int:
        return hash(self.name)

    def copy(self, **kwargs: Any) -> Field:
        """Create a copy of the field with updated values."""
        params = self._to_dict()
        params.update(kwargs)
        return Field(**params)

    def as_nullable(self, **kwargs) -> Field:
        """Create a copy of a field descriptor with a nullable annotation and None as default value.

        WARNING: the new_field will have no default value, nor default_factory.
        """
        annotation = str(self.annotation).lower().strip()
        if "none" in annotation or "optional" in annotation:
            return self.copy()

        # If the field has a validator, wrap it to handle None values
        new_validator = Undefined
        if self.validator is not Undefined:
            original_validator = self.validator

            def nullable_validator(cls, v):
                if v is None:
                    return v
                # Type guard: we know original_validator is not Undefined here
                if original_validator is not Undefined and callable(original_validator):
                    return original_validator(cls, v)
                return v

            new_validator = nullable_validator  # type: ignore[assignment]

        # Handle union type creation safely
        from typing import Union

        new_annotation = None
        if self.annotation is Undefined:
            new_annotation = type(None)
        else:
            try:
                new_annotation = self.annotation | None
            except TypeError:
                # Fallback for older Python versions or complex types
                new_annotation = Union[self.annotation, None]  # type: ignore[arg-type]

        return self.copy(
            annotation=new_annotation,
            default=None,
            default_factory=Undefined,
            validator=new_validator,
            **kwargs,
        )

    def as_listable(self, strict: bool = False, **kwargs) -> Field:
        """Create a copy of a field descriptor with a listable annotation.

        This method does not check whether the field is already listable.
        If strict is True, the annotation will be converted to a list of the current annotation.
        Otherwise, the list is an optional type.
        """
        # Handle annotation union safely
        from typing import Union

        annotation = None
        if strict:
            annotation = list[self.annotation]
        else:
            try:
                annotation = list[self.annotation] | self.annotation
            except TypeError:
                # Fallback for complex types
                annotation = Union[list[self.annotation], self.annotation]  # type: ignore[arg-type]

        # If the field has a validator, wrap it to handle lists
        new_validator = Undefined
        if self.validator is not Undefined:
            original_validator = self.validator

            def listable_validator(cls, v):
                if isinstance(v, list):
                    # Validate each item in the list
                    if original_validator is not Undefined and callable(
                        original_validator
                    ):
                        return [original_validator(cls, item) for item in v]
                    return v
                else:
                    # Single value - validate directly (only if not strict)
                    if strict:
                        raise ValueError("Expected a list")
                    if original_validator is not Undefined and callable(
                        original_validator
                    ):
                        return original_validator(cls, v)
                    return v

            new_validator = listable_validator  # type: ignore[assignment]

        return self.copy(annotation=annotation, validator=new_validator, **kwargs)

    def __setattr__(self, name: str, value: Any) -> None:
        if hasattr(self, "immutable") and self.immutable:
            raise AttributeError(f"Cannot modify immutable field {self.name}")
        object.__setattr__(self, name, value)


def create_model(
    model_name: str,
    config: dict[str, Any] | None = None,
    doc: str | None = None,
    base: type[BaseModel] | None = None,
    fields: list[Field] | dict[str, Field | Any] | None = None,
    frozen: bool = False,
):
    """Create a new pydantic model basing on fields and base class.

    Args:
        model_name (str): Name of the new model.
        config (dict[str, Any], optional): Configuration dictionary for the model.
        doc (str, optional): Documentation string for the model.
        base (type[BaseModel], optional): Base class to inherit from.
        fields (list[Field] | dict[str, Field | FieldTemplate], optional): List of fields or dict of field names to Field/FieldTemplate instances.
        frozen (bool, optional): Whether the model should be immutable (frozen).
    """
    if config and base:
        raise ValidationError(
            message="Error creating new model: cannot provide both config and base class",
            details={"model_name": model_name},
        )

    _use_fields: list[Field] = [] if isinstance(fields, dict) else fields or []

    if isinstance(fields, dict):
        # Import here to avoid circular imports
        from pydapter.fields.template import FieldTemplate

        for name, field_or_template in fields.items():
            if isinstance(field_or_template, FieldTemplate):
                # Create Field from FieldTemplate
                field = field_or_template.create_field(name)
            elif isinstance(field_or_template, dict):
                # Handle dict-style field definition
                field_dict = field_or_template.copy()
                field_dict["name"] = name
                field = Field(**field_dict)
            else:
                # Assume it's a Field
                field = field_or_template
                if hasattr(field, "name") and name != field.name:
                    field = field.copy(name=name)
            _use_fields.append(field)

    use_fields: dict[str, tuple[type, FieldInfo]] = {
        field.name: (field.annotation, field.field_info) for field in _use_fields
    }

    # Collect validators for fields that have them
    validators: dict[str, Callable[..., Any]] = {}
    for field in _use_fields:
        if field.validator is not Undefined and callable(field.validator):
            kwargs = (
                {} if field.validator_kwargs is Undefined else field.validator_kwargs
            )
            validator_name = f"validate_{field.name}"
            validators[validator_name] = field_validator(field.name, **kwargs)(
                field.validator
            )

    # Create the base model with validators included - handle type issues by filtering valid fields
    valid_fields = {
        name: (annotation, field_info)
        for name, (annotation, field_info) in use_fields.items()
        if annotation is not Undefined
    }

    model: type[BaseModel] = create_pydantic_model(
        model_name,
        __config__=config,
        __doc__=doc,
        __base__=base,
        __validators__=validators,
        **valid_fields,
    )

    if frozen:
        from pydantic import ConfigDict

        config_dict = getattr(model, "model_config", {})
        if isinstance(config_dict, dict):
            config_dict["frozen"] = True
            model.model_config = config_dict
        else:
            # If it's already a ConfigDict, create a new one with frozen=True
            new_config = ConfigDict(**config_dict, frozen=True)
            model.model_config = new_config
    return model
