# Pydantic-Enhanced Protocol-Field Strategy (2025)

## Overview

Building on the protocol-field alignment strategy, this document incorporates Pydantic v2 best practices and prepares for v3 compatibility while leveraging Pydantic's powerful features for a more elegant architecture.

## Key Pydantic Features to Leverage

### 1. Discriminated Unions for Protocol Types

Use Pydantic's discriminated unions to handle different protocol implementations:

```python
from typing import Literal, Union
from pydantic import BaseModel, Field, RootModel, field_validator
from datetime import datetime
import uuid

# Base protocol models with discriminators
class IdentifiableModel(BaseModel):
    """Base for identifiable models."""
    protocol_type: Literal["identifiable"] = "identifiable"
    id: uuid.UUID = Field(default_factory=uuid.uuid4)

class TemporalModel(BaseModel):
    """Base for temporal models."""
    protocol_type: Literal["temporal"] = "temporal"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class AuditableModel(BaseModel):
    """Base for auditable models."""
    protocol_type: Literal["auditable"] = "auditable"
    created_by: uuid.UUID | None = None
    updated_by: uuid.UUID | None = None
    version: int = Field(default=1, ge=1)

# Discriminated union for protocol compliance checking
ProtocolModel = Union[
    IdentifiableModel,
    TemporalModel,
    AuditableModel,
]
```

### 2. RootModel for Field Collections

Use RootModel for type-safe field collections:

```python
from pydantic import RootModel
from typing import Dict

class FieldCollection(RootModel[Dict[str, FieldTemplate]]):
    """Type-safe collection of field templates."""
    
    def merge(self, other: "FieldCollection") -> "FieldCollection":
        """Merge two field collections."""
        return FieldCollection({**self.root, **other.root})
    
    def to_fields(self) -> Dict[str, Field]:
        """Convert templates to fields."""
        return {
            name: template.create_field(name) 
            for name, template in self.root.items()
        }

# Protocol field definitions using RootModel
class ProtocolFields:
    IDENTIFIABLE = FieldCollection({
        "id": ID_TEMPLATE
    })
    
    TEMPORAL = FieldCollection({
        "created_at": CREATED_AT_TEMPLATE,
        "updated_at": UPDATED_AT_TEMPLATE
    })
    
    ENTITY = IDENTIFIABLE.merge(TEMPORAL)
```

### 3. ConfigDict for Protocol-Aware Models

Use Pydantic's ConfigDict for protocol-specific behavior:

```python
from pydantic import ConfigDict, create_model as pydantic_create_model

def create_protocol_model(
    name: str,
    *protocols: type[Protocol],
    config: ConfigDict | None = None,
    **fields: Any
) -> type[BaseModel]:
    """Create a model with protocol compliance and Pydantic v2 features."""
    
    # Default protocol-aware config
    default_config = ConfigDict(
        # Enable validation on assignment for temporal updates
        validate_assignment=True,
        # Use enum values for better serialization
        use_enum_values=True,
        # Validate defaults to ensure protocol compliance
        validate_default=True,
        # Custom serialization for protocols
        json_encoders={
            datetime: lambda v: v.isoformat(),
            uuid.UUID: lambda v: str(v),
        },
        # Prepare for v3: use new validation modes
        revalidate_instances="always",
    )
    
    # Merge with user config
    if config:
        final_config = {**default_config, **config}
    else:
        final_config = default_config
    
    # Collect fields from protocols
    protocol_fields = {}
    for protocol in protocols:
        protocol_fields.update(get_protocol_fields(protocol))
    
    # Create model with config
    return pydantic_create_model(
        name,
        __config__=final_config,
        **{**protocol_fields, **fields}
    )
```

### 4. Computed Fields for Protocol Behavior

Replace mixin methods with computed fields where appropriate:

