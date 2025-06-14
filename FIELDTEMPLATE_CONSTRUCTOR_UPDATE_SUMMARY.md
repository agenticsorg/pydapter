# FieldTemplate Constructor Update Summary

## Overview
Successfully updated all FieldTemplate constructors throughout the codebase to use the new kwargs-based pattern instead of method chaining.

## Key Changes

### 1. Constructor Pattern Update
Changed from method chaining to kwargs constructor:
```python
# Old pattern:
FieldTemplate(base_type).with_description("...").with_default(value)

# New pattern:
FieldTemplate(base_type, description="...", default=value)
```

### 2. Files Updated

#### Core Field Definition Files:
- **execution.py**: Updated EXECUTION template
- **params.py**: Updated PARAMS, PARAM_TYPE, and PARAM_TYPE_NULLABLE templates
- **embedding.py**: Updated EMBEDDING template with validator and json_schema_extra
- **ids.py**: Updated ID_FROZEN, ID_MUTABLE, and ID_NULLABLE templates
- **dts.py**: Updated DATETIME and DATETIME_NULLABLE templates
- **builder.py**: Updated examples in docstrings

#### Protocol and Event Files:
- **protocol_families.py**: Fixed union types to use nullable=True instead
- **event.py**: Replaced union types (e.g., `str | None`) with simple types + nullable=True

#### Examples:
- **new_field_template_usage.py**: Updated all examples to use new constructor pattern

### 3. Important Improvements

#### Nullable Handling:
- When using `nullable=True`, the base type should be the simple type, not a union with None
- The nullable handling is done internally by FieldTemplate

```python
# Good:
FieldTemplate(base_type=str, nullable=True, default=None)

# Avoid:
FieldTemplate(base_type=str | None, default=None)
```

#### Default vs Default Factory:
- Callables (like `list`, `dict`, `uuid4`) are automatically treated as default_factory
- No need to distinguish between them in the constructor

```python
FieldTemplate(
    base_type=list[float],
    default=list,  # Automatically treated as default_factory
)
```

### 4. Benefits of New Pattern

1. **Cleaner Syntax**: Single constructor call instead of chained methods
2. **Better IDE Support**: All parameters visible in one place
3. **Easier to Read**: All field configuration in one location
4. **Type Safety**: Better type checking with explicit kwargs

### 5. Test Results
All 160 field tests are passing, confirming the migration is complete and successful.

## Migration Guide for Users

If you have code using the old pattern, update it as follows:

```python
# Old:
template = FieldTemplate(str)
    .with_description("My field")
    .with_default("value")
    .with_validator(my_validator)
    .as_nullable()

# New:
template = FieldTemplate(
    str,
    description="My field",
    default="value",
    validator=my_validator,
    nullable=True,
)
```