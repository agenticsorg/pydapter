# Protocols vs Fields Analysis

## Overview

Pydapter has two parallel systems that work together:
1. **Protocols**: Define structural contracts (what fields a model must have) and behavioral contracts (what methods are available)
2. **Fields**: Provide the actual field implementations to satisfy protocol requirements

## Current Architecture

### Protocols System (`/protocols/`)

Each protocol typically consists of:
- **Protocol Class**: Defines the structural contract (required fields)
- **Mixin Class**: Provides behavioral methods
- **Constants**: Protocol type identifiers

Example:
```python
# protocols/identifiable.py
@runtime_checkable
class Identifiable(Protocol):
    id: uuid.UUID  # Structural requirement

class IdentifiableMixin:
    def get_id(self) -> uuid.UUID:  # Behavioral method
        return self.id
```

### Fields System (`/fields/`)

Provides corresponding field families:
```python
# fields/protocol_families.py
class ProtocolFieldFamilies:
    IDENTIFIABLE = {
        "id": ID_TEMPLATE  # Field that satisfies Identifiable protocol
    }
```

## Key Findings

### 1. Clear Protocol-to-Fields Mapping

| Protocol | Field Family | Fields Provided |
|----------|--------------|-----------------|
| `Identifiable` | `IDENTIFIABLE` | id |
| `Temporal` | `TEMPORAL[_TZ]` | created_at, updated_at |
| `Embeddable` | `EMBEDDABLE` | embedding |
| `Invokable` | `INVOKABLE` | execution |
| `Cryptographical` | `CRYPTOGRAPHICAL` | sha256 |
| `Auditable` | `AUDITABLE` | created_by, updated_by, version |
| `SoftDeletable` | `SOFT_DELETABLE` | deleted_at, is_deleted |

### 2. Structure vs Behavior Separation

The design intentionally separates:
- **Structure**: What fields a model has (provided by field families)
- **Behavior**: What methods are available (provided by mixins)

This allows three usage patterns:

```python
# 1. Structure only (fields without behavior)
Model = create_protocol_model("Model", "identifiable", "temporal")

# 2. Structure + Behavior (fields with mixins)
Model = create_protocol_model_class("Model", IDENTIFIABLE, TEMPORAL)

# 3. Manual combination
class Model(BaseModel, IdentifiableMixin, TemporalMixin):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
```

### 3. Issues Identified

#### Missing Protocol Definitions
- `Auditable` and `SoftDeletable` have:
  - ✅ Mixin classes with behavior
  - ✅ Field families
  - ❌ Protocol class definitions
  - This breaks the established pattern

#### Duplicate Field Families
Two overlapping systems exist:
1. **Core patterns** (`families.py`):
   - `ENTITY` = id + created_at + updated_at
   - `SOFT_DELETE` = deleted_at + is_deleted
   - `AUDIT` = created_by + updated_by + version

2. **Protocol families** (`protocol_families.py`):
   - `IDENTIFIABLE` = id
   - `TEMPORAL` = created_at + updated_at
   - `SOFT_DELETABLE` = deleted_at + is_deleted
   - `AUDITABLE` = created_by + updated_by + version

This creates confusion:
- `ENTITY` ≈ `IDENTIFIABLE` + `TEMPORAL`
- `SOFT_DELETE` = `SOFT_DELETABLE`
- `AUDIT` = `AUDITABLE`

#### Implicit Protocol Requirements
- No explicit connection between protocols and their required fields
- Users must know which field family corresponds to which protocol
- No validation that a model satisfies a protocol's field requirements

## How It Should Work

### Current Flow
```
Protocol Definition → User manually selects field family → Model creation
     ↓                            ↓                           ↓
Identifiable            ProtocolFieldFamilies.IDENTIFIABLE   Model with id field
```

### Ideal Flow
```
Protocol Definition → Automatic field resolution → Model creation
     ↓                         ↓                        ↓
Identifiable            Protocol.get_fields()      Model with id field
                              ↓
                    Returns IDENTIFIABLE fields
```

## Recommendations

### 1. Complete Missing Protocols
Add proper protocol definitions for Auditable and SoftDeletable:
```python
@runtime_checkable
class Auditable(Protocol):
    created_by: uuid.UUID | None
    updated_by: uuid.UUID | None
    version: int

@runtime_checkable
class SoftDeletable(Protocol):
    deleted_at: datetime | None
    is_deleted: bool
```

### 2. Unify Field Families
Choose one approach:
- **Option A**: Keep only protocol-based families, deprecate core patterns
- **Option B**: Make core patterns compose protocol families explicitly:
  ```python
  ENTITY = {**IDENTIFIABLE, **TEMPORAL}
  ```

### 3. Explicit Protocol-Field Registry
Create a registry that maps protocols to their fields:
```python
PROTOCOL_FIELDS = {
    Identifiable: FieldFamilies.IDENTIFIABLE,
    Temporal: FieldFamilies.TEMPORAL,
    # ...
}
```

### 4. Better Factory Functions
Enhance protocol model creation:
```python
def create_protocol_model(name: str, *protocols: Protocol) -> type:
    # Automatically resolve fields from protocols
    fields = {}
    for protocol in protocols:
        fields.update(PROTOCOL_FIELDS[protocol])
    return create_model(name, fields=fields)
```

### 5. Documentation Improvements
- Clearly explain structure vs behavior separation
- Provide decision tree for when to use which approach
- Show complete examples of protocol compliance

## Summary

The current design is sophisticated but suffers from:
1. Incomplete protocol implementations (missing Protocol classes)
2. Duplicate field family systems causing confusion
3. Implicit protocol-to-fields mapping

The core concept of separating structure from behavior is sound, but the implementation needs refinement for clarity and consistency.