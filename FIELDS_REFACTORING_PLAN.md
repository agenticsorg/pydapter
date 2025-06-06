# Fields Module Refactoring Plan

## Overview

The `src/pydapter/fields/` module has evolved organically and now contains redundancies and unclear separations of concerns. This document outlines the issues and proposed refactoring strategy.

## Current Issues

### 1. Duplicate Field Families
- `families.py` provides ENTITY, SOFT_DELETE, AUDIT patterns
- `protocol_families.py` provides IDENTIFIABLE, TEMPORAL, etc.
- ENTITY is essentially IDENTIFIABLE + TEMPORAL
- Both modules serve similar purposes with overlapping functionality

### 2. Field vs FieldTemplate Confusion
- `Field` (in types.py) - A concrete field descriptor with a fixed name
- `FieldTemplate` (in template.py) - A reusable template for creating Fields
- Both can define the same properties, unclear when to use which
- Most of the codebase uses FieldTemplate, but Field still exists

### 3. Scattered Type Definitions
- Core types (ID, Embedding, Metadata) in `types.py`
- `Execution` class in `execution.py`
- `Embedding` validation in `embedding.py`
- No clear organization principle for where types belong

### 4. Unclear Protocol-Field Relationship
- Protocols defined in `/protocols/` directory
- Field requirements for protocols in `/fields/protocol_families.py`
- No explicit connection between a protocol and its required fields
- Users must manually combine field families with protocol mixins

## Proposed Solution

### 1. Unified Field Families (`families_unified.py`)
Merge `families.py` and `protocol_families.py` into a single module with clear sections:

```python
class FieldFamilies:
    # Core Patterns (database patterns)
    ENTITY         # id + created_at + updated_at
    ENTITY_TZ      # with timezone
    SOFT_DELETE    # deleted_at + is_deleted
    AUDIT          # created_by + updated_by + version
    
    # Protocol Fields (minimal protocol requirements)
    IDENTIFIABLE   # just id
    TEMPORAL       # just created_at + updated_at
    EMBEDDABLE     # just embedding
    INVOKABLE      # just execution
    CRYPTOGRAPHICAL # just sha256
    AUDITABLE      # same as AUDIT
    SOFT_DELETABLE # same as SOFT_DELETE_TZ
    
    # Composite Patterns
    EVENT_BASE     # frozen id + timestamps + content
    EVENT_COMPLETE # all event protocols combined
```

### 2. Centralized Types Module
Move all custom field types to `types.py`:

```python
# types.py
ID = uuid.UUID
Embedding = list[float]
Metadata = dict
Execution = <move class here>

# Also consolidate validation functions
validate_embedding()
validate_execution()
```

### 3. Clear Field vs FieldTemplate Guidelines

**FieldTemplate** (Primary API):
- Use for all reusable field patterns
- Supports `.as_nullable()`, `.as_listable()` composition
- Can create multiple Fields with different names
- All common templates should use this

**Field** (Internal/Legacy):
- Use only for one-off, non-reusable fields
- When you know the exact field name upfront
- Consider making this more internal/private

### 4. Explicit Protocol Mapping

Create a clear mapping in the protocols module:

```python
# protocols/registry.py
PROTOCOL_FIELDS = {
    Identifiable: FieldFamilies.IDENTIFIABLE,
    Temporal: FieldFamilies.TEMPORAL,
    Embeddable: FieldFamilies.EMBEDDABLE,
    # etc...
}
```

## Migration Strategy

### Phase 1: Create New Structure (Backward Compatible)
1. Create `families_unified.py` with all families
2. Update `types.py` to include all type definitions
3. Create template versions of all Field-only definitions
4. Keep old modules but mark as deprecated

### Phase 2: Update Internal Usage
1. Update all internal code to use unified families
2. Switch from Field to FieldTemplate where appropriate
3. Update tests to use new structure

### Phase 3: Deprecate Old Modules
1. Add deprecation warnings to old modules
2. Update documentation
3. Plan removal in next major version

## File Structure After Refactoring

```
src/pydapter/fields/
├── __init__.py          # Re-export from new modules
├── builder.py           # DomainModelBuilder (unchanged)
├── common_templates.py  # Common FieldTemplates (unchanged)
├── families_unified.py  # NEW: All field families
├── template.py          # FieldTemplate class (unchanged)
├── types.py            # All types + Field class + validators
├── validation_patterns.py # Regex patterns (unchanged)
│
├── _deprecated/        # Move deprecated modules here
│   ├── families.py     # Mark deprecated
│   ├── protocol_families.py # Mark deprecated
│   ├── embedding.py    # Move content to types.py
│   ├── execution.py    # Move content to types.py
│   ├── dts.py         # Already redundant
│   ├── ids.py         # Already redundant
│   └── params.py      # Move validators to types.py
```

## Benefits

1. **Single Source of Truth**: One place for all field families
2. **Clear Organization**: Obvious where to find/add things
3. **Reduced Redundancy**: No more duplicate definitions
4. **Better Discoverability**: Users can see all options in one place
5. **Explicit Relationships**: Clear protocol-to-fields mapping

## Example Usage After Refactoring

```python
from pydapter.fields import FieldFamilies, create_model

# Simple entity with audit trail
User = create_model(
    "User",
    fields={
        **FieldFamilies.ENTITY_TZ,    # id + timestamps with timezone
        **FieldFamilies.AUDIT,         # created_by + updated_by + version
        "email": EMAIL_TEMPLATE,
        "name": NAME_TEMPLATE,
    }
)

# Protocol-based model
from pydapter.protocols import IdentifiableMixin, TemporalMixin

class TrackedDocument(
    create_protocol_model("Base", "identifiable", "temporal", "embeddable"),
    IdentifiableMixin,
    TemporalMixin
):
    content: str
    
# The model now has both fields AND behavior
```

## Next Steps

1. Review and approve this plan
2. Implement Phase 1 (backward compatible changes)
3. Update tests to verify compatibility
4. Proceed with Phase 2 and 3 based on feedback