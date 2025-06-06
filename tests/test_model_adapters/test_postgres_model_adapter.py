import ipaddress
from datetime import date, datetime

from pydantic import BaseModel, Field
from pydapter.model_adapters.postgres_model import PostgresModelAdapter
from sqlalchemy import String, inspect
from sqlalchemy.dialects.postgresql import (
    ARRAY,
    CIDR,
    DATERANGE,
    INET,
    INT4RANGE,
    JSONB,
    TSRANGE,
)


class AddressModel(BaseModel):
    street: str
    city: str
    zip_code: str


class UserWithNestedSchema(BaseModel):
    id: int | None = None
    name: str
    address: AddressModel = Field(..., json_schema_extra={"db_type": "jsonb"})


class ArraySchema(BaseModel):
    id: int | None = None
    int_array: list[int] = Field(
        ..., json_schema_extra={"db_type": "array", "array_dimensions": 1}
    )
    str_array: list[str] = Field(
        ..., json_schema_extra={"db_type": "array", "array_dimensions": 1}
    )
    nested_array: list[list[float]] = Field(
        ..., json_schema_extra={"db_type": "array", "array_dimensions": 2}
    )


class RangeSchema(BaseModel):
    id: int | None = None
    int_range: tuple[int, int] = Field(..., json_schema_extra={"db_type": "int4range"})
    date_range: tuple[date, date] = Field(
        ..., json_schema_extra={"db_type": "daterange"}
    )
    ts_range: tuple[datetime, datetime] = Field(
        ..., json_schema_extra={"db_type": "tsrange"}
    )


class NetworkSchema(BaseModel):
    id: int | None = None
    ipv4: ipaddress.IPv4Address = Field(..., json_schema_extra={"db_type": "inet"})
    ipv6: ipaddress.IPv6Address = Field(..., json_schema_extra={"db_type": "inet"})
    network: ipaddress.IPv4Network = Field(..., json_schema_extra={"db_type": "cidr"})


class GeometricSchema(BaseModel):
    id: int | None = None
    point: tuple[float, float] = Field(..., json_schema_extra={"db_type": "point"})
    line: tuple[float, float, float, float] = Field(
        ..., json_schema_extra={"db_type": "line"}
    )
    box: tuple[float, float, float, float] = Field(
        ..., json_schema_extra={"db_type": "box"}
    )


def test_jsonb_with_nested_models():
    """Test JSONB fields with nested Pydantic models."""
    # Initialize the adapter
    adapter = PostgresModelAdapter()

    # Convert to SQLAlchemy model
    UserSQL = adapter.pydantic_model_to_sql(UserWithNestedSchema)

    # Verify JSONB column
    mapper = inspect(UserSQL)
    address_col = mapper.columns["address"]
    assert isinstance(address_col.type, JSONB)

    # Test round-trip conversion
    adapter.sql_model_to_pydantic(UserSQL)

    # Create a model instance
    address = AddressModel(street="123 Main St", city="Anytown", zip_code="12345")
    _ = UserWithNestedSchema(id=1, name="John Doe", address=address)

    # Convert to SQLAlchemy instance
    user_sql = UserSQL(id=1, name="John Doe", address=address.model_dump())

    # Verify the address is stored as a dictionary
    assert isinstance(user_sql.address, dict)
    assert user_sql.address["street"] == "123 Main St"
    assert user_sql.address["city"] == "Anytown"
    assert user_sql.address["zip_code"] == "12345"


def test_array_types_with_dimensions():
    """Test ARRAY types with dimension handling."""
    # Initialize the adapter
    adapter = PostgresModelAdapter()

    # Convert to SQLAlchemy model
    ArraySQL = adapter.pydantic_model_to_sql(ArraySchema)

    # Verify array columns
    mapper = inspect(ArraySQL)

    int_array_col = mapper.columns["int_array"]
    assert isinstance(int_array_col.type, ARRAY)
    assert int_array_col.type.dimensions == 1

    str_array_col = mapper.columns["str_array"]
    assert isinstance(str_array_col.type, ARRAY)
    assert str_array_col.type.dimensions == 1

    nested_array_col = mapper.columns["nested_array"]
    assert isinstance(nested_array_col.type, ARRAY)
    assert nested_array_col.type.dimensions == 2


