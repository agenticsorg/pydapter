# Protocol-Field Alignment Strategy

## Goals
1. **Reduce ambiguity** in how protocols and fields relate
2. **Simplify usage** with clear, intuitive APIs
3. **Maintain flexibility** for advanced use cases
4. **Ensure backward compatibility** during transition

## Core Principle: Protocols as First-Class Citizens

Instead of having parallel protocol and field systems, make protocols the primary interface that automatically provides the correct fields.

## Proposed Architecture

### 1. Protocol-Driven Field Resolution

Each protocol should know its own field requirements:

```python
# protocols/base.py
class ProtocolMeta(type):
    """Metaclass that automatically registers protocol field requirements."""
    
    def __new__(cls, name, bases, attrs):
        new_class = super().__new__(cls, name, bases, attrs)
        if hasattr(new_class, '__fields__'):
            PROTOCOL_FIELD_REGISTRY[new_class] = new_class.__fields__
        return new_class

# protocols/identifiable.py
@runtime_checkable
class Identifiable(Protocol, metaclass=ProtocolMeta):
    """Protocol for entities with unique identifiers."""
    id: uuid.UUID
    
    __fields__ = {
        "id": ID_TEMPLATE
    }

class IdentifiableMixin:
    """Behavioral mixin for identifiable entities."""
    
    def get_id(self) -> uuid.UUID:
        return self.id
    
    def __eq__(self, other):
        if isinstance(other, Identifiable):
            return self.id == other.id
        return False
```

### 2. Unified Model Creation API

Replace multiple creation functions with a single, clear API:

```python
# fields/builder.py or protocols/factory.py
def create_model(
    name: str,
    *protocols: type[Protocol] | str,
    fields: dict[str, FieldTemplate] | None = None,
    include_mixins: bool = True,
    **field_overrides: FieldTemplate
) -> type[BaseModel]:
    """
    Create a model with protocol compliance.
    
    Args:
        name: Model class name
        *protocols: Protocol classes or names to implement
        fields: Additional fields beyond protocol requirements
        include_mixins: Whether to include behavioral mixins (default: True)
        **field_overrides: Override specific protocol fields
        
    Returns:
        Model class with protocol fields and optionally mixins
    """
    # Resolve all protocol fields
    protocol_fields = {}
    mixins = []
    
    for protocol in protocols:
        if isinstance(protocol, str):
            protocol = PROTOCOL_REGISTRY[protocol]
        
        # Get fields from protocol
        protocol_fields.update(PROTOCOL_FIELD_REGISTRY[protocol])
        
        # Get mixin if requested
        if include_mixins:
            mixin = PROTOCOL_MIXIN_REGISTRY.get(protocol)
            if mixin:
                mixins.append(mixin)
    
    # Merge fields
    all_fields = {
        **protocol_fields,
        **(fields or {}),
        **field_overrides
    }
    
    # Create model
    if include_mixins:
        return create_model_with_mixins(name, all_fields, mixins)
    else:
        return create_basic_model(name, all_fields)
```

### 3. Protocol Bundles for Common Patterns

Define common protocol combinations as reusable bundles:

```python
# protocols/bundles.py
class ProtocolBundles:
    """Common protocol combinations."""
    
    # Basic entity (replaces ENTITY field family)
    ENTITY = (Identifiable, Temporal)
    
    # Audited entity
    AUDITED_ENTITY = (Identifiable, Temporal, Auditable)
    
    # Soft-deletable entity
    DELETABLE_ENTITY = (Identifiable, Temporal, SoftDeletable)
    
    # Full-featured entity
    FULL_ENTITY = (Identifiable, Temporal, Auditable, SoftDeletable)
    
    # Event pattern
    EVENT = (Identifiable, Temporal, Embeddable, Invokable, Cryptographical)
```

### 4. Simplified Usage Patterns

With the unified API, usage becomes much clearer:

```python
# Simple entity with ID and timestamps
User = create_model("User", Identifiable, Temporal,
    username=USERNAME_TEMPLATE,
    email=EMAIL_TEMPLATE
)

# Using protocol bundles
AuditedUser = create_model("AuditedUser", *ProtocolBundles.AUDITED_ENTITY,
    username=USERNAME_TEMPLATE,
    email=EMAIL_TEMPLATE
)

# Structure-only (no mixins)
UserData = create_model("UserData", Identifiable, Temporal,
    include_mixins=False,
    username=USERNAME_TEMPLATE
)

# With field overrides
CustomUser = create_model("CustomUser", Identifiable,
    id=ID_TEMPLATE.copy(frozen=True),  # Override to make ID frozen
    username=USERNAME_TEMPLATE
)

# Using string protocol names (for config/dynamic creation)
ConfiguredModel = create_model("MyModel", "identifiable", "temporal")
```

