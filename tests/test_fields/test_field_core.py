# test_field_core.py
import json
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st
from hypothesis.strategies import composite
from pydapter.exceptions import ValidationError as ValidationException
from pydapter.fields.dts import DATETIME, validate_datetime
from pydapter.fields.embedding import EMBEDDING, validate_embedding
from pydapter.fields.ids import ID_FROZEN, ID_MUTABLE, ID_NULLABLE, validate_uuid
from pydapter.fields.params import PARAMS, validate_model_to_params
from pydapter.fields.types import Field, Undefined, create_model

# ============================================
# Test Undefined Singleton
# ============================================


class TestUndefinedType:
    """Test the Undefined singleton behavior"""

    def test_undefined_is_singleton(self):
        """Undefined should always be the same instance"""
        from pydapter.fields.types import Undefined as Undefined2

        assert Undefined is Undefined2
        assert id(Undefined) == id(Undefined2)

    def test_undefined_is_falsy(self):
        """Undefined should evaluate to False"""
        assert not Undefined
        assert not bool(Undefined)

    def test_undefined_repr(self):
        """Undefined should have consistent representation"""
        assert repr(Undefined) == "UNDEFINED"
        assert str(Undefined) == "UNDEFINED"

    def test_undefined_deepcopy(self):
        """Undefined should remain singleton even after deepcopy"""
        import copy

        copied = copy.deepcopy(Undefined)
        assert copied is Undefined

    def test_undefined_in_conditions(self):
        """Test Undefined in various conditional contexts"""
        # Should work in identity checks
        assert Undefined is Undefined

        # Should work in equality (though not recommended)
        value = Undefined
        assert value is Undefined

        # Should work in containers
        assert Undefined in [Undefined, None, 0]


# ============================================
# Test Core Field Class
# ============================================


class TestFieldClass:
    """Test the Field descriptor class"""

    def test_field_creation_basic(self):
        """Test basic field creation"""
        field = Field(name="test_field", annotation=str, default="default_value")
        assert field.name == "test_field"
        assert field.annotation is str
        assert field.default == "default_value"

    def test_field_creation_with_factory(self):
        """Test field creation with default_factory"""
        field = Field(name="test_field", annotation=list, default_factory=list)
        assert field.name == "test_field"
        assert field.default_factory is list
        assert field.default is Undefined

    def test_field_cannot_have_both_default_and_factory(self):
        """Field should not allow both default and default_factory"""
        with pytest.raises(
            ValueError, match="Cannot have both default and default_factory"
        ):
            Field(
                name="test_field", annotation=str, default="value", default_factory=str
            )

    def test_field_immutability(self):
        """Test that immutable fields cannot be modified"""
        field = Field(name="immutable_field", annotation=str, immutable=True)

        with pytest.raises(AttributeError, match="Cannot modify immutable field"):
            field.name = "new_name"

        with pytest.raises(AttributeError):
            field.annotation = int

    def test_field_copy(self):
        """Test field copying preserves all attributes"""
        original = Field(
            name="original",
            annotation=str,
            default="test",
            title="Test Field",
            description="A test field",
            frozen=True,
            exclude=False,
        )

        # Copy with no changes
        copy1 = original.copy()
        assert copy1.name == original.name
        assert copy1.annotation == original.annotation
        assert copy1.default == original.default
        assert copy1.title == original.title
        assert copy1.frozen == original.frozen

        # Copy with changes
        copy2 = original.copy(name="modified", default="new_default")
        assert copy2.name == "modified"
        assert copy2.default == "new_default"
        assert copy2.annotation == original.annotation  # Unchanged

    def test_field_as_nullable(self):
        """Test nullable field generation"""
        # Non-nullable field
        field = Field(name="test", annotation=str, default="value")
        nullable = field.as_nullable()

        assert nullable.annotation == str | None
        assert nullable.default is None
        assert nullable.default_factory is Undefined

        # Already nullable field
        already_nullable = Field(name="test", annotation=int | None)
        still_nullable = already_nullable.as_nullable()
        assert still_nullable.annotation == int | None

    def test_field_as_listable(self):
        """Test listable field generation"""
        field = Field(name="test", annotation=str)

        # Non-strict: allows single value or list
        listable = field.as_listable(strict=False)
        assert listable.annotation == list[str] | str

        # Strict: only allows list
        strict_listable = field.as_listable(strict=True)
        assert strict_listable.annotation == list[str]

    def test_field_to_pydantic_field_info(self):
        """Test conversion to Pydantic FieldInfo"""
        field = Field(
            name="test",
            annotation=str,
            default="default",
            title="Test Field",
            description="Description",
            examples=["ex1", "ex2"],
            frozen=True,
        )

        field_info = field.field_info
        assert field_info.default == "default"
        assert field_info.title == "Test Field"
        assert field_info.description == "Description"
        assert field_info.examples == ["ex1", "ex2"]
        assert field_info.frozen is True