def test_range_types():
    """Test PostgreSQL Range types."""
    # Initialize the adapter
    adapter = PostgresModelAdapter()

    # Convert to SQLAlchemy model
    RangeSQL = adapter.pydantic_model_to_sql(RangeSchema)

    # Verify range columns
    mapper = inspect(RangeSQL)

    int_range_col = mapper.columns["int_range"]
    assert isinstance(int_range_col.type, INT4RANGE)

    date_range_col = mapper.columns["date_range"]
    assert isinstance(date_range_col.type, DATERANGE)

    ts_range_col = mapper.columns["ts_range"]
    assert isinstance(ts_range_col.type, TSRANGE)


def test_network_types():
    """Test PostgreSQL Network types."""
    # Initialize the adapter
    adapter = PostgresModelAdapter()

    # Convert to SQLAlchemy model
    NetworkSQL = adapter.pydantic_model_to_sql(NetworkSchema)

    # Verify network columns
    mapper = inspect(NetworkSQL)

    ipv4_col = mapper.columns["ipv4"]
    assert isinstance(ipv4_col.type, INET)

    ipv6_col = mapper.columns["ipv6"]
    assert isinstance(ipv6_col.type, INET)

    network_col = mapper.columns["network"]
    assert isinstance(network_col.type, CIDR)


def test_geometric_types():
    """Test PostgreSQL Geometric types."""
    # Initialize the adapter
    adapter = PostgresModelAdapter()

    # Convert to SQLAlchemy model
    GeometricSQL = adapter.pydantic_model_to_sql(GeometricSchema)

    # Verify geometric columns
    mapper = inspect(GeometricSQL)

    point_col = mapper.columns["point"]
    assert isinstance(point_col.type, String)

    line_col = mapper.columns["line"]
    assert isinstance(line_col.type, String)

    box_col = mapper.columns["box"]
    assert isinstance(box_col.type, String)


def test_handle_jsonb():
    """Test handle_jsonb method."""
    # Initialize the adapter
    adapter = PostgresModelAdapter()

    # Create a field info mock
    class MockFieldInfo:
        def __init__(self, required=True, default=None):
            self.annotation = dict
            self.default = default
            self._required = required

        def is_required(self):
            return self._required

    # Test with a nested model
    column, converter = adapter.handle_jsonb("address", MockFieldInfo(), AddressModel)

    assert isinstance(column.type, JSONB)
    assert column.nullable is False

    # Test the converter
    address = AddressModel(street="123 Main St", city="Anytown", zip_code="12345")
    result = converter(address)

    assert isinstance(result, dict)
    assert result["street"] == "123 Main St"
    assert result["city"] == "Anytown"
    assert result["zip_code"] == "12345"

    # Test with a dictionary
    dict_result = converter({
        "street": "456 Oak St",
        "city": "Othertown",
        "zip_code": "67890",
    })

    assert isinstance(dict_result, dict)
    assert dict_result["street"] == "456 Oak St"
    assert dict_result["city"] == "Othertown"
    assert dict_result["zip_code"] == "67890"


def test_handle_array():
    """Test handle_array method."""
    # Initialize the adapter
    adapter = PostgresModelAdapter()

    # Test with different dimensions
    int_array_col = adapter.handle_array(int, dimensions=1, nullable=False)
    assert isinstance(int_array_col.type, ARRAY)
    assert int_array_col.type.dimensions == 1
    assert int_array_col.nullable is False

    # Test with nullable
    str_array_col = adapter.handle_array(str, dimensions=1, nullable=True)
    assert isinstance(str_array_col.type, ARRAY)
    assert str_array_col.nullable is True

    # Test with default
    default_array = [1, 2, 3]
    default_array_col = adapter.handle_array(
        int, dimensions=1, nullable=False, default=default_array
    )
    assert default_array_col.default.arg == default_array
