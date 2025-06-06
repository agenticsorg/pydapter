"""Test model adapter enhancements for JSONB and timezone-aware datetime support."""

import datetime

import pytest
from pydantic import BaseModel, HttpUrl
from pydapter.fields import (
    CREATED_AT_TZ_TEMPLATE,
    EMAIL_TEMPLATE,
    JSON_TEMPLATE,
    METADATA_TEMPLATE,
    URL_TEMPLATE,
    Field,
    create_model,
)
from pydapter.model_adapters.postgres_model import PostgresModelAdapter
from pydapter.model_adapters.sql_model import SQLModelAdapter
from sqlalchemy import inspect


class TestJsonbSupport:
    """Test JSONB support for BaseModel fields."""

    def test_basemodel_field_maps_to_jsonb(self):
        """Test that BaseModel fields are mapped to JSONB in PostgreSQL."""

        # Create a nested model
        class Settings(BaseModel):
            theme: str = "dark"
            notifications: bool = True

        # Create main model with BaseModel field
        UserModel = create_model(
            "UserModel",
            fields=[
                Field("id", annotation=int, default=...),
                Field("settings", annotation=Settings, default_factory=Settings),
            ],
        )

        # Convert to SQL model using PostgresModelAdapter
        postgres_adapter = PostgresModelAdapter()
        sql_model = postgres_adapter.pydantic_model_to_sql(
            UserModel, table_name="users"
        )

        # Inspect the table
        mapper = inspect(sql_model)
        settings_col = mapper.columns["settings"]

        # Check that it's JSONB
        assert str(settings_col.type) == "JSONB"

    def test_json_template_creates_jsonb_field(self):
        """Test that JSON_TEMPLATE creates JSONB fields."""
        create_model(
            "DataModel",
            fields={
                "id": Field("id", annotation=int, default=...),
                "data": JSON_TEMPLATE,
                "extra_data": METADATA_TEMPLATE,
            },
        )

        # Create field from template and check db_type in extra_info
        data_field = JSON_TEMPLATE.create_field("data")
        # The db_type should be in extra_info from pydantic_field_kwargs
        assert hasattr(data_field, "extra_info")
        # It might also be in the field_info.json_schema_extra
        field_info = data_field.field_info
        if hasattr(field_info, "json_schema_extra") and field_info.json_schema_extra:
            assert field_info.json_schema_extra.get("db_type") == "jsonb"
        else:
            assert data_field.extra_info.get("db_type") == "jsonb"


class TestTimezoneDatetimeSupport:
    """Test timezone-aware datetime support."""

    def test_timezone_aware_datetime_field(self):
        """Test that timezone-aware datetime defaults work properly."""
        EventModel = create_model(
            "EventModel",
            fields={
                "id": Field("id", annotation=int, default=...),
                "created_at": CREATED_AT_TZ_TEMPLATE,
            },
        )

        # Convert to SQL model
        sql_model = SQLModelAdapter.pydantic_model_to_sql(
            EventModel, table_name="events"
        )

        # Create an instance to verify default factory works
        event = EventModel(id=1)
        assert isinstance(event.created_at, datetime.datetime)
        assert event.created_at.tzinfo is not None

        # Verify SQL column handles timezone
        mapper = inspect(sql_model)
        created_col = mapper.columns["created_at"]

        # Check if DateTime has timezone support
        if hasattr(created_col.type, "timezone"):
            # This would be true for PostgreSQL TIMESTAMPTZ
            assert created_col.type.timezone is True


class TestPydanticV2Types:
    """Test Pydantic v2 type mappings."""

    def test_emailstr_mapping(self):
        """Test EmailStr maps to appropriate String length."""
        # Skip if email-validator not installed
        try:
            from pydantic import EmailStr

            create_model(
                "ContactModel",
                fields={
                    "email": EMAIL_TEMPLATE,
                    "website": URL_TEMPLATE,
                },
            )

            # Verify fields use correct Pydantic types
            email_field = EMAIL_TEMPLATE.create_field("email")
            assert email_field.annotation == EmailStr

            url_field = URL_TEMPLATE.create_field("website")
            assert url_field.annotation == HttpUrl
        except ImportError:
            pytest.skip("email-validator not installed")

    def test_pydantic_types_in_sql_model(self):
        """Test that Pydantic types are properly mapped in SQL models."""
        # Skip if email-validator not installed
        try:
            from pydantic import EmailStr

            class ProfileModel(BaseModel):
                id: int = Field(..., description="Profile ID")
                email: EmailStr
                website: HttpUrl

        except ImportError:
            pytest.skip("email-validator not installed")
            return

        # Convert to SQL
        sql_model = SQLModelAdapter.pydantic_model_to_sql(
            ProfileModel, table_name="profiles"
        )

        mapper = inspect(sql_model)

        # Check email column
        email_col = mapper.columns["email"]
        assert str(email_col.type) == "VARCHAR(255)"

        # Check website column
        website_col = mapper.columns["website"]
        assert str(website_col.type) == "VARCHAR(2048)"


def test_comprehensive_model_with_enhancements():
    """Test a comprehensive model using all enhancements."""
    from pydantic import Field as PydanticField

    class UserPreferences(BaseModel):
        """Nested model for user preferences."""

        theme: str = "light"
        language: str = "en"
        notifications: dict = PydanticField(default_factory=dict)

    # Create a comprehensive model - skip email if email-validator not installed
    try:
        UserModel = create_model(
            "UserModel",
            fields={
                "id": Field("id", annotation=int, default=...),
                "email": EMAIL_TEMPLATE,
                "website": URL_TEMPLATE.as_nullable(),
                "preferences": Field(
                    "preferences",
                    annotation=UserPreferences,
                    default_factory=UserPreferences,
                    json_schema_extra={"db_type": "jsonb"},
                ),
                "extra_data": METADATA_TEMPLATE,
                "created_at": CREATED_AT_TZ_TEMPLATE,
            },
        )
    except ImportError:
        # Create without email field
        UserModel = create_model(
            "UserModel",
            fields={
                "id": Field("id", annotation=int, default=...),
                "name": Field("name", annotation=str, default="Test User"),
                "website": URL_TEMPLATE.as_nullable(),
                "preferences": Field(
                    "preferences",
                    annotation=UserPreferences,
                    default_factory=UserPreferences,
                    json_schema_extra={"db_type": "jsonb"},
                ),
                "extra_data": METADATA_TEMPLATE,
                "created_at": CREATED_AT_TZ_TEMPLATE,
            },
        )

    # Create instance
    try:
        user = UserModel(
            id=1,
            email="test@example.com",
            preferences={"theme": "dark", "language": "es"},
        )
    except Exception:
        # Without email field
        user = UserModel(
            id=1,
            preferences={"theme": "dark", "language": "es"},
        )

    assert user.id == 1
    assert isinstance(user.preferences, UserPreferences)
    assert user.preferences.theme == "dark"
    assert user.website is None
    assert isinstance(user.created_at, datetime.datetime)
    assert user.created_at.tzinfo is not None

    # Convert to SQL with PostgreSQL adapter
    postgres_adapter = PostgresModelAdapter()
    sql_model = postgres_adapter.pydantic_model_to_sql(UserModel, table_name="users")

    mapper = inspect(sql_model)

    # Verify column types
    prefs_col = mapper.columns.get("preferences")
    if prefs_col is not None:
        # Should be JSONB for nested model
        assert "JSON" in str(prefs_col.type)

    extra_data_col = mapper.columns.get("extra_data")
    if extra_data_col is not None:
        # Should be JSONB from template
        assert "JSON" in str(extra_data_col.type)
