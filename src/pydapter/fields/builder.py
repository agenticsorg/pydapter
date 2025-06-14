"""Domain Model Builder - Fluent API for creating models with field families.

This module provides a builder pattern implementation for creating database models
using core field families and templates. It offers a fluent API that makes
model creation more intuitive and less error-prone.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydapter.fields.families import FieldFamilies, create_field_dict
from pydapter.fields.types import create_model

if TYPE_CHECKING:
    from pydantic import BaseModel

    from pydapter.fields.template import FieldTemplate


__all__ = ("DomainModelBuilder",)


class DomainModelBuilder:
    """Fluent builder for creating database models with field families.

    This class provides a fluent API for building Pydantic models by composing
    core field families and individual field templates. It supports method chaining
    for a clean, readable syntax.

    Examples:
        ```python
        # Create an entity with soft delete and audit fields
        TrackedEntity = (
            DomainModelBuilder("TrackedEntity")
            .with_entity_fields(timezone_aware=True)
            .with_soft_delete(timezone_aware=True)
            .with_audit_fields()
            .add_field("name", FieldTemplate(base_type=str, description="Entity name"))
            .build()
        )

        # Create a simple versioned model
        VersionedModel = (
            DomainModelBuilder("VersionedModel")
            .with_entity_fields()
            .with_audit_fields()
            .add_field("data", FieldTemplate(base_type=dict, default=dict))
            .build()
        )
        ```
    """

    def __init__(self, model_name: str, **model_config: Any):
        """Initialize the builder with a model name.

        Args:
            model_name: Name for the generated model class
            **model_config: Additional Pydantic model configuration options
                (e.g., orm_mode=True, validate_assignment=True)
        """
        self.model_name = model_name
        self.model_config = model_config
        self._fields: dict[str, FieldTemplate] = {}

    def with_entity_fields(self, timezone_aware: bool = False) -> DomainModelBuilder:
        """Add basic entity fields (id, created_at, updated_at).

        Args:
            timezone_aware: If True, uses timezone-aware datetime fields

        Returns:
            Self for method chaining
        """
        family = FieldFamilies.ENTITY_TZ if timezone_aware else FieldFamilies.ENTITY
        self._merge_family(family)
        return self

    def with_soft_delete(self, timezone_aware: bool = False) -> DomainModelBuilder:
        """Add soft delete fields (deleted_at, is_deleted).

        Args:
            timezone_aware: If True, uses timezone-aware datetime for deleted_at

        Returns:
            Self for method chaining
        """
        family = (
            FieldFamilies.SOFT_DELETE_TZ
            if timezone_aware
            else FieldFamilies.SOFT_DELETE
        )
        self._merge_family(family)

        return self

    def with_audit_fields(self) -> DomainModelBuilder:
        """Add audit/tracking fields (created_by, updated_by, version).

        Returns:
            Self for method chaining
        """
        self._merge_family(FieldFamilies.AUDIT)
        return self

    def with_family(self, family: dict[str, FieldTemplate]) -> DomainModelBuilder:
        """Add a custom field family.

        Args:
            family: Dictionary mapping field names to FieldTemplate instances

        Returns:
            Self for method chaining
        """
        self._merge_family(family)
        return self

    def add_field(
        self, name: str, template: FieldTemplate, replace: bool = True
    ) -> DomainModelBuilder:
        """Add or update a single field.

        Args:
            name: Field name
            template: FieldTemplate instance for the field
            replace: If True (default), replaces existing field with same name.
                    If False, raises ValueError if field already exists.

        Returns:
            Self for method chaining

        Raises:
            ValueError: If field exists and replace=False
        """
        if not replace and name in self._fields:
            raise ValueError(
                f"Field '{name}' already exists. Set replace=True to override."
            )

        self._fields[name] = template
        return self

    def remove_field(self, name: str) -> DomainModelBuilder:
        """Remove a field from the builder.

        Args:
            name: Field name to remove

        Returns:
            Self for method chaining

        Raises:
            KeyError: If field doesn't exist
        """
        if name not in self._fields:
            raise KeyError(f"Field '{name}' not found in builder")

        del self._fields[name]
        return self

    def remove_fields(self, *names: str) -> DomainModelBuilder:
        """Remove multiple fields from the builder.

        Args:
            *names: Field names to remove

        Returns:
            Self for method chaining
        """
        for name in names:
            if name in self._fields:
                del self._fields[name]
        return self

    def _merge_family(self, family: dict[str, FieldTemplate]) -> None:
        """Merge a field family into the current fields.

        Args:
            family: Field family to merge
        """
        self._fields.update(family)

    def build(self, **extra_config: Any) -> type[BaseModel]:
        """Build the Pydantic model with all configured fields.

        Args:
            **extra_config: Additional model configuration to merge with
                           the configuration provided in __init__

        Returns:
            A new Pydantic model class

        Raises:
            ValueError: If no fields have been added to the builder
        """
        if not self._fields:
            raise ValueError(
                f"Cannot build model '{self.model_name}' with no fields. "
                f"Add at least one field or field family before building."
            )

        # Create field dictionary - unpack the single dict as keyword arguments
        fields = create_field_dict(**self._fields)

        # Merge model configuration
        config = {**self.model_config, **extra_config}

        # Create and return the model
        return create_model(self.model_name, fields=fields, config=config)

    def preview(self) -> dict[str, str]:
        """Preview the fields that will be included in the model.

        Returns:
            Dictionary mapping field names to their descriptions
        """
        return {
            name: template.extract_metadata("description")
            or f"{template.base_type} field"
            for name, template in self._fields.items()
        }
