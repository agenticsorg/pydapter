"""Trait Field Families - Field templates for trait integration.

This module provides field families that correspond to pydapter traits,
enabling easy creation of models that implement specific trait interfaces.

This replaces the deprecated protocol_families module.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pydapter.traits import Trait

from pydapter.fields.common_templates import (
    CREATED_AT_TEMPLATE,
    CREATED_AT_TZ_TEMPLATE,
    DELETED_AT_TZ_TEMPLATE,
    ID_TEMPLATE,
    JSON_TEMPLATE,
    UPDATED_AT_TEMPLATE,
    UPDATED_AT_TZ_TEMPLATE,
)
from pydapter.fields.execution import Execution
from pydapter.fields.template import FieldTemplate

__all__ = (
    "TraitFieldFamilies",
    "create_trait_model",
)


class TraitFieldFamilies:
    """Field families for pydapter trait compliance.

    This class provides field template collections that match the requirements
    of various pydapter traits. Using these families ensures your models
    will be compatible with trait protocols and functionality.
    """

    # Identifiable trait fields
    IDENTIFIABLE: dict[str, FieldTemplate] = {
        "id": ID_TEMPLATE,
    }

    # Temporal trait fields (naive datetime)
    TEMPORAL: dict[str, FieldTemplate] = {
        "created_at": CREATED_AT_TEMPLATE,
        "updated_at": UPDATED_AT_TEMPLATE,
    }

    # Temporal trait fields (timezone-aware)
    TEMPORAL_TZ: dict[str, FieldTemplate] = {
        "created_at": CREATED_AT_TZ_TEMPLATE,
        "updated_at": UPDATED_AT_TZ_TEMPLATE,
    }

    # Serializable trait fields (for embeddings/vectors)
    SERIALIZABLE_EMBEDDING: dict[str, FieldTemplate] = {
        "embedding": FieldTemplate(
            base_type=list[float],
            description="Vector embedding",
            default=list,
            json_schema_extra={"vector_dim": 1536},
        ),
    }

    # Operable trait fields (for invokable operations)
    OPERABLE: dict[str, FieldTemplate] = {
        "execution": None,  # Will be defined below
    }

    # Secured trait fields (for cryptographical operations)
    SECURED: dict[str, FieldTemplate] = {
        "sha256": FieldTemplate(
            base_type=str,
            description="SHA256 hash of the content",
            nullable=True,
        ),
    }

    # Auditable trait fields
    AUDITABLE: dict[str, FieldTemplate] = {
        "created_by": FieldTemplate(
            base_type=ID_TEMPLATE.base_type,
            nullable=True,
            description="ID of the creator",
        ),
        "updated_by": FieldTemplate(
            base_type=ID_TEMPLATE.base_type,
            nullable=True,
            description="ID of the last updater",
        ),
        "version": FieldTemplate(
            base_type=int,
            description="Version number for optimistic locking",
            default=1,
        ),
    }

    # Temporal with soft delete (extends Temporal)
    SOFT_DELETABLE: dict[str, FieldTemplate] = {
        "deleted_at": DELETED_AT_TZ_TEMPLATE,
        "is_deleted": FieldTemplate(
            base_type=bool,
            description="Soft delete flag",
            default=False,
        ),
    }

    # Observable trait fields (for event-like models)
    OBSERVABLE_BASE: dict[str, FieldTemplate] = {
        "id": ID_TEMPLATE,  # Events have frozen IDs
        "created_at": CREATED_AT_TZ_TEMPLATE,
        "updated_at": UPDATED_AT_TZ_TEMPLATE,
        "event_type": FieldTemplate(
            base_type=str,
            description="Type of the event",
            nullable=True,
        ),
        "content": FieldTemplate(
            base_type=dict,  # Use dict as base type, nullable will handle None
            description="Content of the event",
            nullable=True,
            default=None,
        ),
        "request": FieldTemplate(
            base_type=JSON_TEMPLATE.base_type,
            description="Request parameters",
            default=dict,
        ),
    }

    # Complete Event fields (combines multiple traits)
    EVENT_COMPLETE: dict[str, FieldTemplate] = {
        **OBSERVABLE_BASE,
        **SERIALIZABLE_EMBEDDING,
        **SECURED,
        "execution": None,  # Will be defined below
    }


# Define the execution template
_EXECUTION_TEMPLATE = FieldTemplate(
    base_type=Execution,
    description="Execution details",
    default=Execution,
)

# Update the OPERABLE family
TraitFieldFamilies.OPERABLE["execution"] = _EXECUTION_TEMPLATE
TraitFieldFamilies.EVENT_COMPLETE["execution"] = _EXECUTION_TEMPLATE


def create_trait_model(
    name: str,
    *traits: str | Trait,
    timezone_aware: bool = True,
    base_fields: dict[str, FieldTemplate] | None = None,
    **extra_fields: FieldTemplate,
) -> type:
    """Create a model with fields required by specified traits (structural compliance).

    This function creates a Pydantic model with fields required by the specified
    traits. It provides STRUCTURAL compliance by including the necessary fields.

    Note: This function only adds the fields required by traits. To get the full
    trait behavior, use the traits.composer.generate_model function instead.

    Args:
        name: Name for the generated model class
        *traits: Trait names to implement. Supported values:
            - "identifiable" or Trait.IDENTIFIABLE: Adds id field
            - "temporal" or Trait.TEMPORAL: Adds created_at and updated_at fields
            - "serializable": Adds serialization support fields
            - "operable" or Trait.OPERABLE: Adds execution field
            - "secured" or Trait.SECURED: Adds sha256 field
            - "auditable" or Trait.AUDITABLE: Adds audit fields
            - "observable" or Trait.OBSERVABLE: Adds event fields
        timezone_aware: If True, uses timezone-aware datetime fields (default: True)
        base_fields: Optional base field family to start with
        **extra_fields: Additional field templates to include

    Returns:
        A new Pydantic model class with trait-compliant fields (structure only)

    Examples:
        ```python
        from pydapter.traits import Trait
        from pydapter.fields.trait_families import create_trait_model

        # Create a model with ID and timestamps
        TrackedEntity = create_trait_model(
            "TrackedEntity",
            Trait.IDENTIFIABLE,
            Trait.TEMPORAL,
        )

        # Create a serializable document
        Document = create_trait_model(
            "Document",
            "identifiable",
            "temporal",
            "serializable",
            title=FieldTemplate(base_type=str),
            content=FieldTemplate(base_type=str),
        )

        # For full trait behavior, use the trait composer:
        from pydapter.traits.composer import generate_model

        FullDocument = generate_model(
            "FullDocument",
            traits=[Trait.IDENTIFIABLE, Trait.TEMPORAL, Trait.SERIALIZABLE],
            fields={
                "title": FieldTemplate(base_type=str),
                "content": FieldTemplate(base_type=str),
            }
        )
        ```
    """
    from pydapter.fields.families import create_field_dict
    from pydapter.fields.types import create_model

    # Handle Trait enum
    try:
        from pydapter.traits import Trait as TraitEnum
    except ImportError:
        TraitEnum = None

    # Start with base fields if provided
    field_families = []
    if base_fields:
        field_families.append(base_fields)

    # Add trait fields
    for trait in traits:
        # Handle Trait enum values
        if TraitEnum and isinstance(trait, TraitEnum):
            trait_name = trait.value
        else:
            trait_name = str(trait).lower()

        if trait_name == "identifiable":
            field_families.append(TraitFieldFamilies.IDENTIFIABLE)
        elif trait_name == "temporal":
            if timezone_aware:
                field_families.append(TraitFieldFamilies.TEMPORAL_TZ)
            else:
                field_families.append(TraitFieldFamilies.TEMPORAL)
        elif trait_name == "serializable":
            # Don't add embedding fields by default for serializable
            pass
        elif trait_name == "operable":
            field_families.append(TraitFieldFamilies.OPERABLE)
        elif trait_name == "secured":
            field_families.append(TraitFieldFamilies.SECURED)
        elif trait_name == "auditable":
            field_families.append(TraitFieldFamilies.AUDITABLE)
        elif trait_name == "observable":
            field_families.append(TraitFieldFamilies.OBSERVABLE_BASE)
        else:
            # For unknown traits, just continue (they might not need fields)
            pass

    # Create field dictionary
    fields = create_field_dict(*field_families, **extra_fields)

    # Create and return the model
    return create_model(name, fields=fields)
