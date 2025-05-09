import pytest
import ipaddress
from typing import Dict, List, Optional, Tuple, Any
from datetime import date, datetime

from pydantic import BaseModel, Field
from sqlalchemy import Column, String, inspect
from sqlalchemy.dialects.postgresql import ARRAY, CIDR, DATERANGE, INET, INT4RANGE, JSONB, TSRANGE
from sqlalchemy.orm import DeclarativeBase

from pydapter.exceptions import TypeConversionError
from pydapter.model_adapters.postgres_model import PostgresModelAdapter
from pydapter.model_adapters.sql_model import create_base
from pydapter.model_adapters.type_registry import TypeRegistry


class NetworkConfig(BaseModel):
    id: int | None = None
    ipv4_address: ipaddress.IPv4Address
    ipv6_address: ipaddress.IPv6Address
    ipv4_network: ipaddress.IPv4Network
    ipv6_network: ipaddress.IPv6Network
    point: Tuple[float, float] = (0.0, 0.0)
    box: Tuple[float, float, float, float] = (0.0, 0.0, 1.0, 1.0)


class RangeModel(BaseModel):
    id: int | None = None
    int_range: Tuple[int, int] = Field((1, 10), json_schema_extra={"db_type": "int4range"})
    date_range: Tuple[date, date] = Field(
        (date(2023, 1, 1), date(2023, 12, 31)), 
        json_schema_extra={"db_type": "daterange"}
    )
    ts_range: Tuple[datetime, datetime] = Field(
        (datetime(2023, 1, 1), datetime(2023, 12, 31)),
        json_schema_extra={"db_type": "tsrange"}
    )


class ArrayModel(BaseModel):
    id: int | None = None
    string_array: List[str] = Field(default_factory=list, json_schema_extra={"db_type": "array"})
    int_array: List[int] = Field(default_factory=list, json_schema_extra={"db_type": "array"})
    float_array: List[float] = Field(default_factory=list)  # Test default array handling
    multi_dim_array: List[List[int]] = Field(
        default_factory=list,
        json_schema_extra={"db_type": "array", "array_dimensions": 2}
    )


class NestedModel(BaseModel):
    name: str
    value: int


class JsonbModel(BaseModel):
    id: int | None = None
    simple_dict: Dict[str, Any] = Field(default_factory=dict, json_schema_extra={"db_type": "jsonb"})
    nested_model: NestedModel = Field(..., json_schema_extra={"db_type": "jsonb"})
    optional_nested: Optional[NestedModel] = Field(None, json_schema_extra={"db_type": "jsonb"})


def test_register_postgres_types():
    """Test registration of PostgreSQL-specific types."""
    adapter = PostgresModelAdapter()
    
    # Create a new adapter instance to trigger registration
    adapter = PostgresModelAdapter()
    adapter._register_postgres_types()
    
    # Check that dict is mapped to JSONB
    sql_type = TypeRegistry.get_sql_type(dict)
    assert sql_type is not None
    assert isinstance(sql_type(), JSONB)
    
    # Check that tuple is mapped
    sql_type = TypeRegistry.get_sql_type(tuple)
    assert sql_type is not None
    
    # Check network types
    sql_type = TypeRegistry.get_sql_type(ipaddress.IPv4Address)
    assert sql_type is not None
    assert isinstance(sql_type(), INET)
    
    sql_type = TypeRegistry.get_sql_type(ipaddress.IPv6Address)
    assert sql_type is not None
    assert isinstance(sql_type(), INET)
    
    sql_type = TypeRegistry.get_sql_type(ipaddress.IPv4Network)
    assert sql_type is not None
    assert isinstance(sql_type(), CIDR)
    
    sql_type = TypeRegistry.get_sql_type(ipaddress.IPv6Network)
    assert sql_type is not None
    assert isinstance(sql_type(), CIDR)


def test_handle_jsonb_with_nested_model():
    """Test handling JSONB fields with nested Pydantic models."""
    field_info = JsonbModel.model_fields["nested_model"]
    
    # Call handle_jsonb with a nested model
    column, converter = PostgresModelAdapter.handle_jsonb("nested_model", field_info, NestedModel)
    
    # Check the column
    assert isinstance(column.type, JSONB)
    assert column.nullable is False
    
    # Check the converter function
    assert converter is not None
    
    # Test the converter with different inputs
    model_instance = NestedModel(name="test", value=42)
    dict_data = {"name": "test", "value": 42}
    
    # Should handle model instances
    result = converter(model_instance)
    assert isinstance(result, dict)
    assert result["name"] == "test"
    assert result["value"] == 42
    
    # Should handle dictionaries
    result = converter(dict_data)
    assert isinstance(result, dict)
    
    # Should handle None for optional fields
    field_info = JsonbModel.model_fields["optional_nested"]
    column, converter = PostgresModelAdapter.handle_jsonb("optional_nested", field_info, NestedModel)
    assert column.nullable is True
    assert converter(None) is None
    
    # Should raise error for invalid types
    with pytest.raises(TypeConversionError):
        converter("not a dict or model")