# ============================================
# Test ID Fields
# ============================================


class TestIDFields:
    """Test UUID-based ID fields"""

    def test_validate_uuid_with_uuid_object(self):
        """validate_uuid should accept UUID objects"""
        test_uuid = uuid4()
        result = validate_uuid(test_uuid)
        assert result == test_uuid
        assert isinstance(result, UUID)

    def test_validate_uuid_with_string(self):
        """validate_uuid should parse valid UUID strings"""
        uuid_str = "550e8400-e29b-41d4-a716-446655440000"
        result = validate_uuid(uuid_str)
        assert isinstance(result, UUID)
        assert str(result) == uuid_str

    def test_validate_uuid_with_invalid_string(self):
        """validate_uuid should raise ValidationException for invalid UUIDs"""
        with pytest.raises(ValidationException, match="must be a valid UUID"):
            validate_uuid("not-a-uuid")

        with pytest.raises(ValidationException):
            validate_uuid("550e8400-e29b-41d4-a716")  # Too short

    def test_validate_uuid_nullable(self):
        """validate_uuid should handle nullable parameter"""
        assert validate_uuid("", nullable=True) is None
        assert validate_uuid(None, nullable=True) is None

        # Should still validate non-empty values
        with pytest.raises(ValidationException):
            validate_uuid("invalid", nullable=True)

    def test_id_frozen_field(self):
        """Test ID_FROZEN field properties"""
        assert ID_FROZEN.name == "id"
        assert ID_FROZEN.annotation == UUID
        assert ID_FROZEN.frozen is True
        assert ID_FROZEN.title == "ID"
        assert callable(ID_FROZEN.default_factory)

        # Should generate new UUIDs
        uuid1 = ID_FROZEN.default_factory()
        uuid2 = ID_FROZEN.default_factory()
        assert uuid1 != uuid2
        assert isinstance(uuid1, UUID)

    def test_id_mutable_field(self):
        """Test ID_MUTABLE field properties"""
        assert ID_MUTABLE.name == "id"
        assert ID_MUTABLE.annotation == UUID
        assert ID_MUTABLE.frozen is not True
        assert ID_MUTABLE.title == "ID"

    def test_id_nullable_field(self):
        """Test ID_NULLABLE field properties"""
        assert ID_NULLABLE.name == "nullable_id"
        assert ID_NULLABLE.annotation == UUID | None
        assert ID_NULLABLE.default is None

    @given(st.text())
    def test_uuid_validation_property(self, text):
        """Property test: validate_uuid should never crash"""
        try:
            validate_uuid(text)
        except ValidationException:
            pass  # Expected for invalid input
        except Exception as e:
            pytest.fail(f"Unexpected exception: {type(e).__name__}: {e}")


# ============================================
# Test DateTime Fields
# ============================================


