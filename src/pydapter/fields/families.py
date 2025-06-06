"""Field Families - Predefined collections of field templates for core database patterns.

This module provides pre-configured field families that group commonly used fields
together for database models. These families focus on core abstractions like
entity tracking, soft deletion, and audit trails.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydapter.fields.common_templates import (
    CREATED_AT_TEMPLATE,
    CREATED_AT_TZ_TEMPLATE,
    DELETED_AT_TEMPLATE,
    DELETED_AT_TZ_TEMPLATE,
    ID_TEMPLATE,
    UPDATED_AT_TEMPLATE,
    UPDATED_AT_TZ_TEMPLATE,
)
from pydapter.fields.template import FieldTemplate

if TYPE_CHECKING:
    from pydantic import Field


__all__ = (
    "FieldFamilies",
    "create_field_dict",
)


class FieldFamilies:
    """Collection of predefined field template groups for core database patterns.

    This class provides field families that represent common database patterns
    like entity tracking, soft deletion, and audit trails. These are foundational
    patterns that align with pydapter's core abstractions.
    """

    # Basic entity fields (id, created_at, updated_at)
    # Maps to Identifiable + Temporal protocols
    ENTITY: dict[str, FieldTemplate] = {
        "id": ID_TEMPLATE,
        "created_at": CREATED_AT_TEMPLATE,
        "updated_at": UPDATED_AT_TEMPLATE,
    }

    # Entity fields with timezone-aware timestamps
    ENTITY_TZ: dict[str, FieldTemplate] = {
        "id": ID_TEMPLATE,
        "created_at": CREATED_AT_TZ_TEMPLATE,
        "updated_at": UPDATED_AT_TZ_TEMPLATE,
    }

    # Soft delete support - common database pattern
    SOFT_DELETE: dict[str, FieldTemplate] = {
        "deleted_at": DELETED_AT_TEMPLATE,
        "is_deleted": None,  # Will be defined below
    }

    # Soft delete with timezone-aware timestamp
    SOFT_DELETE_TZ: dict[str, FieldTemplate] = {
        "deleted_at": DELETED_AT_TZ_TEMPLATE,
        "is_deleted": None,  # Will be defined below
    }

    # Audit/tracking fields - common pattern for tracking changes
    AUDIT: dict[str, FieldTemplate] = {
        "created_by": None,  # Will be defined below
        "updated_by": None,  # Will be defined below
        "version": None,  # Will be defined below
    }


# Define core field templates
_BOOLEAN_TEMPLATE = FieldTemplate(
    base_type=bool,
    description="Boolean flag",
    default=False,
)

_UUID_NULLABLE_TEMPLATE = ID_TEMPLATE.as_nullable()

_VERSION_TEMPLATE = FieldTemplate(
    base_type=int,
    description="Version number for optimistic locking",
    default=1,
)


# Update the field families with actual templates
FieldFamilies.SOFT_DELETE["is_deleted"] = _BOOLEAN_TEMPLATE
FieldFamilies.SOFT_DELETE_TZ["is_deleted"] = _BOOLEAN_TEMPLATE

FieldFamilies.AUDIT.update({
    "created_by": _UUID_NULLABLE_TEMPLATE,
    "updated_by": _UUID_NULLABLE_TEMPLATE,
    "version": _VERSION_TEMPLATE,
})


def create_field_dict(
    *families: dict[str, FieldTemplate], **overrides: FieldTemplate
) -> dict[str, Field]:
    """Create a field dictionary by merging multiple field families.

    This function takes multiple field families and merges them into a single
    dictionary of Pydantic fields. Later families override fields from earlier
    ones if there are naming conflicts.

    Args:
        *families: Variable number of field family dictionaries to merge
        **overrides: Individual field templates to add or override

    Returns:
        Dict[str, Field]: A dictionary mapping field names to Pydantic Field instances

    Example:
        ```python
        # Combine entity and audit fields
        fields = create_field_dict(
            FieldFamilies.ENTITY,
            FieldFamilies.AUDIT,
            name=FieldTemplate(base_type=str, description="Entity name")
        )

        # Create a model with the combined fields
        AuditedEntity = create_model("AuditedEntity", fields=fields)
        ```
    """

    result: dict[str, Field] = {}

    # Process field families in order
    for family in families:
        for field_name, template in family.items():
            if template is not None:
                result[field_name] = template.create_field(field_name)

    # Process individual overrides
    for field_name, template in overrides.items():
        if template is not None:
            result[field_name] = template.create_field(field_name)

    return result
