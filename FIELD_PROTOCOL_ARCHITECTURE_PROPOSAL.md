# Field-Protocol Architecture Proposal

## Executive Summary

Based on the analysis, I propose keeping fields and protocols **separated but tightly integrated** through a clear contract system. This separation of concerns provides maximum flexibility while maintaining ease of use.

## 1. Should They Be Merged or Remain Separated?

### **Answer: Remain Separated with Clear Integration Points**

#### Rationale:
- **Fields** are about **data structure** (what attributes exist)
- **Protocols** are about **contracts and behavior** (what capabilities exist)
- Merging them would violate single responsibility principle

#### Proposed Architecture:

```python
# protocols/base.py
class Protocol:
    """Base protocol with field requirements."""
    __required_fields__: dict[str, FieldTemplate] = {}
    __optional_fields__: dict[str, FieldTemplate] = {}
    __config__: ConfigDict = ConfigDict()

# protocols/identifiable.py
class Identifiable(Protocol):
    """Identity contract."""
    id: uuid.UUID
    
    __required_fields__ = {
        "id": ID_TEMPLATE
    }

class IdentifiableMixin:
    """Identity behaviors."""
    def get_id(self) -> uuid.UUID: ...
    def equals_by_id(self, other) -> bool: ...

# fields/registry.py
class FieldRegistry:
    """Central registry for protocol-field mapping."""
    
    @classmethod
    def get_fields_for_protocol(cls, protocol: Type[Protocol]) -> dict:
        return {
            **protocol.__required_fields__,
            **protocol.__optional_fields__
        }
```

## 2. Field Composability vs Protocol Composability

### Field Composability (Bottom-up, Structural)

```python
# Atomic field templates
ID_FIELD = FieldTemplate(base_type=uuid.UUID)
TIMESTAMP_FIELD = FieldTemplate(base_type=datetime)

# Compositional modifiers
NULLABLE_ID = ID_FIELD.as_nullable()
ID_LIST = ID_FIELD.as_listable()
INDEXED_ID = ID_FIELD.with_index("btree")

# Field collections (structural grouping)
AUDIT_FIELDS = {
    "created_by": ID_FIELD.as_nullable(),
    "updated_by": ID_FIELD.as_nullable(),
    "version": FieldTemplate(base_type=int, default=1)
}
```

### Protocol Composability (Top-down, Contractual)

```python
# Atomic protocols
class Identifiable(Protocol):
    """Has identity."""
    id: uuid.UUID

class Timestamped(Protocol):
    """Has timestamps."""
    created_at: datetime
    updated_at: datetime

# Protocol composition through inheritance
class Entity(Identifiable, Timestamped, Protocol):
    """Composite protocol: identity + timestamps."""
    pass

# Protocol composition through aggregation
class AuditedEntity(Protocol):
    """Explicitly combines multiple protocols."""
    __composed_protocols__ = [Identifiable, Timestamped, Auditable]
```

### Key Differences:

| Aspect | Field Composability | Protocol Composability |
|--------|-------------------|---------------------|
| **Direction** | Bottom-up (fields → structures) | Top-down (contracts → requirements) |
| **Focus** | Data structure | Behavior contracts |
| **Flexibility** | Modify individual fields | Combine entire contracts |
| **Validation** | Type/value constraints | Contract compliance |
| **Reusability** | Field-level | Protocol-level |

## 3. Effective Reuse Without Cognitive Overhead

### **Solution: Three-Tier API**

#### Tier 1: Simple Presets (80% use case)
```python
# Simple, opinionated presets
from pydapter.presets import create_entity, create_event, create_document

# One-liner for common patterns
User = create_entity(
    "User",
    username=str,
    email=EmailStr,
    is_active=bool
)
# Automatically includes: id, created_at, updated_at

Event = create_event(
    "UserLoginEvent",
    user_id=uuid.UUID,
    ip_address=str
)
# Automatically includes: id, created_at, event_type, sha256
```

#### Tier 2: Protocol-Based (15% use case)
```python
# More control, still simple
from pydapter import create_model
from pydapter.protocols import Identifiable, Temporal, Auditable

CustomEntity = create_model(
    "CustomEntity",
    Identifiable,
    Temporal,
    Auditable,
    # Custom fields
    status=FieldTemplate(base_type=str, choices=["active", "inactive"]),
    metadata=JSON_TEMPLATE
)
```

#### Tier 3: Full Control (5% use case)
```python
# Complete control for advanced users
from pydapter.fields import FieldTemplate, DomainModelBuilder
from pydapter.protocols import Protocol

class CustomProtocol(Protocol):
    __required_fields__ = {
        "custom_id": FieldTemplate(
            base_type=str,
            pattern=r"^CUST-\d{6}$"
        )
    }

Model = (
    DomainModelBuilder("Model")
    .with_protocol(CustomProtocol)
    .with_field("data", FieldTemplate(base_type=dict))
    .with_config(ConfigDict(validate_assignment=True))
    .build()
)
```

### Cognitive Load Reduction Strategies:

1. **Consistent Naming**: `create_*` for all factory functions
2. **Progressive Disclosure**: Start simple, add complexity as needed
3. **Clear Defaults**: Sensible defaults for all common cases
4. **Type Hints**: Full typing for IDE support
5. **Rich Examples**: Each tier has comprehensive examples

## 4. Alignment with Microservice Architecture

### **Design for Service Boundaries**