class TestDateTimeFields:
    """Test datetime fields and validation"""

    def test_validate_datetime_with_datetime_object(self):
        """validate_datetime should accept datetime objects"""
        now = datetime.now(timezone.utc)
        result = validate_datetime(now)
        assert result == now
        assert isinstance(result, datetime)

    def test_validate_datetime_with_iso_string(self):
        """validate_datetime should parse ISO format strings"""
        iso_string = "2024-01-15T10:30:00+00:00"
        result = validate_datetime(iso_string)
        assert isinstance(result, datetime)
        assert result.isoformat() == iso_string

    def test_validate_datetime_with_invalid_string(self):
        """validate_datetime should raise ValidationException for invalid formats"""
        with pytest.raises(ValidationException, match="Invalid datetime format"):
            validate_datetime("not-a-date")

        with pytest.raises(ValidationException):
            validate_datetime("2024-13-01")  # Invalid month

    def test_validate_datetime_nullable(self):
        """validate_datetime should handle nullable parameter"""
        assert validate_datetime("", nullable=True) is None
        assert validate_datetime(None, nullable=True) is None
        assert validate_datetime(0, nullable=True) is None

    def test_datetime_field_default_factory(self):
        """DATETIME field should generate current UTC time"""
        # Get default value
        time1 = DATETIME.default_factory()
        assert isinstance(time1, datetime)
        assert time1.tzinfo is not None

        # Should generate new times
        import time

        time.sleep(0.001)
        time2 = DATETIME.default_factory()
        assert time2 > time1

    def test_datetime_serializer(self):
        """Test datetime serialization"""
        from pydapter.fields.dts import datetime_serializer

        dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        serialized = datetime_serializer(dt)
        assert serialized == "2024-01-15T10:30:00+00:00"
        assert isinstance(serialized, str)

    @given(st.text())
    def test_datetime_validation_property(self, text):
        """Property test: validate_datetime should handle any string input"""
        try:
            validate_datetime(text)
        except ValidationException:
            pass  # Expected for invalid input
        except Exception as e:
            pytest.fail(f"Unexpected exception: {type(e).__name__}: {e}")


# ============================================
# Test Embedding Fields
# ============================================


class TestEmbeddingFields:
    """Test embedding fields for ML vectors"""

    def test_validate_embedding_with_list(self):
        """validate_embedding should accept list of floats"""
        embedding = [1.0, 2.0, 3.0, 4.0]
        result = validate_embedding(embedding)
        assert result == embedding
        assert all(isinstance(x, float) for x in result)

    def test_validate_embedding_with_json_string(self):
        """validate_embedding should parse JSON strings"""
        json_str = "[1.0, 2.0, 3.0, 4.0]"
        result = validate_embedding(json_str)
        assert result == [1.0, 2.0, 3.0, 4.0]

    def test_validate_embedding_with_integers(self):
        """validate_embedding should convert integers to floats"""
        embedding = [1, 2, 3, 4]
        result = validate_embedding(embedding)
        assert result == [1.0, 2.0, 3.0, 4.0]
        assert all(isinstance(x, float) for x in result)

    def test_validate_embedding_with_none(self):
        """validate_embedding should return empty list for None"""
        result = validate_embedding(None)
        assert result == []

    def test_validate_embedding_with_invalid_json(self):
        """validate_embedding should raise ValueError for invalid JSON"""
        with pytest.raises(ValueError, match="Invalid embedding string"):
            validate_embedding("{not: valid: json}")

    def test_validate_embedding_with_non_numeric_list(self):
        """validate_embedding should raise ValueError for non-numeric values"""
        with pytest.raises(ValueError, match="Invalid embedding list"):
            validate_embedding([1.0, "two", 3.0])

    def test_embedding_field_properties(self):
        """Test EMBEDDING field configuration"""
        assert EMBEDDING.name == "embedding"
        assert EMBEDDING.annotation == list[float]
        assert EMBEDDING.title == "Embedding"
        assert "vector" in EMBEDDING.description.lower()

    @given(
        st.lists(
            st.floats(allow_nan=False, allow_infinity=False), min_size=0, max_size=100
        )
    )
    def test_embedding_roundtrip_property(self, embedding):
        """Property test: embeddings should roundtrip through JSON"""
        json_str = json.dumps(embedding)
        result = validate_embedding(json_str)
        assert len(result) == len(embedding)
        for original, parsed in zip(embedding, result, strict=False):
            assert abs(original - parsed) < 1e-10


# ============================================
# Test Params Fields
# ============================================


