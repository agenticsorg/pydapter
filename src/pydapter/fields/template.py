"""Field template implementation for compositional field definitions.

This module provides FieldTemplate, a frozen dataclass that enables
compositional field definitions with lazy materialization and aggressive caching.
"""

from __future__ import annotations

import os
import threading
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Annotated, Any

from typing_extensions import Self, override

from pydapter.exceptions import ValidationError

# Cache of valid Pydantic Field parameters
_PYDANTIC_FIELD_PARAMS: set[str] | None = None


def _get_pydantic_field_params() -> set[str]:
    """Get valid Pydantic Field parameters (cached)."""
    global _PYDANTIC_FIELD_PARAMS
    if _PYDANTIC_FIELD_PARAMS is None:
        import inspect

        from pydantic import Field as PydanticField

        _PYDANTIC_FIELD_PARAMS = set(inspect.signature(PydanticField).parameters.keys())
        _PYDANTIC_FIELD_PARAMS.discard("kwargs")
    return _PYDANTIC_FIELD_PARAMS


# Global cache for annotated types with bounded size
_MAX_CACHE_SIZE = int(os.environ.get("LIONAGI_FIELD_CACHE_SIZE", "10000"))
_annotated_cache: OrderedDict[tuple[type, tuple[FieldMeta, ...]], type] = OrderedDict()
_cache_lock = threading.RLock()  # Thread-safe access to cache

# Configurable limit on metadata items to prevent explosion
METADATA_LIMIT = int(os.environ.get("LIONAGI_FIELD_META_LIMIT", "10"))


@dataclass(slots=True, frozen=True)
class FieldMeta:
    """Immutable metadata container for field templates."""

    key: str
    value: Any

    @override
    def __hash__(self) -> int:
        """Make metadata hashable for caching.

        Note: For callables, we hash by id to maintain identity semantics.
        """
        # For callables, use their id
        if callable(self.value):
            return hash((self.key, id(self.value)))
        # For other values, try to hash directly
        try:
            return hash((self.key, self.value))
        except TypeError:
            # Fallback for unhashable types
            return hash((self.key, str(self.value)))

    @override
    def __eq__(self, other: object) -> bool:
        """Compare metadata for equality.

        For callables, compare by id to increase cache hits when the same
        validator instance is reused. For other values, use standard equality.
        """
        if not isinstance(other, FieldMeta):
            return NotImplemented

        if self.key != other.key:
            return False

        # For callables, compare by identity
        if callable(self.value) and callable(other.value):
            return id(self.value) == id(other.value)

        # For other values, use standard equality
        return bool(self.value == other.value)


