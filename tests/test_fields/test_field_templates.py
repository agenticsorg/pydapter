import uuid
from datetime import datetime
from typing import Annotated, Union

import pytest
from pydantic import Field as PydanticField
from pydantic import ValidationError
from pydapter.fields import (
    CREATED_AT_TEMPLATE,
    CREATED_AT_TZ_TEMPLATE,
    DELETED_AT_TEMPLATE,
    EMAIL_TEMPLATE,
    ID_TEMPLATE,
    NAME_TEMPLATE,
    PERCENTAGE_TEMPLATE,
    POSITIVE_INT_TEMPLATE,
    UPDATED_AT_TEMPLATE,
    USERNAME_TEMPLATE,
    Field,
    FieldTemplate,
    create_model,
)


class TestFieldTemplate:
    def test_basic_template_creation(self):
        """Test creating a basic field template."""
        template = FieldTemplate(
            base_type=str,
            description="Test string field",
            default="default_value",
        )

        field = template.create_field("test_field")
        assert field.name == "test_field"
        assert field.annotation is str
        assert field.description == "Test string field"
        assert field.default == "default_value"

    def test_template_with_annotated_type(self):
        """Test template with Annotated type."""
        template = FieldTemplate(
            base_type=Annotated[str, PydanticField(min_length=5, max_length=10)],
            description="Length-constrained string",
        )

        field = template.create_field("constrained_field")
        assert field.name == "constrained_field"
        # Check that annotation is preserved
        assert hasattr(field.annotation, "__metadata__")

    def test_template_with_validator(self):
        """Test template with custom validator."""

        def uppercase_validator(cls, v):
            return v.upper()

        template = FieldTemplate(
            base_type=str,
            validator=uppercase_validator,
        )

        field = template.create_field("uppercase_field")
        assert field.validator == uppercase_validator

    def test_template_copy(self):
        """Test copying a template with modifications."""
        original = FieldTemplate(
            base_type=int,
            description="Original description",
            default=0,
        )

        copied = original.copy(description="Modified description", default=10)

        # Original unchanged
        original_field = original.create_field("field1")
        assert original_field.description == "Original description"
        assert original_field.default == 0

        # Copy has modifications
        copied_field = copied.create_field("field2")
        assert copied_field.description == "Modified description"
        assert copied_field.default == 10

    def test_as_nullable(self):
        """Test creating nullable version of template."""
        template = FieldTemplate(
            base_type=int,
            description="Integer field",
            default=42,
        )

        nullable_template = template.as_nullable()
        field = nullable_template.create_field("nullable_int")

        # Check type is Union[int, None]
        assert field.default is None
        # Annotation should be Union type
        assert (
            Union[int, None] == field.annotation
            or field.annotation == Union[int, type(None)]
        )

    def test_as_nullable_with_validator(self):
        """Test nullable template preserves validator for non-None values."""

        def positive_validator(cls, v):
            if v <= 0:
                raise ValueError("Must be positive")
            return v

        template = FieldTemplate(
            base_type=int,
            validator=positive_validator,
        )

        nullable_template = template.as_nullable()
        field = nullable_template.create_field("nullable_positive")

        # Create a model to test validation
        TestModel = create_model("TestModel", fields={"nullable_positive": field})

        # None should be valid
        instance = TestModel(nullable_positive=None)
        assert instance.nullable_positive is None

        # Positive value should be valid
        instance = TestModel(nullable_positive=5)
        assert instance.nullable_positive == 5

        # Negative value should fail
        with pytest.raises(ValidationError):
            TestModel(nullable_positive=-5)

    def test_as_listable_strict(self):
        """Test creating strict listable version of template."""
        template = FieldTemplate(
            base_type=str,
            description="String field",
        )

        listable_template = template.as_listable(strict=True)
        field = listable_template.create_field("string_list")

        # Annotation should be list[str]
        assert field.annotation == list[str]

    def test_as_listable_flexible(self):
        """Test creating flexible listable version of template."""
        template = FieldTemplate(
            base_type=int,
            description="Integer field",
        )

        listable_template = template.as_listable(strict=False)
        field = listable_template.create_field("int_or_list")

        # Annotation should be Union[list[int], int]
        origin = getattr(field.annotation, "__origin__", None)
        assert origin is Union

    def test_field_override_in_create_field(self):
        """Test overriding field properties when creating from template."""
        template = FieldTemplate(
            base_type=str,
            description="Original description",
            default="original",
            frozen=False,
        )

        field = template.create_field(
            "overridden_field",
            description="Overridden description",
            default="overridden",
            frozen=True,
        )

        assert field.description == "Overridden description"
        assert field.default == "overridden"
        assert field.frozen is True