### 5. Enhanced Builder Pattern

Update `DomainModelBuilder` to use protocols:

```python
class DomainModelBuilder:
    """Fluent API for building models with protocols."""
    
    def with_protocols(self, *protocols: type[Protocol]) -> Self:
        """Add protocols to the model."""
        self._protocols.extend(protocols)
        return self
    
    def with_bundle(self, bundle: tuple[type[Protocol], ...]) -> Self:
        """Add a protocol bundle."""
        self._protocols.extend(bundle)
        return self
    
    # Convenience methods that map to protocols
    def with_identity(self) -> Self:
        """Add Identifiable protocol."""
        return self.with_protocols(Identifiable)
    
    def with_timestamps(self) -> Self:
        """Add Temporal protocol."""
        return self.with_protocols(Temporal)
    
    def with_audit(self) -> Self:
        """Add Auditable protocol."""
        return self.with_protocols(Auditable)
    
    def with_soft_delete(self) -> Self:
        """Add SoftDeletable protocol."""
        return self.with_protocols(SoftDeletable)

# Usage
Model = (
    DomainModelBuilder("Model")
    .with_bundle(ProtocolBundles.ENTITY)
    .with_audit()
    .with_field("name", NAME_TEMPLATE)
    .build()
)
```

### 6. Clear Protocol Discovery

Add utilities for protocol introspection:

```python
# protocols/utils.py
def get_protocol_fields(protocol: type[Protocol]) -> dict[str, FieldTemplate]:
    """Get all fields required by a protocol."""
    return PROTOCOL_FIELD_REGISTRY.get(protocol, {})

def get_protocol_info(protocol: type[Protocol]) -> ProtocolInfo:
    """Get comprehensive information about a protocol."""
    return ProtocolInfo(
        name=protocol.__name__,
        fields=get_protocol_fields(protocol),
        mixin=PROTOCOL_MIXIN_REGISTRY.get(protocol),
        description=protocol.__doc__
    )

def list_protocols() -> list[type[Protocol]]:
    """List all available protocols."""
    return list(PROTOCOL_REGISTRY.values())

def validate_model_protocols(model: type[BaseModel], *protocols: type[Protocol]) -> ValidationResult:
    """Check if a model satisfies protocol requirements."""
    # Implementation
```

## Migration Strategy

### Phase 1: Add Protocol-Centric Features
1. Add `__fields__` to all Protocol classes
2. Implement the unified `create_model` function
3. Create `ProtocolBundles` for common patterns
4. Keep existing APIs working

### Phase 2: Deprecate Redundant APIs
1. Mark `create_protocol_model` as deprecated → use `create_model`
2. Mark `FieldFamilies` as deprecated → use `ProtocolBundles`
3. Add deprecation warnings with migration hints

### Phase 3: Clean Up
1. Remove deprecated functions
2. Move all field definitions to their respective protocols
3. Simplify documentation to focus on protocol-driven approach

## Benefits

1. **Single Source of Truth**: Protocols define both structure and fields
2. **Intuitive API**: One function (`create_model`) handles all cases
3. **Clear Semantics**: Protocols are the primary abstraction
4. **Discoverable**: Easy to see what protocols are available and what they provide
5. **Flexible**: Can still override fields or exclude mixins when needed

## Example: Before and After

### Before (Confusing)
```python
# Which one to use?
# Option 1: Field families
from pydapter.fields import FieldFamilies
fields = {**FieldFamilies.ENTITY, **FieldFamilies.AUDIT}
Model1 = create_model("Model1", fields=fields)

# Option 2: Protocol families
from pydapter.fields import ProtocolFieldFamilies
Model2 = create_protocol_model("Model2", "identifiable", "temporal", "auditable")

# Option 3: Builder
Model3 = (
    DomainModelBuilder("Model3")
    .with_entity_fields()
    .with_audit_fields()
    .build()
)

# Option 4: Manual
class Model4(BaseModel, IdentifiableMixin, TemporalMixin, AuditableMixin):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    created_by: uuid.UUID | None
    updated_by: uuid.UUID | None
    version: int
```

### After (Clear)
```python
# One clear way
Model = create_model("Model", 
    Identifiable, Temporal, Auditable,
    name=NAME_TEMPLATE
)

# Or use bundles for common patterns
Model = create_model("Model",
    *ProtocolBundles.AUDITED_ENTITY,
    name=NAME_TEMPLATE
)
```

## Summary

This strategy aligns protocols and fields by:
1. Making protocols the primary interface
2. Automatically resolving fields from protocols
3. Providing a single, unified API
4. Supporting common patterns through bundles
5. Maintaining flexibility for advanced use cases

The result is a cleaner, more intuitive API that reduces ambiguity while preserving the power and flexibility of the current system.