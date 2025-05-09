from typing import List, Optional

import pytest
from pydantic import BaseModel, Field
from sqlalchemy import ForeignKey, Integer, String, inspect
from sqlalchemy.orm import DeclarativeBase, relationship

from pydapter.exceptions import TypeConversionError
from pydapter.model_adapters.sql_model import SQLModelAdapter


def test_register_type_mapping():
    """Test registering custom type mappings."""
    from sqlalchemy import CHAR

    # Register a custom type mapping
    SQLModelAdapter.register_type_mapping(
        python_type=bool,
        sql_type_factory=lambda: CHAR(1),
        python_to_sql=lambda x: "Y" if x else "N",
        sql_to_python=lambda x: x == "Y",
    )

    # Create a model with the custom type
    class CustomBoolSchema(BaseModel):
        id: Optional[int] = None
        flag: bool

    # Convert to SQLAlchemy model
    CustomSQL = SQLModelAdapter.pydantic_model_to_sql(CustomBoolSchema)

    # Verify custom type mapping
    mapper = inspect(CustomSQL)
    flag_col = mapper.columns["flag"]
    assert isinstance(flag_col.type, CHAR)
    assert flag_col.type.length == 1
    # Clean up by restoring original mapping
    from sqlalchemy import Boolean

    SQLModelAdapter.register_type_mapping(
        python_type=bool, sql_type_factory=lambda: Boolean()
    )


@pytest.mark.skip("Relationship handling needs more complex changes")
def test_one_to_one_relationship():
    """Test one-to-one relationship handling."""

    class User(BaseModel):
        id: Optional[int] = None
        name: str
        profile: Optional["Profile"] = Field(
            None,
            json_schema_extra={
                "relationship": {"type": "one_to_one", "back_populates": "user"}
            },
        )

    class Profile(BaseModel):
        id: Optional[int] = None
        bio: str
        user: Optional[User] = Field(
            None,
            json_schema_extra={
                "relationship": {"type": "one_to_one", "back_populates": "profile"}
            },
        )

    # Update forward references
    User.model_rebuild()
    Profile.model_rebuild()

    # Convert to SQLAlchemy models
    UserSQL = SQLModelAdapter.pydantic_model_to_sql(User)
    ProfileSQL = SQLModelAdapter.pydantic_model_to_sql(Profile)

    # Verify relationship in User model
    user_mapper = inspect(UserSQL)
    assert hasattr(UserSQL, "profile")
    assert user_mapper.relationships["profile"].direction.name == "ONETOMANY"
    assert not user_mapper.relationships["profile"].uselist

    # Verify relationship in Profile model
    profile_mapper = inspect(ProfileSQL)
    assert hasattr(ProfileSQL, "user")
    assert profile_mapper.relationships["user"].direction.name == "MANYTOONE"
    assert not profile_mapper.relationships["user"].uselist


@pytest.mark.skip("Relationship handling needs more complex changes")
def test_one_to_many_relationship():
    """Test one-to-many relationship handling."""

    class Author(BaseModel):
        id: Optional[int] = None
        name: str
        books: List["Book"] = Field(
            default_factory=list,
            json_schema_extra={
                "relationship": {"type": "one_to_many", "back_populates": "author"}
            },
        )

    class Book(BaseModel):
        id: Optional[int] = None
        title: str
        author_id: Optional[int] = None
        author: Optional[Author] = Field(
            None,
            json_schema_extra={
                "relationship": {"type": "many_to_one", "back_populates": "books"}
            },
        )

    # Update forward references
    Author.model_rebuild()
    Book.model_rebuild()

    # Convert to SQLAlchemy models
    AuthorSQL = SQLModelAdapter.pydantic_model_to_sql(Author)
    BookSQL = SQLModelAdapter.pydantic_model_to_sql(Book)

    # Verify relationship in Author model
    author_mapper = inspect(AuthorSQL)
    assert hasattr(AuthorSQL, "books")
    assert author_mapper.relationships["books"].direction.name == "ONETOMANY"
    assert author_mapper.relationships["books"].uselist

    # Verify relationship in Book model
    book_mapper = inspect(BookSQL)
    assert hasattr(BookSQL, "author")
    assert book_mapper.relationships["author"].direction.name == "MANYTOONE"
    assert not book_mapper.relationships["author"].uselist
    assert hasattr(BookSQL, "author_id")
    assert isinstance(book_mapper.columns["author_id"].type, Integer)
    assert book_mapper.columns["author_id"].foreign_keys


def test_error_handling_with_pydapter_exceptions():
    """Test error handling with pydapter exceptions."""

    class UnsupportedSchema(BaseModel):
        id: Optional[int] = None
        complex_val: complex  # Not supported

    with pytest.raises(TypeConversionError) as excinfo:
        SQLModelAdapter.pydantic_model_to_sql(UnsupportedSchema)

    # Verify exception details
    assert "Unsupported type" in str(excinfo.value)
    assert excinfo.value.source_type is complex
    assert excinfo.value.field_name == "complex_val"
    assert excinfo.value.model_name == "UnsupportedSchema"


def test_pydantic_v2_compatibility():
    """Test Pydantic v2 compatibility."""

    class UserSchema(BaseModel):
        id: Optional[int] = None
        name: str
        email: Optional[str] = None

    # Convert to SQLAlchemy model
    UserSQL = SQLModelAdapter.pydantic_model_to_sql(UserSchema)

    # Convert back to Pydantic model
    UserSchemaRT = SQLModelAdapter.sql_model_to_pydantic(UserSQL)

    # Check Pydantic v2 compatibility
    assert UserSchemaRT.model_config.get("from_attributes") is True
    assert UserSchemaRT.model_config.get("orm_mode") is True  # Backward compatibility