class TestCommonTemplates:
    def test_id_template(self):
        """Test ID template creates proper UUID field."""
        field = ID_TEMPLATE.create_field("id")
        assert field.annotation == uuid.UUID
        assert field.description == "Unique identifier"
        assert callable(field.default_factory)

        # Test default factory creates UUIDs
        value1 = field.default_factory()
        value2 = field.default_factory()
        assert isinstance(value1, uuid.UUID)
        assert isinstance(value2, uuid.UUID)
        assert value1 != value2

    def test_email_template(self):
        """Test email template with validation."""
        # Skip if email-validator is not installed
        try:
            TestModel = create_model("TestModel", fields={"email": EMAIL_TEMPLATE})

            # Valid email
            instance = TestModel(email="TEST@EXAMPLE.COM")
            assert (
                instance.email == "TEST@example.com"
            )  # EmailStr normalizes domain only

            # Invalid email
            with pytest.raises(ValidationError):
                TestModel(email="not-an-email")
        except ImportError:
            pytest.skip("email-validator not installed")

    def test_username_template(self):
        """Test username template with validation."""
        TestModel = create_model("TestModel", fields={"username": USERNAME_TEMPLATE})

        # Valid usernames
        assert TestModel(username="user123").username == "user123"
        assert TestModel(username="test_user").username == "test_user"
        assert TestModel(username="user-name").username == "user-name"

        # Invalid usernames - constr validation happens at the Pydantic level
        # The pattern should catch these
        with pytest.raises(ValidationError):
            TestModel(username="ab")  # Too short

        with pytest.raises(ValidationError):
            TestModel(username="a" * 33)  # Too long

        with pytest.raises(ValidationError):
            TestModel(username="user@name")  # Invalid character

    def test_datetime_templates(self):
        """Test datetime templates."""
        from pydantic import AwareDatetime, NaiveDatetime

        # Test naive datetime templates
        created_field = CREATED_AT_TEMPLATE.create_field("created_at")
        updated_field = UPDATED_AT_TEMPLATE.create_field("updated_at")
        deleted_field = DELETED_AT_TEMPLATE.create_field("deleted_at")

        assert created_field.annotation == NaiveDatetime
        assert created_field.frozen is True
        assert callable(created_field.default_factory)

        assert updated_field.annotation == NaiveDatetime
        assert updated_field.frozen is not True

        # Deleted should be nullable
        assert deleted_field.default is None

        # Test timezone-aware datetime templates
        created_tz_field = CREATED_AT_TZ_TEMPLATE.create_field("created_at")
        assert created_tz_field.annotation == AwareDatetime
        assert callable(created_tz_field.default_factory)

    def test_numeric_templates(self):
        """Test numeric templates with constraints."""
        TestModel = create_model(
            "TestModel",
            fields={
                "positive_int": POSITIVE_INT_TEMPLATE,
                "percentage": PERCENTAGE_TEMPLATE,
            },
        )

        # Valid values
        instance = TestModel(positive_int=5, percentage=50.0)
        assert instance.positive_int == 5
        assert instance.percentage == 50.0

        # Invalid positive int - conint validation
        with pytest.raises(ValidationError):
            TestModel(positive_int=0, percentage=50.0)

        # Invalid percentage - confloat validation
        with pytest.raises(ValidationError):
            TestModel(positive_int=5, percentage=101.0)


class TestCreateModelWithTemplates:
    def test_create_model_with_templates_dict(self):
        """Test creating model with dictionary of templates."""
        # Use templates that don't require external validators
        UserModel = create_model(
            "UserModel",
            fields={
                "id": ID_TEMPLATE,
                "username": USERNAME_TEMPLATE,
                "name": NAME_TEMPLATE,
                "created_at": CREATED_AT_TEMPLATE,
                "deleted_at": DELETED_AT_TEMPLATE,
            },
        )

        # Create instance
        user = UserModel(
            username="testuser",
            name="Test User",
        )

        assert isinstance(user.id, uuid.UUID)
        assert user.username == "testuser"
        assert user.name == "Test User"
        assert isinstance(user.created_at, datetime)
        assert user.deleted_at is None

    def test_create_model_with_mixed_fields_and_templates(self):
        """Test creating model with mix of Field and FieldTemplate."""
        custom_field = Field(
            name="custom",
            annotation=str,
            description="Custom field",
            default="custom_default",
        )

        MixedModel = create_model(
            "MixedModel",
            fields={
                "id": ID_TEMPLATE,
                "custom": custom_field,
                "percentage": PERCENTAGE_TEMPLATE,
            },
        )

        instance = MixedModel()
        assert isinstance(instance.id, uuid.UUID)
        assert instance.custom == "custom_default"
        assert instance.percentage == 0.0

    def test_create_model_with_template_overrides(self):
        """Test that field name from dict key overrides template."""
        # Create a template-based field with different name
        ProductModel = create_model(
            "ProductModel",
            fields={
                "product_id": ID_TEMPLATE,  # Using different name
                "product_name": NAME_TEMPLATE,
            },
        )

        # Field names should match dict keys
        fields = ProductModel.model_fields
        assert "product_id" in fields
        assert "product_name" in fields
        assert "id" not in fields
        assert "name" not in fields


