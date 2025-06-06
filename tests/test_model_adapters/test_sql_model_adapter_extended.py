from datetime import date, time
from typing import Any, Optional, Union

import pytest
from pydantic import BaseModel, Field
from pydapter.exceptions import TypeConversionError
from pydapter.model_adapters.sql_model import SQLModelAdapter, create_base
from pydapter.model_adapters.type_registry import TypeRegistry
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Integer,
    LargeBinary,
    String,
    Time,
)


class UserSchema(BaseModel):
    id: int | None = None
    name: str
    email: str
    is_active: bool = True
    age: int | None = None


class UserWithRelationship(BaseModel):
    id: int | None = None
    name: str
    email: str
    posts: list[dict[str, Any]] = Field(
        default_factory=list,
        json_schema_extra={
            "relationship": {
                "type": "one_to_many",
                "model": "Post",
                "back_populates": "author",
            }
        },
    )


class PostSchema(BaseModel):
    id: int | None = None
    title: str
    content: str
    author_id: int | None = None
    author: dict[str, Any] | None = Field(
        None,
        json_schema_extra={
            "relationship": {
                "type": "many_to_one",
                "model": "User",
                "back_populates": "posts",
            }
        },
    )


def test_create_base():
    """Test the create_base function."""
    Base = create_base()
    assert hasattr(Base, "metadata")
    assert Base.metadata.schema == "public"  # SQLAlchemy uses 'schema', not 'db_schema'


def test_register_type_mapping():
    """Test registering custom type mappings."""

    # Define a custom Python type
    class CustomType:
        pass

    # Define a custom SQL type
    class CustomSQLType:
        pass

    # Register the mapping
    SQLModelAdapter.register_type_mapping(
        python_type=CustomType,
        sql_type_factory=lambda: CustomSQLType(),
        python_to_sql=lambda value: str(value),
        sql_to_python=lambda _: CustomType(),
    )

    # Verify the mapping was registered
    assert TypeRegistry.get_sql_type(CustomType) is not None

    # Clean up
    TypeRegistry._PY_TO_SQL.pop(CustomType, None)
    TypeRegistry._PY_TO_SQL_CONVERTERS.pop(CustomType, None)
    TypeRegistry._SQL_TO_PY_CONVERTERS.pop(CustomSQLType, None)


def test_pydantic_model_to_sql_with_relationships():
    """Test converting a Pydantic model with relationships to SQLAlchemy."""
    # Convert the model with relationships
    UserSQL = SQLModelAdapter.pydantic_model_to_sql(UserWithRelationship)

    # Check that the relationship was created
    assert hasattr(UserSQL, "posts")

    # Convert the related model
    PostSQL = SQLModelAdapter.pydantic_model_to_sql(PostSchema)

    # Check that the relationship and foreign key were created
    assert hasattr(PostSQL, "author")
    assert hasattr(PostSQL, "author_id")


def test_handle_relationship():
    """Test the handle_relationship method."""
    # Create a field with relationship metadata
    field_info = PostSchema.model_fields["author"]

    # Call handle_relationship
    result = SQLModelAdapter.handle_relationship(PostSchema, "author", field_info)

    # Check the result
    assert "relationship" in result
    assert "foreign_key" in result
    assert result["foreign_key_name"] == "author_id"

    # Test with a field that has no relationship metadata
    field_info = UserSchema.model_fields["name"]
    result = SQLModelAdapter.handle_relationship(UserSchema, "name", field_info)
    assert result == {}


def test_is_optional():
    """Test the is_optional method."""
    # Test with Union type (Optional[str])
    assert SQLModelAdapter.is_optional(Optional[str])

    # Test with pipe syntax (str | None)
    assert SQLModelAdapter.is_optional(str | None)

    # Test with non-optional type
    assert not SQLModelAdapter.is_optional(str)

    # Test with Union that doesn't include None
    assert not SQLModelAdapter.is_optional(Union[str, int])


def test_sql_model_to_pydantic_with_mock():
    """Test sql_model_to_pydantic with a mock ORM class."""

    # Create a mock ORM class with columns
    class MockColumn:
        def __init__(self, key, type_, nullable=False, primary_key=False, default=None):
            self.key = key
            self.type = type_
            self.nullable = nullable
            self.primary_key = primary_key
            self.default = default
            # Only set is_scalar if default is an object with appropriate attributes
            if default and hasattr(default, "is_scalar"):
                self.default.is_scalar = True
                self.default.arg = "default_value"

    # Create a mock default object
    class MockDefault:
        def __init__(self):
            self.is_scalar = True
            self.arg = "default_value"

    mock_default = MockDefault()

    class MockORM:
        __name__ = "MockORM"
        columns = [
            MockColumn("id", Integer(), primary_key=True),
            MockColumn("name", String(), nullable=False),
            MockColumn("email", String(), nullable=False),
            MockColumn("is_active", Boolean(), nullable=False, default=mock_default),
        ]

    # Convert to Pydantic
    result = SQLModelAdapter.sql_model_to_pydantic(MockORM)

    # Check the result
    assert result.__name__ == "MockORMSchema"
    assert "id" in result.model_fields
    assert "name" in result.model_fields
    assert "email" in result.model_fields
    assert "is_active" in result.model_fields
    assert result.model_config["from_attributes"] is True
    assert result.model_config["orm_mode"] is True


def test_python_type_for_basic():
    """Test the _python_type_for method with basic types."""
    # Create real SQLAlchemy columns for testing
    int_column = Column("id", Integer())
    bool_column = Column("is_active", Boolean())
    date_column = Column("birth_date", Date())
    datetime_column = Column("created_at", DateTime())
    time_column = Column("start_time", Time())
    binary_column = Column("data", LargeBinary())

    # Test each column
    assert SQLModelAdapter._python_type_for(int_column) is int
    assert SQLModelAdapter._python_type_for(bool_column) is bool
    assert SQLModelAdapter._python_type_for(date_column) is date
    # DateTime might be mapped to NaiveDatetime due to Pydantic registrations
    datetime_type = SQLModelAdapter._python_type_for(datetime_column)
    assert datetime_type is not None and isinstance(datetime_type, type)
    assert SQLModelAdapter._python_type_for(time_column) is time
    assert SQLModelAdapter._python_type_for(binary_column) is bytes


def test_python_type_for_error_handling():
    """Test error handling in _python_type_for method."""

    # Create a custom column class for testing
    class CustomColumn:
        def __init__(self):
            self.type = type("UnsupportedType", (), {})

    # Create a column with unsupported type
    custom_column = CustomColumn()

    # This should raise a TypeConversionError
    with pytest.raises(TypeConversionError):
        SQLModelAdapter._python_type_for(custom_column)
