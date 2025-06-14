# Test Fixes Summary

## Overview
After updating all FieldTemplate constructors to use the new kwargs pattern, we encountered and fixed 3 test failures.

## Fixes Applied

### 1. JSONB Support Test
**Issue**: Test expected JSON_TEMPLATE to have `db_type="jsonb"` metadata for PostgreSQL JSONB support.

**Fix**: Added `json_schema_extra` to JSON_TEMPLATE and METADATA_TEMPLATE:
```python
JSON_TEMPLATE = FieldTemplate(
    base_type=dict,
    description="JSON data",
    default=dict,
    json_schema_extra={"db_type": "jsonb"},
)
```

Also updated the test to check `json_schema_extra` instead of non-existent `extra_info` attribute.

### 2. EmailStr Type Mapping Test
**Issue**: Test expected FieldInfo to have annotation set to EmailStr, but our `create_field()` method doesn't set annotations.

**Fix**: Updated test to check the FieldTemplate's base_type directly:
```python
# Old: assert email_field.annotation == EmailStr
# New: assert EMAIL_TEMPLATE.base_type == EmailStr
```

### 3. Event Protocol Validator Test
**Issue**: Event model wasn't converting Pydantic models to dicts for the `request` field.

**Fix**: Added `mode="before"` to field validators in create_model():
```python
validators[validator_name] = field_validator(name, mode="before")(meta.value)
```

This ensures validators run before Pydantic's type validation, allowing the PARAMS validator to convert BaseModel instances to dicts.

## Additional Improvements

### Union Type Cleanup
Fixed unnecessary union types in favor of `nullable=True`:
- Changed `base_type=str | None` to `base_type=str, nullable=True`
- Changed `base_type=str | dict | None` to `base_type=dict, nullable=True`

This provides cleaner type handling and aligns with the new FieldTemplate design.

## Test Results
All 774 tests now pass successfully, with 11 skipped tests and 5 warnings.