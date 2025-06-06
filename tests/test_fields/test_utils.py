# test_utils.py
import asyncio
import json
from datetime import datetime
from typing import Any
from uuid import UUID

import pytest
from pydantic import BaseModel
from pydapter.fields.dts import DATETIME
from pydapter.fields.ids import ID_FROZEN
from pydapter.fields.types import Field, create_model

# ============================================
# Test Fixtures
# ============================================


@pytest.fixture
def sample_fields():
    """Provide a standard set of fields for testing"""
    return {
        "id": ID_FROZEN.copy(name="id"),
        "name": Field(name="name", annotation=str),
        "email": Field(
            name="email",
            annotation=str,
            validator=lambda cls, v: v if "@" in v else ValueError("Invalid email"),
        ),
        "age": Field(name="age", annotation=int, default=0),
        "active": Field(name="active", annotation=bool, default=True),
        "tags": Field(name="tags", annotation=list[str], default_factory=list),
        "metadata": Field(name="metadata", annotation=dict, default_factory=dict),
        "created_at": DATETIME.copy(name="created_at"),
    }


@pytest.fixture
def user_model_class(sample_fields):
    """Create a reusable User model class"""
    fields = [
        sample_fields["id"],
        sample_fields["name"],
        sample_fields["email"],
        sample_fields["created_at"],
    ]
    return create_model("User", fields=fields)


@pytest.fixture
def sample_user_data():
    """Provide sample user data for testing"""
    return {
        "name": "John Doe",
        "email": "john@example.com",
        "age": 30,
        "tags": ["customer", "premium"],
        "metadata": {"source": "web", "campaign": "summer2024"},
    }


# ============================================
# Test Helpers
# ============================================


class FieldTestHelper:
    """Helper methods for field testing"""

    @staticmethod
    def assert_field_properties(field: Field, expected: dict[str, Any]):
        """Assert field has expected properties"""
        for key, value in expected.items():
            actual = getattr(field, key)
            assert actual == value, f"Field.{key} = {actual}, expected {value}"

    @staticmethod
    def create_test_model(
        fields: list[Field], model_name: str = "TestModel"
    ) -> type[BaseModel]:
        """Create a test model with error handling"""
        try:
            return create_model(model_name, fields=fields)
        except Exception as e:
            pytest.fail(f"Failed to create model: {e}")

    @staticmethod
    def validate_field_roundtrip(field: Field, test_value: Any):
        """Test that a value can go through field validation and back"""
        # Create model with single field
        Model = create_model("TestModel", fields=[field])

        # Create instance
        instance = Model(**{field.name: test_value})

        # Serialize and deserialize
        json_str = instance.model_dump_json()
        parsed = Model.model_validate_json(json_str)

        # Verify roundtrip
        original_value = getattr(instance, field.name)
        parsed_value = getattr(parsed, field.name)

        if isinstance(original_value, UUID):
            assert str(original_value) == str(parsed_value)
        elif isinstance(original_value, datetime):
            assert original_value.isoformat() == parsed_value.isoformat()
        else:
            assert original_value == parsed_value


# ============================================
# Async Test Utilities
# ============================================


class AsyncFieldTester:
    """Utilities for testing fields in async contexts"""

    @staticmethod
    async def validate_concurrently(field: Field, values: list[Any]) -> list[bool]:
        """Validate multiple values concurrently"""

        async def validate_one(value):
            try:
                if field.validator:
                    field.validator(None, value)
                return True
            except Exception:
                return False

        tasks = [validate_one(v) for v in values]
        return await asyncio.gather(*tasks)

    @staticmethod
    async def stress_test_field(field: Field, valid_value: Any, iterations: int = 1000):
        """Stress test field validation"""
        tasks = []
        for i in range(iterations):
            # Mix valid and invalid values
            if i % 2 == 0:
                value = valid_value
            else:
                value = f"invalid_{i}"

            async def validate():
                try:
                    if field.validator:
                        field.validator(None, value)
                    return True
                except Exception:
                    return False

            tasks.append(validate())

        results = await asyncio.gather(*tasks)
        valid_count = sum(1 for r in results if r)
        return valid_count, iterations - valid_count