#### Service-Specific Protocols
```python
# protocols/service_protocols.py
class PublicAPIEntity(Protocol):
    """Protocol for public API entities."""
    id: str  # String IDs for public APIs
    created_at: datetime
    updated_at: datetime
    version: str  # API versioning
    
    __config__ = ConfigDict(
        json_schema_extra={"x-api-version": "v1"},
        alias_generator=to_camel  # camelCase for APIs
    )

class InternalServiceEntity(Protocol):
    """Protocol for internal service communication."""
    id: uuid.UUID  # UUIDs for internal
    created_at: datetime
    updated_at: datetime
    correlation_id: str  # For distributed tracing
    
    __config__ = ConfigDict(
        json_encoders={uuid.UUID: str}  # String serialization
    )

class EventStoreEntity(Protocol):
    """Protocol for event sourcing."""
    id: uuid.UUID
    created_at: datetime
    event_type: str
    aggregate_id: uuid.UUID
    sequence_number: int
    
    __config__ = ConfigDict(frozen=True)  # Immutable events
```

#### Adapter-Aware Field Templates
```python
# fields/service_fields.py
class ServiceFieldTemplates:
    # API Gateway fields
    API_ID = FieldTemplate(
        base_type=str,
        pattern=r"^[a-zA-Z0-9-_]+$",
        json_schema_extra={
            "x-api-visible": True,
            "x-searchable": True
        }
    )
    
    # Message Queue fields
    CORRELATION_ID = FieldTemplate(
        base_type=str,
        default_factory=lambda: str(uuid.uuid4()),
        json_schema_extra={
            "x-header": "X-Correlation-ID",
            "x-propagate": True
        }
    )
    
    # Event Store fields
    SEQUENCE_NUMBER = FieldTemplate(
        base_type=int,
        ge=0,
        json_schema_extra={
            "x-index": "clustered",
            "x-partition-key": True
        }
    )
```

#### Service Boundary Utilities
```python
# boundaries.py
class ServiceBoundary:
    """Utilities for service boundaries."""
    
    @staticmethod
    def create_dto(
        name: str,
        source_model: Type[BaseModel],
        service_type: Literal["public_api", "internal", "event"]
    ) -> Type[BaseModel]:
        """Create DTO for service boundary."""
        if service_type == "public_api":
            protocols = [PublicAPIEntity]
            config = ConfigDict(alias_generator=to_camel)
        elif service_type == "internal":
            protocols = [InternalServiceEntity]
            config = ConfigDict()
        else:  # event
            protocols = [EventStoreEntity]
            config = ConfigDict(frozen=True)
        
        return create_model(
            f"{name}DTO",
            *protocols,
            config=config,
            **extract_fields(source_model)
        )
    
    @staticmethod
    def create_event(
        name: str,
        aggregate: str,
        **fields
    ) -> Type[BaseModel]:
        """Create event for event-driven architecture."""
        return create_model(
            name,
            EventStoreEntity,
            aggregate_id=FieldTemplate(
                base_type=uuid.UUID,
                description=f"ID of {aggregate} aggregate"
            ),
            **fields
        )
```

### Microservice Patterns Support:

#### 1. **API Gateway Pattern**
```python
# Easy API model creation
UserAPI = ServiceBoundary.create_dto(
    "User",
    source_model=UserDomain,
    service_type="public_api"
)
```

#### 2. **Event Sourcing**
```python
# Event creation for event store
UserCreatedEvent = ServiceBoundary.create_event(
    "UserCreatedEvent",
    aggregate="User",
    username=str,
    email=EmailStr
)
```

#### 3. **CQRS Pattern**
```python
# Separate read/write models
UserCommand = create_model(
    "UserCommand",
    InternalServiceEntity,
    command_type=Literal["create", "update", "delete"],
    payload=dict
)

UserQuery = create_model(
    "UserQuery", 
    PublicAPIEntity,
    fields=["id", "username", "email", "created_at"]
)
```

#### 4. **Service Mesh Integration**
```python
# Headers for service mesh
class ServiceMeshAware(Protocol):
    __required_fields__ = {
        "trace_id": FieldTemplate(base_type=str),
        "span_id": FieldTemplate(base_type=str),
        "parent_span_id": FieldTemplate(base_type=str).as_nullable()
    }
```

## Summary Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Application Layer                      │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │   Presets   │  │Protocol-Based│  │ Full Control  │  │
│  │  (Simple)   │  │  (Flexible)  │  │  (Advanced)   │  │
│  └─────────────┘  └──────────────┘  └───────────────┘  │
└─────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────┐
│                   Integration Layer                       │
│  ┌──────────────────────┐  ┌────────────────────────┐   │
│  │   Field Registry     │  │  Protocol Registry     │   │
│  │ (Structure Mapping)  │  │ (Contract Definition)  │   │
│  └──────────────────────┘  └────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────┐
│                      Core Layer                          │
│  ┌─────────────┐  ┌─────────────┐  ┌────────────────┐  │
│  │    Fields   │  │  Protocols  │  │   Adapters     │  │
│  │ (Structure) │  │ (Contracts) │  │ (Persistence)  │  │
│  └─────────────┘  └─────────────┘  └────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

This architecture provides:
1. **Clear separation** between structure (fields) and contracts (protocols)
2. **Flexible composition** at both field and protocol levels
3. **Progressive complexity** through three-tier API
4. **Microservice-ready** patterns and utilities