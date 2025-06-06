# Leveraging Pydantic Features Without Rebuilding the Wheel

## Core Principle

Our `Field` and `FieldTemplate` classes should wrap and enhance Pydantic's functionality, not replace it. Here are the Pydantic features we should leverage directly:

## 1. Pydantic Features We Should Use Directly

### Model Configuration (ConfigDict)
Instead of building our own configuration system, leverage Pydantic's:

```python
from pydantic import ConfigDict

# In our field families/protocols
PROTOCOL_CONFIGS = {
    "strict": ConfigDict(
        validate_assignment=True,
        validate_default=True,
        extra="forbid",
        str_strip_whitespace=True,
    ),
    "flexible": ConfigDict(
        validate_assignment=False,
        extra="allow",
    ),
    "immutable": ConfigDict(
        frozen=True,
        validate_assignment=False,
    )
}

# Let users choose configuration styles
def create_model_with_protocol(name: str, *protocols, config_style: str = "strict"):
    config = PROTOCOL_CONFIGS.get(config_style, ConfigDict())
    # ... create model with this config
```

### Field Validators and Serializers
Don't rebuild validation - use Pydantic's decorator-based system:

```python
from pydantic import field_validator, field_serializer

# In our FieldTemplate
class FieldTemplate:
    def create_field(self, name: str, **overrides):
        # ... existing logic ...
        
        # Add Pydantic validators if provided
        if "validators" in overrides:
            # These get applied to the model, not reimplemented
            pass
```

### Discriminated Unions for Protocol Types
Use for protocol type checking without custom logic:

```python
from typing import Literal, Union
from pydantic import Field as PydanticField, BaseModel

# For event types with different payloads
class CreateEvent(BaseModel):
    event_type: Literal["create"] = "create"
    resource_id: str
    resource_data: dict

class UpdateEvent(BaseModel):
    event_type: Literal["update"] = "update"
    resource_id: str
    changes: dict

class DeleteEvent(BaseModel):
    event_type: Literal["delete"] = "delete"
    resource_id: str

Event = Union[CreateEvent, UpdateEvent, DeleteEvent]
# Pydantic handles the discrimination automatically
```

### JSON Schema Generation
Leverage Pydantic's schema generation for our field metadata:

```python
# In FieldTemplate
class FieldTemplate:
    def __init__(self, base_type, **kwargs):
        # Store json_schema_extra for adapter-specific metadata
        self.json_schema_extra = kwargs.pop("json_schema_extra", {})
        
        # This gets passed through to Pydantic
        # We don't reimplement schema generation

# Usage for vector fields
EMBEDDING_TEMPLATE = FieldTemplate(
    base_type=list[float],
    json_schema_extra={
        "x-vector-dimensions": 1536,
        "x-vector-index": "hnsw",
        "x-adapter-hint": "pgvector"
    }
)
```

### Type Coercion and Strict Mode
Use Pydantic's type coercion instead of custom converters:

```python
# Don't do this:
def validate_uuid(value):
    if isinstance(value, str):
        return uuid.UUID(value)
    return value

# Do this:
from pydantic import BeforeValidator
from typing import Annotated

# Let Pydantic handle the coercion
UUID = Annotated[uuid.UUID, BeforeValidator(str)]
```

### Model Serialization Modes
Use Pydantic's serialization modes for different contexts:

```python
# For our models
class ProtocolBaseModel(BaseModel):
    def to_db(self):
        """Serialize for database storage."""
        return self.model_dump(mode="json", exclude_unset=True)
    
    def to_api(self):
        """Serialize for API response."""
        return self.model_dump(mode="python", exclude_defaults=True)
    
    def to_cache(self):
        """Serialize for caching."""
        return self.model_dump_json(exclude={"computed_fields"})
```

## 2. What We Should Build on Top

### Protocol-Field Registry
This is our value-add, not rebuilding Pydantic:

```python
# Our abstraction layer
class ProtocolFieldRegistry:
    """Maps protocols to their required fields - our innovation."""
    
    def __init__(self):
        self._registry = {}
    
    def register(self, protocol: type, fields: dict[str, FieldTemplate]):
        """Register fields for a protocol."""
        self._registry[protocol] = fields
    
    def get_fields_for_protocols(self, *protocols) -> dict:
        """Get combined fields for multiple protocols."""
        result = {}
        for protocol in protocols:
            if protocol in self._registry:
                result.update(self._registry[protocol])
        return result
```

### Field Template Composition
Our composition features that Pydantic doesn't provide:

```python
class FieldTemplate:
    """Our abstraction for reusable field definitions."""
    
    def as_nullable(self):
        """Make field nullable - our feature."""
        # Uses Union[T, None] under the hood
        
    def as_listable(self):
        """Make field accept lists - our feature."""
        # Uses Union[T, list[T]] under the hood
    
    def with_adapter_hint(self, adapter: str, **hints):
        """Add adapter-specific hints - our innovation."""
        json_extra = self.json_schema_extra.copy()
        json_extra[f"x-{adapter}"] = hints
        return self.copy(json_schema_extra=json_extra)
```

### Protocol Behavioral Mixins
Our behavioral additions that complement Pydantic models:

```python
class TemporalMixin:
    """Our behavior for temporal models."""
    
    def update_timestamp(self):
        """Update the timestamp - our method."""
        if hasattr(self, 'updated_at'):
            self.updated_at = datetime.utcnow()
    
    def age(self) -> timedelta:
        """Calculate age - our method."""
        if hasattr(self, 'created_at'):
            return datetime.utcnow() - self.created_at
```

## 3. Features to Avoid Rebuilding

### ❌ Don't Rebuild These:
- Validation logic (use Pydantic's validators)
- Serialization/deserialization (use model_dump/model_validate)
- Type coercion (use Pydantic's type system)
- JSON Schema generation (use Pydantic's schema)
- Field constraints (use Pydantic's Field constraints)

### ✅ Do Build These:
- Protocol-to-field mapping
- Field template composition (nullable, listable)
- Adapter-specific metadata
- Protocol behavioral mixins
- Unified model creation API

## 4. Practical Integration Example

```python
from pydantic import BaseModel, ConfigDict, field_validator
from typing import Annotated

# Our FieldTemplate wraps Pydantic features
class SmartFieldTemplate(FieldTemplate):
    def create_field(self, name: str, **overrides):
        # Get base field from parent
        field = super().create_field(name, **overrides)
        
        # Enhance with Pydantic features we want to leverage
        if self.json_schema_extra.get("x-indexed"):
            # Add to model's indexes (our feature)
            field.json_schema_extra["indexed"] = True
        
        if self.json_schema_extra.get("x-encrypted"):
            # Mark for encryption (our feature)
            field.json_schema_extra["encrypted"] = True
        
        return field

# Usage combining our abstractions with Pydantic
USERNAME_TEMPLATE = SmartFieldTemplate(
    base_type=str,
    description="Username",
    # Pydantic constraints
    min_length=3,
    max_length=20,
    pattern=r"^[a-zA-Z0-9_]+$",
    # Our extensions
    json_schema_extra={
        "x-indexed": True,
        "x-unique": True,
        "x-searchable": True
    }
)

# Model uses both Pydantic and our features
class User(create_protocol_model("User", Identifiable, Temporal)):
    username: str  # Will use our template
    
    # Pydantic validator - we don't rebuild this
    @field_validator('username')
    @classmethod
    def username_not_reserved(cls, v: str) -> str:
        if v in RESERVED_USERNAMES:
            raise ValueError(f"Username {v} is reserved")
        return v
    
    # Our protocol behavior
    def get_cache_key(self) -> str:
        """Our addition for caching."""
        return f"user:{self.id}"
```

## 5. Migration Path

### Current State
```python
# We're duplicating Pydantic functionality
class Field:
    def __init__(self, validator=None, ...):
        self.validator = validator  # Rebuilding validation
```

### Target State
```python
# Leverage Pydantic, add our value
class Field:
    def __init__(self, pydantic_field_kwargs=None, adapter_hints=None):
        self.pydantic_field_kwargs = pydantic_field_kwargs or {}
        self.adapter_hints = adapter_hints or {}  # Our addition
```

## Summary

Focus our efforts on:
1. **Protocol-field mapping** - Our core innovation
2. **Field composition patterns** - as_nullable(), as_listable()
3. **Adapter metadata** - Database/search hints
4. **Protocol behaviors** - Mixins with business logic
5. **Unified API** - Simplifying Pydantic for protocol use

Let Pydantic handle:
1. **Validation** - Their validators are battle-tested
2. **Serialization** - Their JSON/dict handling is optimized
3. **Type conversion** - Their type system is comprehensive
4. **Schema generation** - Their JSON Schema support is complete
5. **Configuration** - ConfigDict is well-designed

This approach gives us the best of both worlds: Pydantic's robust foundation with our protocol-oriented abstractions on top.