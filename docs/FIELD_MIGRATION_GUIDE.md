# Field to FieldTemplate Migration Guide

This guide explains how to migrate from the deprecated `Field` class to the
new `FieldTemplate` system in pydapter.

## Overview

The `Field` class has been deprecated in favor of `FieldTemplate`, which
provides a more compositional and flexible approach to defining fields. The
new system uses method chaining for a cleaner API and better type safety.

## Key Changes

1. **Compositional API**: FieldTemplate uses method chaining instead of constructor parameters
2. **Immutable Design**: FieldTemplate instances are frozen dataclasses
3. **Better Caching**: Aggressive caching for performance with bounded memory usage
4. **Clearer Semantics**: Methods like `as_nullable()` and `with_default()` make intent clearer

## Migration Examples

### Basic Field Definition

**Old way (deprecated):**

```python
from pydapter.fields import Field

status_field = Field(
    name="status",
    annotation=str,
    default="active",
    description="Status of the record"
)
```

**New way:**

```python
from pydapter.fields import FieldTemplate

status_field = FieldTemplate(str).with_description("Status of the record").with_default("active")
```

### Nullable Fields

**Old way:**

```python
optional_field = Field(
    name="optional_field",
    annotation=str | None,
    default=None,
    description="Optional field"
)
```

**New way:**

```python
optional_field = FieldTemplate(str).as_nullable().with_description("Optional field")
```

### Fields with Validators

**Old way:**

```python
def validate_positive(cls, v):
    if v < 0:
        raise ValueError("Must be positive")
    return v

age_field = Field(
    name="age",
    annotation=int,
    validator=validate_positive,
    description="Age must be positive"
)
```

**New way:**

```python
def validate_positive(v):
    return v >= 0

age_field = (
    FieldTemplate(int)
    .with_validator(validate_positive)
    .with_description("Age must be positive")
)
```

### Creating Models

**Old way:**

```python
from pydapter.fields import create_model, Field

fields = [
    Field(name="id", annotation=uuid.UUID, default_factory=uuid.uuid4),
    Field(name="name", annotation=str),
    Field(name="age", annotation=int, default=0)
]

UserModel = create_model("User", fields=fields)
```

**New way:**

```python
from pydapter.fields import create_model, FieldTemplate

fields = {
    "id": FieldTemplate(uuid.UUID).with_default(uuid.uuid4),
    "name": FieldTemplate(str),
    "age": FieldTemplate(int).with_default(0)
}

UserModel = create_model("User", fields=fields)
```

### Using Pre-built Templates

**New way only:**

```python
from pydapter.fields import ID_FROZEN, DATETIME, JSON_TEMPLATE

fields = {
    "id": ID_FROZEN,
    "created_at": DATETIME,
    "metadata": JSON_TEMPLATE
}

Model = create_model("MyModel", fields=fields)
```

## Advanced Features

### Composition of Templates

```python
# Create a base template
base_string = FieldTemplate(str).with_description("Text field")

# Create variations
nullable_string = base_string.as_nullable()
string_list = base_string.as_listable()
frozen_string = base_string.with_frozen(True)
```

### Custom Metadata

```python
# Add custom metadata that will be included in JSON schema
template = (
    FieldTemplate(str)
    .with_metadata("ui_widget", "textarea")
    .with_metadata("max_rows", 10)
)
```

## API Reference

### FieldTemplate Methods

- `as_nullable()` - Make field accept None values
- `as_listable()` - Make field accept list of values
- `with_default(value)` - Set default value
- `with_validator(func)` - Add validation function
- `with_description(text)` - Add field description
- `with_frozen(bool)` - Make field immutable
- `with_alias(name)` - Set field alias
- `with_title(text)` - Set field title
- `with_exclude(bool)` - Exclude from serialization
- `with_metadata(key, value)` - Add custom metadata

### Pre-built Templates

- `ID_FROZEN` - Immutable UUID field
- `ID_MUTABLE` - Mutable UUID field
- `ID_NULLABLE` - Optional UUID field
- `DATETIME` - DateTime field with timezone
- `EMBEDDING` - List of floats for ML embeddings
- `JSON_TEMPLATE` - JSON/dict field
- `METADATA_TEMPLATE` - Metadata dict field
- `PARAMS` - Parameters dict field

## Performance Considerations

The new FieldTemplate system includes several performance optimizations:

- Bounded LRU cache for annotated types (configurable via
  LIONAGI_FIELD_CACHE_SIZE)
- Metadata limit warnings (configurable via LIONAGI_FIELD_META_LIMIT)
- Thread-safe caching implementation
- Lazy materialization of annotated types

## Environment Variables

- `LIONAGI_FIELD_CACHE_SIZE` - Maximum cached annotated types (default: 10000)
- `LIONAGI_FIELD_META_LIMIT` - Metadata items warning threshold (default: 10)

## Deprecation Timeline

The `Field` class is deprecated as of version 2.0.0 and will be removed in a
future major release. We recommend migrating to `FieldTemplate` as soon as
possible.

## Need Help?

If you encounter issues during migration:

1. Check the test files for examples
2. Review the docstrings in the source code
3. Open an issue on GitHub with your specific use case