# ============================================
# Mock Objects and Factories
# ============================================


class FieldFactory:
    """Factory for creating test fields"""

    @staticmethod
    def create_email_field(name: str = "email", required: bool = True) -> Field:
        """Create a standard email field"""
        return Field(
            name=name,
            annotation=str,
            default=... if required else None,
            validator=lambda cls, v: (
                v if v and "@" in v else ValueError("Invalid email")
            ),
            title="Email Address",
            description="Valid email address",
        )

    @staticmethod
    def create_phone_field(name: str = "phone", required: bool = True) -> Field:
        """Create a phone number field"""

        def validate_phone(cls, v):
            if not v:
                return v if not required else ValueError("Phone required")
            # Simple validation - just check length
            digits = "".join(c for c in v if c.isdigit())
            if len(digits) < 10:
                raise ValueError("Phone must have at least 10 digits")
            return v

        return Field(
            name=name,
            annotation=str,
            default=... if required else None,
            validator=validate_phone,
        )

    @staticmethod
    def create_range_field(
        name: str,
        annotation: type = int,
        min_value: float = None,
        max_value: float = None,
    ) -> Field:
        """Create a field with range validation"""

        def validate_range(cls, v):
            if min_value is not None and v < min_value:
                raise ValueError(f"{name} must be >= {min_value}")
            if max_value is not None and v > max_value:
                raise ValueError(f"{name} must be <= {max_value}")
            return v

        return Field(name=name, annotation=annotation, validator=validate_range)


# ============================================
# Parameterized Test Data
# ============================================


class TestData:
    """Test data for parameterized tests"""

    VALID_UUIDS = [
        "550e8400-e29b-41d4-a716-446655440000",
        "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
        "00000000-0000-0000-0000-000000000000",
    ]

    INVALID_UUIDS = [
        "not-a-uuid",
        "550e8400-e29b-41d4-a716",  # Too short
        "550e8400-e29b-41d4-a716-446655440000-extra",  # Too long
        "550e8400-e29b-41d4-xxxx-446655440000",  # Invalid hex
        "",
        "123",
        None,
    ]

    VALID_DATETIMES = [
        "2024-01-15T10:30:00Z",
        "2024-01-15T10:30:00+00:00",
        "2024-01-15T10:30:00.123456Z",
        "2024-12-31T23:59:59-05:00",
    ]

    INVALID_DATETIMES = [
        "not-a-date",
        "2024-13-01T00:00:00Z",  # Invalid month
        "2024-01-32T00:00:00Z",  # Invalid day
        "2024-01-15",  # Missing time
        "10:30:00",  # Missing date
        "",
        None,
    ]

    VALID_EMBEDDINGS = [
        [1.0, 2.0, 3.0],
        [0.0],
        [-1.5, 0.0, 1.5],
        list(range(100)),  # Large embedding
        [],  # Empty is valid
    ]

    INVALID_EMBEDDINGS = [
        "not-a-list",
        ["not", "numbers"],
        [1.0, "2.0", 3.0],  # Mixed types
        {"not": "a list"},
        123,
    ]


# ============================================
# Benchmark Utilities
# ============================================