class TestParamsFields:
    """Test parameter fields for dynamic configs"""

    def test_validate_params_with_dict(self):
        """validate_model_to_params should accept dictionaries"""
        params = {"key": "value", "number": 42}
        result = validate_model_to_params(params)
        assert result == params

    def test_validate_params_with_empty_values(self):
        """validate_model_to_params should return {} for empty values"""
        assert validate_model_to_params(None) == {}
        assert validate_model_to_params({}) == {}
        assert validate_model_to_params([]) == {}
        assert validate_model_to_params(Undefined) == {}

    def test_validate_params_with_basemodel(self):
        """validate_model_to_params should convert BaseModel to dict"""
        from pydantic import BaseModel

        class TestModel(BaseModel):
            name: str = "test"
            value: int = 42

        model = TestModel()
        result = validate_model_to_params(model)
        assert result == {"name": "test", "value": 42}

    def test_validate_params_invalid_input(self):
        """validate_model_to_params should raise for invalid input"""
        with pytest.raises(ValidationException, match="Invalid params input"):
            validate_model_to_params("string")

        with pytest.raises(ValidationException):
            validate_model_to_params(123)

    def test_params_field_properties(self):
        """Test PARAMS field configuration"""
        assert PARAMS.name == "params"
        assert PARAMS.annotation is dict
        assert PARAMS.default_factory is dict


# ============================================
# Test Model Creation
# ============================================


class TestModelCreation:
    """Test dynamic model creation from fields"""

    def test_create_basic_model(self):
        """Test creating a simple model from fields"""

        fields = {
            "id": ID_FROZEN,
            "name": Field(name="name", annotation=str),
            "age": Field(name="age", annotation=int, default=0),
        }

        Model = create_model("TestModel", fields=fields)

        # Test model creation
        instance = Model(name="Test")
        assert isinstance(instance.id, UUID)
        assert instance.name == "Test"
        assert instance.age == 0

    def test_create_model_with_validators(self):
        """Test model creation with field validators"""

        def validate_positive(cls, v):
            if v < 0:
                raise ValueError("Must be positive")
            return v

        fields = {
            "count": Field(name="count", annotation=int, validator=validate_positive),
        }

        Model = create_model("TestModel", fields=fields)

        # Valid value
        instance = Model(count=5)
        assert instance.count == 5

        # Invalid value
        with pytest.raises(ValueError, match="Must be positive"):
            Model(count=-1)

    def test_create_frozen_model(self):
        """Test creating an immutable model"""
        fields = [Field(name="id", annotation=int), Field(name="value", annotation=str)]

        Model = create_model("FrozenModel", fields=fields, frozen=True)
        instance = Model(id=1, value="test")

        # Should not be able to modify
        with pytest.raises(Exception):  # Pydantic raises validation error
            instance.id = 2

    def test_create_model_with_base_class(self):
        """Test model creation with inheritance"""
        from pydantic import BaseModel

        class BaseClass(BaseModel):
            base_field: str = "base"

        fields = [Field(name="child_field", annotation=int)]

        Model = create_model("ChildModel", base=BaseClass, fields=fields)
        instance = Model(child_field=42)

        assert instance.base_field == "base"
        assert instance.child_field == 42


# ============================================
# Performance and Stress Tests
# ============================================


class TestPerformance:
    """Performance benchmarks for field validation"""

    def test_uuid_validation_performance(self, benchmark):
        """Benchmark UUID validation"""
        valid_uuid = "550e8400-e29b-41d4-a716-446655440000"

        def validate_many():
            for _ in range(1000):
                validate_uuid(valid_uuid)

        benchmark(validate_many)

    def test_field_copy_performance(self, benchmark):
        """Benchmark field copying"""
        field = Field(
            name="test",
            annotation=str,
            default="value",
            title="Test",
            description="Description",
        )

        def copy_many():
            for i in range(1000):
                field.copy(name=f"field_{i}")

        benchmark(copy_many)

    def test_model_creation_performance(self, benchmark):
        """Benchmark dynamic model creation"""
        fields = [
            ID_FROZEN.copy(name="id"),
            Field(name="name", annotation=str),
            Field(name="value", annotation=float),
        ]

        def create_many():
            for i in range(100):
                Model = create_model(f"Model_{i}", fields=fields)
                Model(name="test", value=1.0)

        benchmark(create_many)


# ============================================
# Integration Tests
# ============================================


