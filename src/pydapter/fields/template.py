from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Annotated, Any, TypeVar, Union, get_args, get_origin

from pydantic import Field as PydanticField
from pydantic.fields import FieldInfo
from pydapter.fields.types import Field, Undefined, UndefinedType

if TYPE_CHECKING:
    from typing_extensions import Self

T = TypeVar("T")

__all__ = ("FieldTemplate",)


class FieldTemplate:
    """Template for creating reusable field definitions with naming flexibility.

    FieldTemplate provides a way to define field configurations that can be reused
    across multiple models with different field names. It supports Pydantic v2
    Annotated types and provides compositional methods for creating nullable and
    listable variations.

    Examples:
        >>> # Create a reusable email field template
        >>> email_template = FieldTemplate(
        ...     base_type=EmailStr,
        ...     description="Email address",
        ...     title="Email"
        ... )
        >>>
        >>> # Use the template in different models with different names
        >>> user_email = email_template.create_field("user_email")
        >>> contact_email = email_template.create_field("contact_email")
        >>>
        >>> # Create variations
        >>> optional_email = email_template.as_nullable()
        >>> email_list = email_template.as_listable()
    """

    def __init__(
        self,
        base_type: type | Any,
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
        **pydantic_field_kwargs: Any,
    ):
        """Initialize a field template.

        Args:
            base_type: The base type for the field (can be Annotated)
            default: Default value for the field
            default_factory: Factory function for default value
            title: Title for the field
            description: Description for the field
            examples: Examples for the field
            exclude: Whether to exclude the field from serialization
            frozen: Whether the field is frozen
            validator: Validator function for the field
            validator_kwargs: Keyword arguments for the validator
            alias: Alias for the field
            immutable: Whether the field is immutable
            **pydantic_field_kwargs: Additional Pydantic FieldInfo arguments
        """
        self.base_type = base_type
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
        self.immutable = immutable
        self.pydantic_field_kwargs = pydantic_field_kwargs

        # Extract Pydantic FieldInfo from Annotated type if present
        self._extract_pydantic_info()

        # Cache for base field info (without overrides)
        self._base_field_info_cache: FieldInfo | None = None

    def _extract_pydantic_info(self) -> None:
        """Extract Pydantic FieldInfo from Annotated base_type."""
        self._extracted_type = self.base_type
        self._extracted_field_info = None

        # For constrained types (constr, conint, etc.), we should NOT extract
        # We need to preserve the full Annotated type with constraints
        if get_origin(self.base_type) is Annotated:
            args = get_args(self.base_type)

            # Check if this has constraint annotations (StringConstraints, Interval, etc.)
            has_constraints = False
            for arg in args[1:]:
                arg_str = str(arg)
                if any(
                    constraint in arg_str
                    for constraint in ["StringConstraints", "Interval", "Constraints"]
                ):
                    has_constraints = True
                    break

            if has_constraints:
                # This is a constrained type from constr/conint/etc
                # Keep the full Annotated type
                return

            # Otherwise extract normally
            self._extracted_type = args[0]

            # Look for FieldInfo in the annotations
            for arg in args[1:]:
                if isinstance(arg, FieldInfo):
                    self._extracted_field_info = arg
                    break

    def _get_base_field_info(self) -> dict[str, Any]:
        """Get base field info parameters with caching.

        This method caches the expensive operation of extracting and merging
        base parameters from extracted FieldInfo and template settings.

        Returns:
            Dictionary of base field parameters
        """
        if hasattr(self, "_base_params_cache"):
            return self._base_params_cache.copy()

        base_params = {}
        if self._extracted_field_info:
            # Extract relevant attributes from existing FieldInfo
            for attr in [
                "default",
                "default_factory",
                "title",
                "description",
                "examples",
                "exclude",
                "frozen",
                "alias",
            ]:
                value = getattr(self._extracted_field_info, attr, Undefined)
                if value is not Undefined:
                    base_params[attr] = value

        # Override with template-level settings
        template_params = {
            "default": self.default,
            "default_factory": self.default_factory,
            "title": self.title,
            "description": self.description,
            "examples": self.examples,
            "exclude": self.exclude,
            "frozen": self.frozen,
            "alias": self.alias,
            **self.pydantic_field_kwargs,
        }

        # Filter out Undefined values
        template_params = {
            k: v for k, v in template_params.items() if v is not Undefined
        }
        base_params.update(template_params)

        # Cache the result
        self._base_params_cache = base_params.copy()
        return base_params

    def _merge_field_info(self, **overrides: Any) -> FieldInfo:
        """Merge FieldInfo from various sources.

        This internal method combines field information from:
        1. Extracted FieldInfo from Annotated types
        2. Template-level settings
        3. Runtime overrides

        The precedence order is: overrides > template settings > extracted FieldInfo

        Args:
            **overrides: Keyword arguments that override template settings

        Returns:
            A Pydantic FieldInfo instance with merged settings
        """
        # Get base parameters (with caching)
        base_params = self._get_base_field_info()

        # Apply overrides
        base_params.update(overrides)

        # Create new FieldInfo
        return PydanticField(**base_params)

    def create_field(self, name: str, **overrides: Any) -> Field:
        """Create a Field instance with the given name.

        This method creates a new Field instance using the template's configuration
        combined with any overrides provided. The resulting Field can be used in
        pydapter's create_model function.

        Args:
            name: The name for the field. Must be a valid Python identifier.
            **overrides: Keyword arguments to override template settings.
                Supported overrides include all Field constructor parameters
                like default, description, title, validator, etc.

        Returns:
            A Field instance configured with the template settings and overrides.

        Raises:
            ValueError: If the field name is not a valid Python identifier.
            TypeError: If there are conflicts between template settings and overrides.
            RuntimeError: If attempting to override a frozen field property.

        Examples:
            >>> template = FieldTemplate(base_type=str, description="A string field")
            >>> field = template.create_field("username", title="User Name")
            >>> # field will have description from template and title from override
        """
        # Validate field name
        if not name.isidentifier():
            raise ValueError(
                f"Field name '{name}' is not a valid Python identifier. "
                f"Field names must start with a letter or underscore and contain "
                f"only letters, numbers, and underscores."
            )

        # Check for frozen field overrides
        if self.frozen and "frozen" in overrides and overrides["frozen"] is False:
            raise RuntimeError(
                f"Cannot override frozen=True on field '{name}'. "
                f"Frozen fields cannot be made mutable at runtime."
            )

        # Validate that both default and default_factory are not provided
        effective_default = overrides.get("default", self.default)
        effective_default_factory = overrides.get(
            "default_factory", self.default_factory
        )

        if (
            effective_default is not Undefined
            and effective_default_factory is not Undefined
        ):
            raise ValueError(
                f"Field '{name}' cannot have both 'default' and 'default_factory'. "
                f"Please provide only one."
            )
        # Merge pydapter-specific kwargs
        pydapter_kwargs = {
            "validator": self.validator,
            "validator_kwargs": self.validator_kwargs,
            "immutable": self.immutable,
        }

        # Extract pydapter-specific overrides
        pydapter_overrides = {}
        pydantic_overrides = {}

        for key, value in overrides.items():
            if key in ["validator", "validator_kwargs", "immutable"]:
                pydapter_overrides[key] = value
            else:
                pydantic_overrides[key] = value

        # Update pydapter kwargs
        for key, value in pydapter_overrides.items():
            if value is not Undefined:
                pydapter_kwargs[key] = value

        # Get merged FieldInfo
        field_info = self._merge_field_info(**pydantic_overrides)

        # Create the final annotation
        # If we have a constrained type (where _extracted_type == base_type), use it as-is
        if (
            self._extracted_type == self.base_type
            and get_origin(self.base_type) is Annotated
        ):
            # This is a constrained type, use as-is
            final_annotation = self._extracted_type
        elif self._extracted_field_info or pydantic_overrides:
            final_annotation = Annotated[self._extracted_type, field_info]
        else:
            final_annotation = self._extracted_type

        # Create the Field - handle default vs default_factory properly
        field_kwargs = {
            "name": name,
            "annotation": final_annotation,
        }

        # Extract field info attributes carefully
        # Check for PydanticUndefined as well
        from pydantic_core import PydanticUndefined

        if hasattr(field_info, "default") and field_info.default not in (
            Undefined,
            PydanticUndefined,
        ):
            field_kwargs["default"] = field_info.default
        elif hasattr(
            field_info, "default_factory"
        ) and field_info.default_factory not in (None, Undefined):
            field_kwargs["default_factory"] = field_info.default_factory

        # Add other attributes
        for attr in ["title", "description", "examples", "exclude", "frozen", "alias"]:
            if hasattr(field_info, attr):
                value = getattr(field_info, attr)
                if value is not None:
                    field_kwargs[attr] = value

        # Add pydapter-specific kwargs
        field_kwargs.update(pydapter_kwargs)

        # Extract json_schema_extra and pass it to Field's extra_info
        if hasattr(field_info, "json_schema_extra") and field_info.json_schema_extra:
            field_kwargs.update(field_info.json_schema_extra)

        return Field(**field_kwargs)

    def copy(self, **kwargs: Any) -> Self:
        """Create a copy of the template with updated values."""
        params = {
            "base_type": self.base_type,
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
            "immutable": self.immutable,
            **self.pydantic_field_kwargs,
        }
        params.update(kwargs)
        return FieldTemplate(**params)

    def as_nullable(self) -> Self:
        """Create a nullable version of this template.

        Returns a new FieldTemplate where the base type is modified to accept None
        values. The default value is set to None and any existing default_factory
        is removed. If the template has a validator, it's wrapped to handle None values.

        Returns:
            A new FieldTemplate instance that accepts None values

        Examples:
            >>> int_template = FieldTemplate(base_type=int, default=0)
            >>> nullable_int = int_template.as_nullable()
            >>> # nullable_int will have type Union[int, None] with default=None
        """
        # Create nullable type
        nullable_type = Union[self._extracted_type, None]
        if get_origin(self.base_type) is Annotated:
            # Preserve annotations but update the base type
            args = get_args(self.base_type)
            if len(args) > 1:
                # Extract the base type and annotations
                base = args[0]
                annotations = args[1:]
                # Create new Annotated with nullable base type
                nullable_type = Annotated[Union[base, None], *annotations]
            else:
                nullable_type = Annotated[Union[args[0], None]]

        # Wrap validator to handle None
        new_validator = Undefined
        if self.validator is not Undefined:
            original_validator = self.validator

            def nullable_validator(cls, v):
                if v is None:
                    return v
                if callable(original_validator):
                    return original_validator(cls, v)
                return v

            new_validator = nullable_validator

        return self.copy(
            base_type=nullable_type,
            default=None,
            default_factory=Undefined,
            validator=new_validator,
        )

    def as_listable(self, strict: bool = False) -> Self:
        """Create a listable version of this template.

        Returns a new FieldTemplate where the base type can accept either a single
        value or a list of values (flexible mode), or only lists (strict mode).

        Args:
            strict: If True, only lists are accepted. If False (default), both
                single values and lists are accepted.

        Returns:
            A new FieldTemplate instance that accepts lists

        Examples:
            >>> str_template = FieldTemplate(base_type=str)
            >>> # Flexible mode: accepts "value" or ["value1", "value2"]
            >>> flexible_list = str_template.as_listable(strict=False)
            >>> # Strict mode: only accepts ["value1", "value2"]
            >>> strict_list = str_template.as_listable(strict=True)
        """
        # Create list type
        if strict:
            list_type = list[self._extracted_type]
        else:
            list_type = Union[list[self._extracted_type], self._extracted_type]

        if get_origin(self.base_type) is Annotated:
            # Preserve annotations but update the base type
            args = get_args(self.base_type)
            # For Python 3.10 compatibility
            if strict:
                list_type = list[args[0]]
            else:
                list_type = Union[list[args[0]], args[0]]

        # Wrap validator to handle lists
        new_validator = Undefined
        if self.validator is not Undefined:
            original_validator = self.validator

            def listable_validator(cls, v):
                if isinstance(v, list):
                    if callable(original_validator):
                        return [original_validator(cls, item) for item in v]
                    return v
                else:
                    if strict:
                        raise ValueError("Expected a list")
                    if callable(original_validator):
                        return original_validator(cls, v)
                    return v

            new_validator = listable_validator

        return self.copy(base_type=list_type, validator=new_validator)