class BenchmarkHelper:
    """Utilities for performance testing"""

    @staticmethod
    def create_large_model(num_fields: int = 100) -> type[BaseModel]:
        """Create a model with many fields for performance testing"""
        fields = []
        for i in range(num_fields):
            field_type = i % 4
            if field_type == 0:
                field = Field(name=f"str_field_{i}", annotation=str, default="")
            elif field_type == 1:
                field = Field(name=f"int_field_{i}", annotation=int, default=0)
            elif field_type == 2:
                field = Field(name=f"float_field_{i}", annotation=float, default=0.0)
            else:
                field = Field(name=f"bool_field_{i}", annotation=bool, default=False)
            fields.append(field)

        return create_model("LargeModel", fields=fields)

    @staticmethod
    def generate_test_data(
        model_class: type[BaseModel], num_instances: int = 1000
    ) -> list[dict]:
        """Generate test data for a model"""
        instances = []
        for i in range(num_instances):
            data = {}
            for field_name, field_info in model_class.model_fields.items():
                if field_info.annotation is str:
                    data[field_name] = f"value_{i}"
                elif field_info.annotation is int:
                    data[field_name] = i
                elif field_info.annotation is float:
                    data[field_name] = float(i)
                elif field_info.annotation is bool:
                    data[field_name] = i % 2 == 0
            instances.append(data)
        return instances


# ============================================
# Custom Assertions
# ============================================


class FieldAssertions:
    """Custom assertions for field testing"""

    @staticmethod
    def assert_fields_equal(field1: Field, field2: Field, ignore: list[str] = None):
        """Assert two fields are equal (ignoring specified attributes)"""
        ignore = ignore or []

        for attr in field1.__slots__:
            if attr in ignore or attr.startswith("_"):
                continue

            val1 = getattr(field1, attr, None)
            val2 = getattr(field2, attr, None)

            assert val1 == val2, f"Fields differ on {attr}: {val1} != {val2}"

    @staticmethod
    def assert_model_has_fields(
        model_class: type[BaseModel], expected_fields: list[str]
    ):
        """Assert model has expected fields"""
        model_fields = set(model_class.model_fields.keys())
        expected_set = set(expected_fields)

        missing = expected_set - model_fields
        extra = model_fields - expected_set

        assert not missing, f"Model missing fields: {missing}"
        assert not extra, f"Model has extra fields: {extra}"

    @staticmethod
    def assert_validation_error(
        model_class: type[BaseModel], data: dict, error_field: str
    ):
        """Assert that creating a model with data raises validation error on specific field"""
        with pytest.raises(Exception) as exc_info:
            model_class(**data)

        # Check that error mentions the expected field
        error_str = str(exc_info.value).lower()
        assert error_field.lower() in error_str, (
            f"Expected error for field '{error_field}', but got: {exc_info.value}"
        )


# ============================================
# Test Decorators
# ============================================


def parametrize_fields(*field_names):
    """Decorator to parametrize test with different fields"""

    def decorator(test_func):
        @pytest.mark.parametrize("field_name", field_names)
        def wrapper(self, field_name, sample_fields, *args, **kwargs):
            field = sample_fields[field_name]
            return test_func(self, field, *args, **kwargs)

        return wrapper

    return decorator


def with_temp_model(fields: list[Field]):
    """Decorator that creates a temporary model for the test"""

    def decorator(test_func):
        def wrapper(*args, **kwargs):
            model_class = create_model("TempModel", fields=fields)
            return test_func(*args, model_class=model_class, **kwargs)

        return wrapper

    return decorator


# ============================================
# Integration Test Base Class
# ============================================


class FieldIntegrationTestBase:
    """Base class for field integration tests"""

    def setup_method(self):
        """Setup for each test"""
        self.helper = FieldTestHelper()
        self.factory = FieldFactory()
        self.assertions = FieldAssertions()

    def create_test_model(self, *fields: Field) -> type[BaseModel]:
        """Create a test model from fields"""
        return create_model("TestModel", fields=list(fields))

    def assert_roundtrip(self, model_class: type[BaseModel], data: dict):
        """Assert data can roundtrip through model"""
        # Create instance
        instance = model_class(**data)

        # Convert to dict
        instance.model_dump()

        # Convert to JSON and back
        json_str = instance.model_dump_json()
        parsed_dict = json.loads(json_str)

        # Create new instance from parsed data
        new_instance = model_class(**parsed_dict)

        # Should be equivalent
        assert instance.model_dump() == new_instance.model_dump()
