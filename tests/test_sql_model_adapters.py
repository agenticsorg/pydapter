import typing as t
from datetime import date, datetime, time
from uuid import UUID

import pytest
from pydantic import BaseModel
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    Integer,
    LargeBinary,
    String,
    Time,
    inspect,
)

from pydapter.exceptions import TypeConversionError
from pydapter.model_adapters.sql_model import SQLModelAdapter


# ---------- Sample Pydantic models for testing -------------------------------------------
class UserSchema(BaseModel):
    id: t.Optional[int] = None  # PK should become autoincrement
    name: str
    email: t.Optional[str] = None  # nullable
    active: bool = True  # server default simulated
    signup_ts: t.Optional[datetime] = None


class CompleteTypeSchema(BaseModel):
    """Model with all supported scalar types for comprehensive testing"""

    id: t.Optional[int] = None
    int_val: int = 42
    float_val: float = 3.14
    bool_val: bool = True
    str_val: str = "default"
    bytes_val: bytes = b"binary"
    datetime_val: datetime = datetime(2025, 1, 1)
    date_val: date = date(2025, 1, 1)
    time_val: time = time(12, 0, 0)
    uuid_val: t.Optional[UUID] = None


# ---------- Tests for SQLModelAdapter ----------------------------------------------------
def test_pydantic_to_sql_scalar_mapping():
    """Test conversion from Pydantic model to SQLAlchemy model with scalar types"""
    UserSQL = SQLModelAdapter.pydantic_model_to_sql(UserSchema)

    mapper = inspect(UserSQL)
    cols = {c.key: c for c in mapper.columns}

    # column presence & types
    assert isinstance(cols["id"].type, Integer)
    assert cols["id"].primary_key and cols["id"].autoincrement
    assert isinstance(cols["name"].type, String)
    assert isinstance(cols["active"].type, Boolean)
    assert isinstance(cols["signup_ts"].type, DateTime)

    # nullable reflected correctly
    assert cols["email"].nullable is True
    assert cols["name"].nullable is False

    # default values
    assert cols["active"].default.arg is True


def test_pydantic_to_sql_all_types():
    """Test conversion of all supported scalar types"""
    CompleteSQL = SQLModelAdapter.pydantic_model_to_sql(CompleteTypeSchema)

    mapper = inspect(CompleteSQL)
    cols = {c.key: c for c in mapper.columns}

    # Verify all types mapped correctly
    assert isinstance(cols["int_val"].type, Integer)
    assert isinstance(cols["float_val"].type, Float)
    assert isinstance(cols["bool_val"].type, Boolean)
    assert isinstance(cols["str_val"].type, String)
    assert isinstance(cols["bytes_val"].type, LargeBinary)
    assert isinstance(cols["datetime_val"].type, DateTime)
    assert isinstance(cols["date_val"].type, Date)
    assert isinstance(cols["time_val"].type, Time)
    assert isinstance(cols["uuid_val"].type, String)  # UUID maps to String(36)

    # Verify defaults
    assert cols["int_val"].default.arg == 42
    assert cols["float_val"].default.arg == 3.14
    assert cols["bool_val"].default.arg is True
    assert cols["str_val"].default.arg == "default"


def test_pydantic_to_sql_table_name():
    """Test custom table name"""
    UserSQL = SQLModelAdapter.pydantic_model_to_sql(UserSchema, table_name="users")
    assert UserSQL.__tablename__ == "users"


def test_pydantic_to_sql_custom_pk():
    """Test custom primary key field"""

    class CustomPKSchema(BaseModel):
        custom_id: t.Optional[int] = None
        name: str

    CustomSQL = SQLModelAdapter.pydantic_model_to_sql(
        CustomPKSchema, pk_field="custom_id"
    )
    mapper = inspect(CustomSQL)
    pk_col = mapper.columns["custom_id"]

    assert pk_col.primary_key
    assert pk_col.autoincrement


def test_pydantic_to_sql_unsupported_type():
    """Test error handling for unsupported types"""

    class UnsupportedSchema(BaseModel):
        id: int | None = None
        complex_val: complex  # Not supported

    with pytest.raises(TypeConversionError, match="Unsupported type"):
        SQLModelAdapter.pydantic_model_to_sql(UnsupportedSchema)


def test_round_trip_scalar():
    """Test round-trip conversion: Pydantic -> SQLAlchemy -> Pydantic"""
    UserSQL = SQLModelAdapter.pydantic_model_to_sql(UserSchema)
    RoundTrip = SQLModelAdapter.sql_model_to_pydantic(UserSQL)

    # orm_mode / from_attributes (v2) should be on
    assert RoundTrip.model_config.get("orm_mode") or RoundTrip.model_config.get(
        "from_attributes"
    )

    # field definitions preserved
    fields = RoundTrip.model_fields
    assert "name" in fields and fields["name"].is_required()
    assert "email" in fields and not fields["email"].is_required()
    assert fields["active"].default is True


def test_sql_to_pydantic_all_types():
    """Test conversion from SQLAlchemy to Pydantic with all types"""
    CompleteSQL = SQLModelAdapter.pydantic_model_to_sql(CompleteTypeSchema)
    RoundTrip = SQLModelAdapter.sql_model_to_pydantic(CompleteSQL)

    fields = RoundTrip.model_fields

    # Check types
    assert fields["int_val"].annotation is int
    assert fields["float_val"].annotation is float
    assert fields["bool_val"].annotation is bool
    assert fields["str_val"].annotation is str
    assert fields["bytes_val"].annotation is bytes
    assert fields["datetime_val"].annotation is datetime
    assert fields["date_val"].annotation is date
    assert fields["time_val"].annotation is time

    # Check defaults
    assert fields["int_val"].default == 42
    assert fields["float_val"].default == 3.14
    assert fields["bool_val"].default is True
    assert fields["str_val"].default == "default"


def test_sql_to_pydantic_name_suffix():
    """Test custom name suffix for generated Pydantic model"""
    UserSQL = SQLModelAdapter.pydantic_model_to_sql(UserSchema)
    CustomName = SQLModelAdapter.sql_model_to_pydantic(UserSQL, name_suffix="Model")

    assert CustomName.__name__ == "UserSQLModel"


def test_sql_to_pydantic_unsupported_type():
    """Test error handling for unsupported SQL types"""
    from sqlalchemy import Column, MetaData, Table
    from sqlalchemy.dialects.postgresql import JSONB

    # Create a SQLAlchemy model with an unsupported type
    metadata = MetaData()
    unsupported_table = Table(
        "unsupported",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("json_data", JSONB),  # Not in the mapping
    )

    # Create a mock class with the table and proper SQLAlchemy setup
    class UnsupportedSQL:
        __tablename__ = "unsupported"
        __table__ = unsupported_table
        columns = unsupported_table.columns

        @classmethod
        def __table_cls__(cls):
            return unsupported_table

    # Mock the inspect function to return our columns
    def mock_inspect(cls):
        class MockInspector:
            columns = [
                Column("id", Integer, primary_key=True),
                Column("json_data", JSONB),
            ]

        return MockInspector()

    # Patch the inspect function temporarily
    import unittest.mock

    with unittest.mock.patch(
        "sqlalchemy.inspect", return_value=mock_inspect(UnsupportedSQL)
    ):
        with pytest.raises(TypeConversionError, match="Unsupported SQL type"):
            SQLModelAdapter.sql_model_to_pydantic(UnsupportedSQL)