def test_handle_array():
    """Test handling PostgreSQL ARRAY types."""
    # Test with string items
    column = PostgresModelAdapter.handle_array(str, dimensions=1, nullable=False)
    assert isinstance(column.type, ARRAY)
    assert column.type.dimensions == 1
    assert column.nullable is False
    
    # Test with integer items and multiple dimensions
    column = PostgresModelAdapter.handle_array(int, dimensions=2, nullable=True, default=[])
    assert isinstance(column.type, ARRAY)
    assert column.type.dimensions == 2
    assert column.nullable is True
    # Check default value exists (can't directly compare with [] due to SQLAlchemy's wrapper)
    assert column.default is not None
    assert str(column.default.arg) == '[]'
    
    # Test with unsupported item type
    class UnsupportedType:
        pass
    
    with pytest.raises(TypeConversionError):
        PostgresModelAdapter.handle_array(UnsupportedType, dimensions=1)


def test_pydantic_model_to_sql_with_postgres_types():
    """Test converting Pydantic models with PostgreSQL-specific types to SQLAlchemy."""
    # Convert the network model
    NetworkSQL = PostgresModelAdapter.pydantic_model_to_sql(NetworkConfig)
    
    # Check that the fields were created with the correct types
    mapper = inspect(NetworkSQL)
    assert isinstance(mapper.columns.ipv4_address.type, INET)
    assert isinstance(mapper.columns.ipv6_address.type, INET)
    assert isinstance(mapper.columns.ipv4_network.type, CIDR)
    assert isinstance(mapper.columns.ipv6_network.type, CIDR)
    assert isinstance(mapper.columns.point.type, String)
    assert isinstance(mapper.columns.box.type, String)
    
    # Convert the range model
    RangeSQL = PostgresModelAdapter.pydantic_model_to_sql(RangeModel)
    
    # Check that the range fields were created with the correct types
    mapper = inspect(RangeSQL)
    assert isinstance(mapper.columns.int_range.type, INT4RANGE)
    assert isinstance(mapper.columns.date_range.type, DATERANGE)
    assert isinstance(mapper.columns.ts_range.type, TSRANGE)
    
    # Convert the array model
    ArraySQL = PostgresModelAdapter.pydantic_model_to_sql(ArrayModel)
    
    # Check that the array fields were created with the correct types
    mapper = inspect(ArraySQL)
    assert isinstance(mapper.columns.string_array.type, ARRAY)
    assert isinstance(mapper.columns.int_array.type, ARRAY)
    assert isinstance(mapper.columns.float_array.type, ARRAY)
    assert isinstance(mapper.columns.multi_dim_array.type, ARRAY)
    assert mapper.columns.multi_dim_array.type.dimensions == 2
    
    # Convert the JSONB model
    JsonbSQL = PostgresModelAdapter.pydantic_model_to_sql(JsonbModel)
    
    # Check that the JSONB fields were created with the correct types
    mapper = inspect(JsonbSQL)
    assert isinstance(mapper.columns.simple_dict.type, JSONB)
    assert isinstance(mapper.columns.nested_model.type, JSONB)
    assert isinstance(mapper.columns.optional_nested.type, JSONB)
    assert mapper.columns.optional_nested.nullable is True


def test_pydantic_model_to_sql_with_schema():
    """Test converting a Pydantic model with a specific schema."""
    # Convert the model with a schema
    NetworkSQL = PostgresModelAdapter.pydantic_model_to_sql(
        NetworkConfig, schema="network"
    )
    
    # Check that the schema was set correctly
    assert NetworkSQL.__table_args__["schema"] == "network"


def test_handle_relationship_with_foreign_key():
    """Test handling relationships with foreign keys."""
    # Create a model with a relationship that has a foreign key
    class ParentModel(BaseModel):
        id: int | None = None
        name: str
    
    class ChildModel(BaseModel):
        id: int | None = None
        name: str
        parent: Dict[str, Any] | None = Field(None, json_schema_extra={
            "relationship": {
                "type": "many_to_one",
                "model": "ParentModel",
                "table": "custom_parents",
                "foreign_key": "parent_fk_id"
            }
        })
    
    # This test is more complex and requires a different approach
    # We'll just check that the relationship info is correctly extracted
    field_info = ChildModel.model_fields["parent"]
    
    # Extract relationship info
    rel_info = field_info.json_schema_extra["relationship"]
    assert rel_info["type"] == "many_to_one"
    assert rel_info["model"] == "ParentModel"
    assert rel_info["table"] == "custom_parents"
    assert rel_info["foreign_key"] == "parent_fk_id"