```python
from pydantic import computed_field

class TemporalBase(BaseModel):
    """Base model with temporal protocol behavior."""
    created_at: datetime
    updated_at: datetime
    
    @computed_field
    @property
    def age(self) -> timedelta:
        """Compute age of the record."""
        return datetime.utcnow() - self.created_at
    
    @computed_field
    @property
    def is_recent(self) -> bool:
        """Check if record was updated recently."""
        return (datetime.utcnow() - self.updated_at).days < 7
    
    def model_post_init(self, __context) -> None:
        """Auto-update timestamp on changes."""
        # This is called after validation
        if self.model_fields_set and 'updated_at' not in self.model_fields_set:
            self.updated_at = datetime.utcnow()
```

### 5. Generic Models for Type-Safe Protocols

Use generics for flexible, type-safe protocol implementations:

```python
from typing import Generic, TypeVar
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)
P = TypeVar('P', bound=Protocol)

class ProtocolCompliant(BaseModel, Generic[T, P]):
    """Generic base for protocol-compliant models."""
    
    @classmethod
    def from_base(cls, base: T, **extra) -> "ProtocolCompliant[T, P]":
        """Create protocol-compliant model from base model."""
        return cls(**base.model_dump(), **extra)
    
    def validate_protocol(self) -> bool:
        """Validate protocol compliance."""
        return isinstance(self, P)

# Usage
class UserData(BaseModel):
    username: str
    email: str

class IdentifiableUser(ProtocolCompliant[UserData, Identifiable]):
    id: uuid.UUID
    username: str
    email: str
```

### 6. Model Validators for Protocol Constraints

Use Pydantic v2 validators for protocol-specific constraints:

```python
from pydantic import field_validator, model_validator

class AuditableBase(BaseModel):
    created_by: uuid.UUID | None = None
    updated_by: uuid.UUID | None = None
    version: int = 1
    
    @field_validator('version')
    @classmethod
    def version_must_be_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError('Version must be >= 1')
        return v
    
    @model_validator(mode='after')
    def check_audit_consistency(self) -> 'AuditableBase':
        """Ensure audit fields are consistent."""
        if self.updated_by and not self.created_by:
            raise ValueError('Cannot have updated_by without created_by')
        return self
```

### 7. Serialization Context for Protocol Metadata

Use serialization context for protocol-aware serialization:

```python
class ProtocolAwareModel(BaseModel):
    """Base model with protocol-aware serialization."""
    
    def model_dump(
        self,
        *,
        include_protocol_meta: bool = False,
        **kwargs
    ) -> dict[str, Any]:
        """Dump model with optional protocol metadata."""
        data = super().model_dump(**kwargs)
        
        if include_protocol_meta:
            data['_protocols'] = [
                p.__name__ for p in self.__class__.__bases__
                if isinstance(p, type) and issubclass(p, Protocol)
            ]
            data['_version'] = '2.0'  # Protocol version
        
        return data
    
    @classmethod
    def model_validate(cls, obj: Any, *, strict: bool = None) -> 'ProtocolAwareModel':
        """Validate with protocol checking."""
        instance = super().model_validate(obj, strict=strict)
        
        # Validate protocol compliance
        for protocol in cls.__annotations__.get('__protocols__', []):
            if not isinstance(instance, protocol):
                raise ValueError(f"Model does not comply with {protocol.__name__}")
        
        return instance
```

## Future-Ready Architecture

### 1. Prepare for Pydantic v3

```python
# Use new-style type annotations
from typing import Annotated
from pydantic import Field, BeforeValidator, AfterValidator

# Future-ready field definitions
IdField = Annotated[
    uuid.UUID,
    Field(default_factory=uuid.uuid4),
    BeforeValidator(lambda x: uuid.UUID(x) if isinstance(x, str) else x),
]

TimestampField = Annotated[
    datetime,
    Field(default_factory=datetime.utcnow),
    AfterValidator(lambda x: x.replace(microsecond=0)),  # Round to seconds
]

# Use in models
class FutureReadyModel(BaseModel):
    id: IdField
    created_at: TimestampField
    updated_at: TimestampField
```

