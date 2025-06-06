"""Unified Field Families - Consolidated field templates for all patterns.

This module merges the functionality of families.py and protocol_families.py,
providing a single source for field families that support both core database
patterns and protocol compliance.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydapter.fields.common_templates import (
    CREATED_AT_TEMPLATE,
    CREATED_AT_TZ_TEMPLATE,
    DELETED_AT_TEMPLATE,
    DELETED_AT_TZ_TEMPLATE,
    ID_TEMPLATE,
    JSON_TEMPLATE,
    UPDATED_AT_TEMPLATE,
    UPDATED_AT_TZ_TEMPLATE,
)
from pydapter.fields.embedding import EMBEDDING_TEMPLATE
from pydapter.fields.execution import EXECUTION_TEMPLATE
from pydapter.fields.template import FieldTemplate

if TYPE_CHECKING:
    from pydantic import Field as PydanticField
    from pydapter.protocols import ProtocolType

__all__ = (
    "FieldFamilies",
    "create_field_dict",
    "create_protocol_model",
)


# Core field templates used across families
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

_SHA256_TEMPLATE = FieldTemplate(
    base_type=str,
    description="SHA256 hash of the content",
).as_nullable()


class FieldFamilies:
    """Unified collection of field template groups for all patterns.
    
    This class provides field families for both core database patterns and
    protocol compliance. It consolidates the previously separate families.py
    and protocol_families.py into a single, coherent API.
    
    Field families are organized into three categories:
    1. Core Patterns: Common database patterns (entity, soft delete, audit)
    2. Protocol Fields: Fields required by specific protocols
    3. Composite Patterns: Combinations of multiple patterns
    """
    
    # ==================== CORE PATTERNS ====================
    # These represent fundamental database patterns
    
    # Basic entity fields (id + timestamps)
    # Equivalent to IDENTIFIABLE + TEMPORAL protocols
    ENTITY: dict[str, FieldTemplate] = {
        "id": ID_TEMPLATE,
        "created_at": CREATED_AT_TEMPLATE,
        "updated_at": UPDATED_AT_TEMPLATE,
    }
    
    # Entity with timezone-aware timestamps
    ENTITY_TZ: dict[str, FieldTemplate] = {
        "id": ID_TEMPLATE,
        "created_at": CREATED_AT_TZ_TEMPLATE,
        "updated_at": UPDATED_AT_TZ_TEMPLATE,
    }
    
    # Soft delete pattern
    SOFT_DELETE: dict[str, FieldTemplate] = {
        "deleted_at": DELETED_AT_TEMPLATE,
        "is_deleted": _BOOLEAN_TEMPLATE,
    }
    
    # Soft delete with timezone
    SOFT_DELETE_TZ: dict[str, FieldTemplate] = {
        "deleted_at": DELETED_AT_TZ_TEMPLATE,
        "is_deleted": _BOOLEAN_TEMPLATE,
    }
    
    # Audit/tracking fields
    AUDIT: dict[str, FieldTemplate] = {
        "created_by": _UUID_NULLABLE_TEMPLATE,
        "updated_by": _UUID_NULLABLE_TEMPLATE,
        "version": _VERSION_TEMPLATE,
    }
    
    # ==================== PROTOCOL FIELDS ====================
    # These map directly to pydapter protocol requirements
    
    # Identifiable protocol - just ID field
    IDENTIFIABLE: dict[str, FieldTemplate] = {
        "id": ID_TEMPLATE,
    }
    
    # Temporal protocol - timestamps only (no ID)
    TEMPORAL: dict[str, FieldTemplate] = {
        "created_at": CREATED_AT_TEMPLATE,
        "updated_at": UPDATED_AT_TEMPLATE,
    }
    
    # Temporal with timezone
    TEMPORAL_TZ: dict[str, FieldTemplate] = {
        "created_at": CREATED_AT_TZ_TEMPLATE,
        "updated_at": UPDATED_AT_TZ_TEMPLATE,
    }
    
    # Embeddable protocol - vector embeddings
    EMBEDDABLE: dict[str, FieldTemplate] = {
        "embedding": EMBEDDING_TEMPLATE,
    }
    
    # Invokable protocol - execution tracking
    INVOKABLE: dict[str, FieldTemplate] = {
        "execution": EXECUTION_TEMPLATE,
    }
    
    # Cryptographical protocol - content hashing
    CRYPTOGRAPHICAL: dict[str, FieldTemplate] = {
        "sha256": _SHA256_TEMPLATE,
    }
    
    # Auditable protocol - same as AUDIT for consistency
    AUDITABLE: dict[str, FieldTemplate] = AUDIT
    
    # SoftDeletable protocol - same as SOFT_DELETE_TZ for consistency
    SOFT_DELETABLE: dict[str, FieldTemplate] = SOFT_DELETE_TZ
    
    # ==================== COMPOSITE PATTERNS ====================
    # These combine multiple patterns for specific use cases
    
    # Event base fields (frozen ID + timestamps + content)
    EVENT_BASE: dict[str, FieldTemplate] = {
        "id": ID_TEMPLATE.copy(frozen=True),
        "created_at": CREATED_AT_TZ_TEMPLATE,
        "updated_at": UPDATED_AT_TZ_TEMPLATE,
        "event_type": FieldTemplate(
            base_type=str,
            description="Type of the event",
        ).as_nullable(),
        "content": FieldTemplate(
            base_type=str | dict | None,
            description="Content of the event",
            default=None,
        ),
        "request": JSON_TEMPLATE.copy(description="Request parameters"),
    }
    
    # Complete Event fields (all event-related protocols)
    EVENT_COMPLETE: dict[str, FieldTemplate] = {
        **EVENT_BASE,
        **EMBEDDABLE,
        **INVOKABLE,
        **CRYPTOGRAPHICAL,
    }
    
    # ==================== ALIASES FOR COMPATIBILITY ====================
    # These provide backward compatibility and intuitive naming
    
    @classmethod
    def get_protocol_fields(cls, protocol: str, timezone_aware: bool = True) -> dict[str, FieldTemplate]:
        """Get fields for a specific protocol.
        
        Args:
            protocol: Protocol name (case-insensitive)
            timezone_aware: Whether to use timezone-aware timestamps
            
        Returns:
            Dictionary of field templates for the protocol
            
        Raises:
            ValueError: If protocol is not recognized
        """
        protocol_lower = protocol.lower()
        
        if protocol_lower == "identifiable":
            return cls.IDENTIFIABLE
        elif protocol_lower == "temporal":
            return cls.TEMPORAL_TZ if timezone_aware else cls.TEMPORAL
        elif protocol_lower == "embeddable":
            return cls.EMBEDDABLE
        elif protocol_lower == "invokable":
            return cls.INVOKABLE
        elif protocol_lower == "cryptographical":
            return cls.CRYPTOGRAPHICAL
        elif protocol_lower == "auditable":
            return cls.AUDITABLE
        elif protocol_lower in ["soft_deletable", "softdeletable"]:
            return cls.SOFT_DELETABLE
        else:
            raise ValueError(
                f"Unknown protocol: {protocol}. Supported protocols are: "
                f"identifiable, temporal, embeddable, invokable, cryptographical, "
                f"auditable, soft_deletable"
            )


def create_field_dict(
    *families: dict[str, FieldTemplate], **overrides: FieldTemplate
) -> dict[str, PydanticField]:
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
    result: dict[str, PydanticField] = {}
    
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


def create_protocol_model(
    name: str,
    *protocols: str | ProtocolType,
    timezone_aware: bool = True,
    base_fields: dict[str, FieldTemplate] | None = None,
    **extra_fields: FieldTemplate,
) -> type:
    """Create a model with fields required by specified protocols.
    
    This function creates a Pydantic model with fields required by the specified
    protocols. It provides STRUCTURAL compliance by including the necessary fields,
    but does NOT add behavioral methods from protocol mixins.
    
    Note: This function only adds the fields required by protocols. To get
    behavioral methods (e.g., update_timestamp() from TemporalMixin), you must
    explicitly inherit from the corresponding mixin classes.
    
    Args:
        name: Name for the generated model class
        *protocols: Protocol names or types to implement
        timezone_aware: If True, uses timezone-aware datetime fields (default: True)
        base_fields: Optional base field family to start with
        **extra_fields: Additional field templates to include
        
    Returns:
        A new Pydantic model class with protocol-compliant fields
        
    Examples:
        ```python
        # Create a model with ID and timestamps
        TrackedEntity = create_protocol_model(
            "TrackedEntity",
            "identifiable",
            "temporal",
        )
        
        # Use the ENTITY shorthand (combines identifiable + temporal)
        TrackedEntity2 = create_model(
            "TrackedEntity2",
            fields=FieldFamilies.ENTITY
        )
        
        # Add behavioral methods with mixins
        from pydapter.protocols import IdentifiableMixin, TemporalMixin
        
        _UserBase = create_protocol_model(
            "UserBase",
            "identifiable",
            "temporal",
            username=FieldTemplate(base_type=str)
        )
        
        class User(_UserBase, IdentifiableMixin, TemporalMixin):
            pass
        ```
    """
    from pydapter.fields.types import create_model
    
    # Start with base fields if provided
    field_families = []
    if base_fields:
        field_families.append(base_fields)
    
    # Add protocol fields
    for protocol in protocols:
        field_families.append(
            FieldFamilies.get_protocol_fields(str(protocol), timezone_aware)
        )
    
    # Create field dictionary
    fields = create_field_dict(*field_families, **extra_fields)
    
    # Create and return the model
    return create_model(name, fields=fields)