@dataclass(slots=True, frozen=True, init=False)
class FieldTemplate:
    """Field template for compositional field definitions.

    This class provides a way to define field templates that can be composed
    and materialized lazily with aggressive caching for performance.

    Attributes:
        base_type: The base Python type for this field
        metadata: Tuple of metadata to attach via Annotated

    Environment Variables:
        LIONAGI_FIELD_CACHE_SIZE: Maximum number of cached annotated types (default: 10000)
        LIONAGI_FIELD_META_LIMIT: Maximum metadata items per template (default: 10)

    Example:
        >>> tmpl = FieldTemplate(str)
        >>> nullable_tmpl = tmpl.as_nullable()
        >>> annotated_type = nullable_tmpl.annotated()
    """

    base_type: type[Any]
    metadata: tuple[FieldMeta, ...] = field(default_factory=tuple)

    def __init__(
        self,
        base_type: type[Any],
        metadata: tuple[FieldMeta, ...] | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize FieldTemplate with optional metadata and kwargs.

        Args:
            base_type: The base Python type for this field
            metadata: Tuple of metadata to attach via Annotated
            **kwargs: Additional metadata as keyword arguments that will be converted to FieldMeta
        """
        # Convert kwargs to FieldMeta objects
        meta_list = list(metadata) if metadata else []

        # Handle special kwargs that trigger method calls
        if "nullable" in kwargs and kwargs["nullable"]:
            # Add nullable marker
            meta_list.append(FieldMeta("nullable", True))
            kwargs.pop("nullable")
        if "listable" in kwargs and kwargs["listable"]:
            # Change base type to list
            base_type = list[base_type]  # type: ignore
            meta_list.append(FieldMeta("listable", True))
            kwargs.pop("listable")

        # Convert remaining kwargs to FieldMeta
        for key, value in kwargs.items():
            meta_list.append(FieldMeta(key, value))

        # Use object.__setattr__ to set frozen dataclass fields
        object.__setattr__(self, "base_type", base_type)
        object.__setattr__(self, "metadata", tuple(meta_list))

        # Manually call __post_init__ since we have a custom __init__
        self.__post_init__()

    def __post_init__(self) -> None:
        """Validate metadata limit after initialization."""
        if len(self.metadata) > METADATA_LIMIT:
            import warnings

            warnings.warn(
                f"FieldTemplate has {len(self.metadata)} metadata items, "
                f"exceeding recommended limit of {METADATA_LIMIT}. "
                "Consider simplifying the field definition.",
                stacklevel=3,  # Show user's call site, not __post_init__
            )

    # ---- factory helpers -------------------------------------------------- #

    def as_nullable(self) -> Self:
        """Create a new template that allows None values.

        Returns:
            New FieldTemplate with nullable metadata added
        """
        # Add nullable marker to metadata
        new_metadata = (*self.metadata, FieldMeta("nullable", True))
        return type(self)(self.base_type, new_metadata)

    def as_listable(self) -> Self:
        """Create a new template that wraps the type in a list.

        Note: This produces list[T] which is a types.GenericAlias in Python 3.11+,
        not typing.List. This is intentional for better performance and native support.

        Returns:
            New FieldTemplate with list wrapper
        """
        # Change base type to list of current type
        new_base = list[self.base_type]  # type: ignore
        # Add listable marker to metadata
        new_metadata = (*self.metadata, FieldMeta("listable", True))
        return type(self)(new_base, new_metadata)

    def with_validator(self, f: Callable[[Any], bool]) -> Self:
        """Add a validator function to this template.

        Args:
            f: Validator function that takes a value and returns bool

        Returns:
            New FieldTemplate with validator added
        """
        # Add validator to metadata
        new_metadata = (*self.metadata, FieldMeta("validator", f))
        return type(self)(self.base_type, new_metadata)

    def with_description(self, description: str) -> Self:
        """Add a description to this template.

        Args:
            description: Human-readable description of the field

        Returns:
            New FieldTemplate with description added
        """
        # Remove any existing description
        filtered_metadata = tuple(m for m in self.metadata if m.key != "description")
        new_metadata = (*filtered_metadata, FieldMeta("description", description))
        return type(self)(self.base_type, new_metadata)

    def with_default(self, default: Any) -> Self:
        """Add a default value to this template.

        Args:
            default: Default value for the field

        Returns:
            New FieldTemplate with default added
        """
        # Remove any existing default metadata to avoid conflicts
        filtered_metadata = tuple(m for m in self.metadata if m.key != "default")
        new_metadata = (*filtered_metadata, FieldMeta("default", default))
        return type(self)(self.base_type, new_metadata)

    def with_frozen(self, frozen: bool = True) -> Self:
        """Mark this field as frozen (immutable after creation).

        Args:
            frozen: Whether the field should be frozen

        Returns:
            New FieldTemplate with frozen setting
        """
        # Remove any existing frozen metadata
        filtered_metadata = tuple(m for m in self.metadata if m.key != "frozen")
        new_metadata = (*filtered_metadata, FieldMeta("frozen", frozen))
        return type(self)(self.base_type, new_metadata)

    def with_alias(self, alias: str) -> Self:
        """Add an alias to this field.

        Args:
            alias: Alternative name for the field

        Returns:
            New FieldTemplate with alias
        """
        filtered_metadata = tuple(m for m in self.metadata if m.key != "alias")
        new_metadata = (*filtered_metadata, FieldMeta("alias", alias))
        return type(self)(self.base_type, new_metadata)

    def with_title(self, title: str) -> Self:
        """Add a title to this field.

        Args:
            title: Human-readable title for the field

        Returns:
            New FieldTemplate with title
        """
        filtered_metadata = tuple(m for m in self.metadata if m.key != "title")
        new_metadata = (*filtered_metadata, FieldMeta("title", title))
        return type(self)(self.base_type, new_metadata)

    def with_exclude(self, exclude: bool = True) -> Self:
        """Mark this field to be excluded from serialization.

        Args:
            exclude: Whether to exclude the field

        Returns:
            New FieldTemplate with exclude setting
        """
        filtered_metadata = tuple(m for m in self.metadata if m.key != "exclude")
        new_metadata = (*filtered_metadata, FieldMeta("exclude", exclude))
        return type(self)(self.base_type, new_metadata)

    def with_metadata(self, key: str, value: Any) -> Self:
        """Add custom metadata to this field.

        Args:
            key: Metadata key
            value: Metadata value

        Returns:
            New FieldTemplate with custom metadata
        """
        # Replace existing metadata with same key
        filtered_metadata = tuple(m for m in self.metadata if m.key != key)
        new_metadata = (*filtered_metadata, FieldMeta(key, value))
        return type(self)(self.base_type, new_metadata)

    def with_json_schema_extra(self, **kwargs: Any) -> Self:
        """Add JSON schema extra information.

        Args:
            **kwargs: Key-value pairs for json_schema_extra

        Returns:
            New FieldTemplate with json_schema_extra
        """
        # Get existing json_schema_extra or create new dict
        existing = self.extract_metadata("json_schema_extra") or {}
        updated = {**existing, **kwargs}

        filtered_metadata = tuple(
            m for m in self.metadata if m.key != "json_schema_extra"
        )
        new_metadata = (*filtered_metadata, FieldMeta("json_schema_extra", updated))
        return type(self)(self.base_type, new_metadata)

    def create_field(self) -> Any:
        """Create a Pydantic FieldInfo object from this template.

        Returns:
            A Pydantic FieldInfo object with all metadata applied
        """
        from pydantic import Field as PydanticField

        # Get valid Pydantic Field parameters (cached)
        pydantic_field_params = _get_pydantic_field_params()

        # Extract metadata for FieldInfo
        field_kwargs = {}

        for meta in self.metadata:
            if meta.key == "default":
                # Handle callable defaults as default_factory
                if callable(meta.value):
                    field_kwargs["default_factory"] = meta.value
                else:
                    field_kwargs["default"] = meta.value
            elif meta.key == "validator":
                # Validators are handled separately in create_model
                continue
            elif meta.key in pydantic_field_params:
                # Pass through standard Pydantic field attributes
                field_kwargs[meta.key] = meta.value
            elif meta.key in {"nullable", "listable"}:
                # These are FieldTemplate markers, don't pass to FieldInfo
                pass
            else:
                # Any other metadata goes in json_schema_extra
                if "json_schema_extra" not in field_kwargs:
                    field_kwargs["json_schema_extra"] = {}
                field_kwargs["json_schema_extra"][meta.key] = meta.value

        # Handle nullable case - ensure default is set if not already
        if (
            self.is_nullable
            and "default" not in field_kwargs
            and "default_factory" not in field_kwargs
        ):
            field_kwargs["default"] = None

        return PydanticField(**field_kwargs)

    # ---- materialization -------------------------------------------------- #

    def annotated(self) -> type[Any]:
        """Materialize this template into an Annotated type.

        This method is cached to ensure repeated calls return the same
        type object for performance and identity checks. The cache is bounded
        using LRU eviction to prevent unbounded memory growth.

        Returns:
            Annotated type with all metadata attached
        """
        # Check cache first with thread safety
        cache_key = (self.base_type, self.metadata)

        with _cache_lock:
            if cache_key in _annotated_cache:
                # Move to end to mark as recently used
                _annotated_cache.move_to_end(cache_key)
                return _annotated_cache[cache_key]

            # Handle nullable case - wrap in Optional-like union
            actual_type = self.base_type
            if any(m.key == "nullable" and m.value for m in self.metadata):
                # Use union syntax for nullable
                actual_type = actual_type | None  # type: ignore

            if self.metadata:
                # Python 3.10 doesn't support unpacking in Annotated, so we need to build it differently
                # We'll use Annotated.__class_getitem__ to build the type dynamically
                args = [actual_type] + list(self.metadata)
                result = Annotated.__class_getitem__(tuple(args))  # type: ignore
            else:
                result = actual_type  # type: ignore[misc]

            # Cache the result with LRU eviction
            _annotated_cache[cache_key] = result  # type: ignore[assignment]

            # Evict oldest if cache is too large (guard against empty cache)
            while len(_annotated_cache) > _MAX_CACHE_SIZE:
                try:
                    _annotated_cache.popitem(last=False)  # Remove oldest
                except KeyError:
                    # Cache became empty during race, safe to continue
                    break

        return result  # type: ignore[return-value]

    def extract_metadata(self, key: str) -> Any:
        """Extract metadata value by key.

        Args:
            key: Metadata key to look for

        Returns:
            Metadata value if found, None otherwise
        """
        for m in self.metadata:
            if m.key == key:
                return m.value
        return None

    def has_validator(self) -> bool:
        """Check if this template has a validator.

        Returns:
            True if validator exists in metadata
        """
        return any(m.key == "validator" for m in self.metadata)

    def is_valid(self, value: Any) -> bool:
        """Check if a value is valid against all validators in this template.

        Args:
            value: Value to validate

        Returns:
            True if all validators pass, False otherwise
        """
        for m in self.metadata:
            if m.key == "validator":
                validator = m.value
                if not validator(value):
                    return False
        return True

    def validate(self, value: Any, field_name: str | None = None) -> None:
        """Validate a value against all validators, raising ValidationError on failure.

        Args:
            value: Value to validate
            field_name: Optional field name for error context

        Raises:
            ValidationError: If any validator fails
        """
        # Early exit if no validators
        if not self.has_validator():
            return

        for i, m in enumerate(self.metadata):
            if m.key == "validator":
                validator = m.value
                if not validator(value):
                    # Try to get a useful name for the validator
                    validator_name = getattr(validator, "__name__", f"validator_{i}")
                    raise ValidationError(
                        f"Validation failed for {validator_name}",
                        field_name=field_name,
                        value=value,
                        validator_name=validator_name,
                    )

    @property
    def is_nullable(self) -> bool:
        """Check if this field allows None values."""
        return any(m.key == "nullable" and m.value for m in self.metadata)

    @property
    def is_listable(self) -> bool:
        """Check if this field is a list type."""
        return any(m.key == "listable" and m.value for m in self.metadata)

    @override
    def __repr__(self) -> str:
        """String representation of the template."""
        attrs = []
        if self.is_nullable:
            attrs.append("nullable")
        if self.is_listable:
            attrs.append("listable")
        if self.has_validator():
            attrs.append("validated")

        attr_str = f" [{', '.join(attrs)}]" if attrs else ""
        return f"FieldTemplate({self.base_type.__name__}{attr_str})"