class TestFieldIntegration:
    """Test field system integration scenarios"""

    def test_complete_model_workflow(self):
        """Test a complete workflow from fields to model instance"""
        # Define fields for a user model
        fields = [
            ID_FROZEN.copy(name="user_id"),
            Field(
                name="email",
                annotation=str,
                validator=lambda cls, v: v if "@" in v else ValueError("Invalid email"),
            ),
            DATETIME.copy(name="created_at"),
            Field(name="metadata", annotation=dict, default_factory=dict),
            EMBEDDING.copy(name="profile_embedding"),
        ]

        # Create model
        UserModel = create_model("User", fields=fields)

        # Create instance
        user = UserModel(email="user@example.com", profile_embedding=[1.0, 2.0, 3.0])

        # Verify all fields work correctly
        assert isinstance(user.user_id, UUID)
        assert user.email == "user@example.com"
        assert isinstance(user.created_at, datetime)
        assert user.metadata == {}
        assert user.profile_embedding == [1.0, 2.0, 3.0]

        # Test serialization
        user_dict = user.model_dump()
        assert "user_id" in user_dict
        assert "created_at" in user_dict

        # Test JSON serialization
        user_json = user.model_dump_json()
        assert isinstance(user_json, str)

    def test_field_inheritance_pattern(self):
        """Test creating specialized fields from base fields"""
        # Create specialized email field
        email_field = Field(
            name="email",
            annotation=str,
            validator=lambda cls, v: v if "@" in v else ValueError("Invalid email"),
            title="Email Address",
            description="User's email for communication",
        )

        # Create variations
        optional_email = email_field.as_nullable()
        email_list = email_field.as_listable()

        # Create models with variations
        Model1 = create_model("Model1", fields=[email_field])
        Model2 = create_model("Model2", fields=[optional_email])
        Model3 = create_model("Model3", fields=[email_list])

        # Test each variation
        m1 = Model1(email="test@example.com")
        assert m1.email == "test@example.com"

        m2 = Model2(email=None)
        assert m2.email is None

        m3 = Model3(email=["test1@example.com", "test2@example.com"])
        assert len(m3.email) == 2


# ============================================
# Hypothesis Property Tests
# ============================================


@composite
def field_strategy(draw):
    """Generate random Field objects for property testing"""
    name = draw(
        st.text(min_size=1, max_size=20, alphabet=st.characters(categories=["L", "N"]))
    )
    annotation = draw(st.sampled_from([str, int, float, bool, list, dict]))
    has_default = draw(st.booleans())

    field_kwargs = {
        "name": name,
        "annotation": annotation,
    }

    if has_default:
        if annotation is str:
            field_kwargs["default"] = draw(st.text())
        elif annotation is int:
            field_kwargs["default"] = draw(st.integers())
        elif annotation is float:
            field_kwargs["default"] = draw(st.floats(allow_nan=False))
        elif annotation is bool:
            field_kwargs["default"] = draw(st.booleans())

    return Field(**field_kwargs)


class TestPropertyBased:
    """Property-based tests for field system"""

    @given(field_strategy())
    def test_field_copy_preserves_properties(self, field):
        """Copying a field should preserve all properties"""
        copy = field.copy()
        assert copy.name == field.name
        assert copy.annotation == field.annotation
        assert copy.default == field.default
        assert copy.default_factory == field.default_factory

    @given(field_strategy())
    def test_field_nullable_is_idempotent(self, field):
        """Making a field nullable twice should be idempotent"""
        nullable1 = field.as_nullable()
        nullable2 = nullable1.as_nullable()

        # Should have same properties
        assert nullable1.annotation == nullable2.annotation
        assert nullable1.default == nullable2.default

    @given(st.lists(field_strategy(), min_size=1, max_size=10))
    def test_model_creation_never_fails(self, fields):
        """Creating a model from any valid fields should not crash"""
        # Ensure unique field names
        seen_names = set()
        unique_fields = []
        for field in fields:
            if field.name not in seen_names:
                seen_names.add(field.name)
                unique_fields.append(field)

        assume(len(unique_fields) > 0)

        try:
            Model = create_model("TestModel", fields=unique_fields)
            assert Model is not None
            assert hasattr(Model, "model_fields")
        except Exception as e:
            pytest.fail(f"Model creation failed: {e}")


# ============================================
# Test Configuration
# ============================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--benchmark-only"])