### 2. Protocol Registry with Pydantic

```python
from pydantic import BaseModel, Field
from typing import Dict, Type, Set

class ProtocolRegistry(BaseModel):
    """Type-safe protocol registry using Pydantic."""
    
    protocols: Dict[str, Type[Protocol]] = Field(default_factory=dict)
    fields: Dict[str, FieldCollection] = Field(default_factory=dict)
    mixins: Dict[str, Type] = Field(default_factory=dict)
    
    def register(
        self,
        protocol: Type[Protocol],
        fields: FieldCollection,
        mixin: Type | None = None
    ) -> None:
        """Register a protocol with its fields and mixin."""
        name = protocol.__name__
        self.protocols[name] = protocol
        self.fields[name] = fields
        if mixin:
            self.mixins[name] = mixin
    
    def get_combined_fields(self, *protocol_names: str) -> FieldCollection:
        """Get combined fields for multiple protocols."""
        result = FieldCollection({})
        for name in protocol_names:
            if name in self.fields:
                result = result.merge(self.fields[name])
        return result

# Global registry instance
protocol_registry = ProtocolRegistry()
```

### 3. Enhanced Builder with Pydantic

```python
class DomainModelBuilder(BaseModel):
    """Pydantic-based model builder."""
    
    name: str
    protocols: Set[Type[Protocol]] = Field(default_factory=set)
    fields: Dict[str, FieldTemplate] = Field(default_factory=dict)
    config: ConfigDict = Field(default_factory=lambda: ConfigDict())
    
    def with_protocol(self, protocol: Type[Protocol]) -> "DomainModelBuilder":
        """Add a protocol fluently."""
        self.protocols.add(protocol)
        return self
    
    def with_field(self, name: str, template: FieldTemplate) -> "DomainModelBuilder":
        """Add a field fluently."""
        self.fields[name] = template
        return self
    
    def build(self) -> Type[BaseModel]:
        """Build the final model."""
        # Collect protocol fields
        protocol_fields = {}
        mixins = []
        
        for protocol in self.protocols:
            fields = protocol_registry.fields.get(protocol.__name__, {})
            protocol_fields.update(fields.root)
            
            mixin = protocol_registry.mixins.get(protocol.__name__)
            if mixin:
                mixins.append(mixin)
        
        # Merge all fields
        all_fields = {**protocol_fields, **self.fields}
        
        # Create model with mixins
        bases = (BaseModel, *mixins) if mixins else (BaseModel,)
        
        return type(
            self.name,
            bases,
            {
                "__annotations__": {
                    name: field.annotation 
                    for name, field in all_fields.items()
                },
                "model_config": self.config,
                **all_fields
            }
        )
```

## Benefits of Pydantic Integration

1. **Type Safety**: Full type checking with Pydantic's validation
2. **Performance**: Leverage Pydantic v2's Rust-based core
3. **Serialization**: Built-in JSON/dict conversion with protocol awareness
4. **Validation**: Automatic validation of protocol constraints
5. **Future Ready**: Prepared for Pydantic v3 changes
6. **Developer Experience**: Better IDE support and error messages

## Migration Example

```python
# Old approach
class User(BaseModel, IdentifiableMixin, TemporalMixin):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    username: str

# New Pydantic-enhanced approach
User = DomainModelBuilder("User")\
    .with_protocol(Identifiable)\
    .with_protocol(Temporal)\
    .with_field("username", USERNAME_TEMPLATE)\
    .build()

# Or using the simplified API
User = create_protocol_model(
    "User",
    Identifiable,
    Temporal,
    username=USERNAME_TEMPLATE,
    config=ConfigDict(
        json_schema_extra={"example": {
            "username": "john_doe",
            "id": "123e4567-e89b-12d3-a456-426614174000"
        }}
    )
)
```

This enhanced strategy leverages Pydantic's powerful features while maintaining the clean protocol-based architecture, preparing for future Pydantic versions, and providing a superior developer experience.