class TestAdvancedTemplateFeatures:
    def test_nested_nullable_listable(self):
        """Test combining nullable and listable transformations."""
        template = FieldTemplate(
            base_type=str,
            description="String field",
        )

        # Create nullable, then listable
        nullable_listable = template.as_nullable().as_listable()
        field = nullable_listable.create_field("test_field")

        TestModel = create_model("TestModel", fields={"test_field": field})

        # Test various valid inputs
        assert TestModel(test_field=None).test_field is None
        assert TestModel(test_field=["a", "b"]).test_field == ["a", "b"]
        assert TestModel(test_field="single").test_field == "single"

    def test_template_with_complex_validator_wrapping(self):
        """Test that complex validators are properly wrapped."""
        call_count = {"validator": 0, "nullable": 0, "listable": 0}

        def counting_validator(cls, v):
            call_count["validator"] += 1
            if not v.startswith("valid_"):
                raise ValueError("Must start with 'valid_'")
            return v

        template = FieldTemplate(
            base_type=str,
            validator=counting_validator,
        )

        # Make it nullable and listable
        complex_template = template.as_nullable().as_listable()

        TestModel = create_model(
            "TestModel", fields={"complex": complex_template.create_field("complex")}
        )

        # Test None (should not call validator)
        instance = TestModel(complex=None)
        assert instance.complex is None
        assert call_count["validator"] == 0

        # Test single value
        instance = TestModel(complex="valid_single")
        assert instance.complex == "valid_single"
        assert call_count["validator"] == 1

        # Test list
        instance = TestModel(complex=["valid_1", "valid_2"])
        assert instance.complex == ["valid_1", "valid_2"]
        assert call_count["validator"] == 3  # 1 from before + 2 new

        # Test invalid in list
        with pytest.raises(ValidationError):
            TestModel(complex=["valid_1", "invalid"])


def test_field_template_immutability():
    """Test that field templates respect immutability settings."""
    template = FieldTemplate(
        base_type=str,
        immutable=True,
    )

    field = template.create_field("immutable_field")
    assert field.immutable is True

    # Test that Field's immutability works
    with pytest.raises(AttributeError):
        field.name = "new_name"


def test_field_name_validation():
    """Test that field names must be valid Python identifiers."""
    template = FieldTemplate(base_type=str)

    # Valid names
    assert template.create_field("valid_name").name == "valid_name"
    assert template.create_field("_private").name == "_private"
    assert template.create_field("name123").name == "name123"

    # Invalid names
    with pytest.raises(ValueError) as excinfo:
        template.create_field("123invalid")
    assert "not a valid Python identifier" in str(excinfo.value)

    with pytest.raises(ValueError) as excinfo:
        template.create_field("invalid-name")
    assert "not a valid Python identifier" in str(excinfo.value)

    with pytest.raises(ValueError) as excinfo:
        template.create_field("invalid name")
    assert "not a valid Python identifier" in str(excinfo.value)


def test_frozen_field_validation():
    """Test that frozen fields cannot be made mutable."""
    frozen_template = FieldTemplate(base_type=str, frozen=True)

    # Can't override frozen=True with frozen=False
    with pytest.raises(RuntimeError) as excinfo:
        frozen_template.create_field("test_field", frozen=False)
    assert "Cannot override frozen=True" in str(excinfo.value)

    # Can keep it frozen or not specify
    field1 = frozen_template.create_field("field1", frozen=True)
    assert field1.frozen is True

    field2 = frozen_template.create_field("field2")  # No override
    assert field2.frozen is True


def test_default_and_default_factory_validation():
    """Test that a field cannot have both default and default_factory."""
    # Template with default
    template1 = FieldTemplate(base_type=str, default="template_default")

    # Override with default_factory should fail
    with pytest.raises(ValueError) as excinfo:
        template1.create_field("field1", default_factory=lambda: "factory")
    assert "cannot have both 'default' and 'default_factory'" in str(excinfo.value)

    # Template with default_factory
    template2 = FieldTemplate(base_type=list, default_factory=list)

    # Override with default should fail
    with pytest.raises(ValueError) as excinfo:
        template2.create_field("field2", default=[])
    assert "cannot have both 'default' and 'default_factory'" in str(excinfo.value)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
