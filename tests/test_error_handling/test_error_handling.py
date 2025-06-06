"""
Tests for error handling in pydapter.
"""

from pathlib import Path

import pytest
from pydantic import BaseModel
from pydapter.adapters import CsvAdapter, JsonAdapter, TomlAdapter
from pydapter.core import Adaptable, Adapter, AdapterRegistry
from pydapter.exceptions import (
    AdapterError,
    AdapterNotFoundError,
    ConfigurationError,
    ConnectionError,
    ParseError,
    QueryError,
    ResourceError,
)
from pydapter.exceptions import ValidationError as AdapterValidationError


class TestCustomExceptions:
    """Tests for custom exception classes."""

    def test_adapter_error_basic(self):
        """Test basic AdapterError functionality."""
        error = AdapterError("Test error")
        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.context == {}

    def test_adapter_error_with_context(self):
        """Test AdapterError with context."""
        error = AdapterError("Test error", key1="value1", key2=123)
        assert "Test error" in str(error)
        assert "key1='value1'" in str(error)
        assert "key2=123" in str(error)
        assert error.context == {"key1": "value1", "key2": 123}

    def test_validation_error(self):
        """Test ValidationError."""
        data = {"id": "not_an_int"}
        error = AdapterValidationError("Validation failed", data=data)
        assert "Validation failed" in str(error)
        assert error.data == data

    def test_parse_error(self):
        """Test ParseError."""
        source = '{"invalid": json'
        error = ParseError("Parse error", source=source)
        assert "Parse error" in str(error)
        assert error.source == source

    def test_connection_error(self):
        """Test ConnectionError."""
        url = "postgresql://localhost:5432/nonexistent"
        error = ConnectionError("Connection failed", adapter="postgres", url=url)
        assert "Connection failed" in str(error)
        assert error.adapter == "postgres"
        assert error.url == url

    def test_query_error(self):
        """Test QueryError."""
        query = "SELECT * FROM nonexistent"
        error = QueryError("Query failed", query=query, adapter="sql")
        assert "Query failed" in str(error)
        assert error.query == query
        assert error.adapter == "sql"

    def test_resource_error(self):
        """Test ResourceError."""
        resource = "users"
        error = ResourceError("Resource not found", resource=resource)
        assert "Resource not found" in str(error)
        assert error.resource == resource

    def test_configuration_error(self):
        """Test ConfigurationError."""
        config = {"url": "invalid://url"}
        error = ConfigurationError("Invalid configuration", config=config)
        assert "Invalid configuration" in str(error)
        assert error.config == config

    def test_adapter_not_found_error(self):
        """Test AdapterNotFoundError."""
        obj_key = "nonexistent"
        error = AdapterNotFoundError("Adapter not found", obj_key=obj_key)
        assert "Adapter not found" in str(error)
        assert error.obj_key == obj_key


class TestInvalidAdapters:
    """Tests for invalid adapter implementations."""

    def test_missing_obj_key(self):
        """Test adapter missing the required obj_key attribute."""

        class MissingKeyAdapter:
            @classmethod
            def from_obj(cls, subj_cls, obj, /, *, many=False, **kw):
                return subj_cls()

            @classmethod
            def to_obj(cls, subj, /, *, many=False, **kw):
                return {}

        registry = AdapterRegistry()
        with pytest.raises(ConfigurationError, match="Adapter must define 'obj_key'"):
            registry.register(MissingKeyAdapter)

    def test_missing_methods(self):
        """Test adapter missing required methods."""

        class MissingMethodAdapter:
            obj_key = "invalid"
            # Missing from_obj and to_obj methods

        # Check if it implements the Adapter protocol
        assert not isinstance(MissingMethodAdapter, Adapter)

    def test_invalid_return_types(self):
        """Test adapter with invalid return types."""

        class InvalidReturnAdapter:
            obj_key = "invalid_return"

            @classmethod
            def from_obj(cls, subj_cls, obj, /, *, many=False, **kw):
                return None  # Invalid return type

            @classmethod
            def to_obj(cls, subj, /, *, many=False, **kw):
                return None  # Invalid return type

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_adapter(InvalidReturnAdapter)

        # Test from_obj with invalid return
        # The implementation might handle None returns gracefully
        # Instead, test that the result is not a valid model instance
        with pytest.raises(AdapterError):
            TestModel.adapt_from({}, obj_key="invalid_return")

        # Test to_obj with invalid return
        model = TestModel(id=1, name="test", value=42.5)
        with pytest.raises(AdapterError):
            model.adapt_to(obj_key="invalid_return")


class TestJsonAdapterErrors:
    """Tests for JSON adapter error handling."""

    def test_invalid_json(self):
        """Test handling of invalid JSON input."""

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_adapter(JsonAdapter)

        # Test invalid JSON
        with pytest.raises(ParseError) as exc_info:
            TestModel.adapt_from("{invalid json}", obj_key="json")
        assert "Invalid JSON" in str(exc_info.value)

    def test_empty_json(self):
        """Test handling of empty JSON input."""

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_adapter(JsonAdapter)

        # Test empty string
        with pytest.raises(ParseError) as exc_info:
            TestModel.adapt_from("", obj_key="json")
        assert "Empty JSON content" in str(exc_info.value)

    def test_missing_required_fields(self):
        """Test handling of missing required fields."""

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_adapter(JsonAdapter)

        # Test missing required fields
        with pytest.raises(AdapterValidationError) as exc_info:
            TestModel.adapt_from('{"id": 1}', obj_key="json")
        assert "Validation error" in str(exc_info.value)
        assert "name" in str(exc_info.value) or "value" in str(exc_info.value)

    def test_invalid_field_types(self):
        """Test handling of invalid field types."""

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_adapter(JsonAdapter)

        # Test invalid field types
        with pytest.raises(AdapterValidationError) as exc_info:
            TestModel.adapt_from(
                '{"id": "not_an_int", "name": "test", "value": 42.5}', obj_key="json"
            )
        assert "Validation error" in str(exc_info.value)
        assert "id" in str(exc_info.value)

    def test_json_file_not_found(self):
        """Test handling of non-existent JSON file."""

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_adapter(JsonAdapter)

        # Test non-existent file
        with pytest.raises(ParseError) as exc_info:
            TestModel.adapt_from(Path("nonexistent.json"), obj_key="json")
        assert "Failed to read" in str(exc_info.value)

    def test_json_array_with_many_false(self):
        """Test handling of JSON array with many=False."""

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_adapter(JsonAdapter)

        # Test JSON array with many=False
        with pytest.raises(AdapterValidationError) as exc_info:
            TestModel.adapt_from(
                '[{"id": 1, "name": "test", "value": 42.5}]', obj_key="json", many=False
            )
        assert "Validation error" in str(exc_info.value)


class TestCsvAdapterErrors:
    """Tests for CSV adapter error handling."""

    def test_empty_csv(self):
        """Test handling of empty CSV input."""

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_adapter(CsvAdapter)

        # Test empty string
        with pytest.raises(ParseError) as exc_info:
            TestModel.adapt_from("", obj_key="csv")
        assert "Empty CSV content" in str(exc_info.value)

    def test_missing_headers(self):
        """Test handling of CSV with missing headers."""

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_adapter(CsvAdapter)

        # Test CSV without headers
        with pytest.raises(ParseError) as exc_info:
            # Create a CSV reader with empty fieldnames
            TestModel.adapt_from("", obj_key="csv")
        assert "Empty CSV content" in str(exc_info.value)

        # Test CSV with empty headers
        with pytest.raises(ParseError) as exc_info:
            # Create a CSV with empty header row
            TestModel.adapt_from(",,,\n1,test,42.5", obj_key="csv")
        assert "CSV missing required fields" in str(exc_info.value)

    def test_missing_required_fields(self):
        """Test handling of CSV with missing required fields."""

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_adapter(CsvAdapter)

        # Test CSV with missing required fields
        with pytest.raises(ParseError) as exc_info:
            TestModel.adapt_from("id,name\n1,test", obj_key="csv")
        assert "CSV missing required fields" in str(exc_info.value)
        assert "value" in str(exc_info.value)

    def test_invalid_field_types(self):
        """Test handling of CSV with invalid field types."""

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_adapter(CsvAdapter)

        # Test CSV with invalid field types
        with pytest.raises(AdapterValidationError) as exc_info:
            TestModel.adapt_from("id,name,value\nnot_an_int,test,42.5", obj_key="csv")
        assert "Validation error" in str(exc_info.value)
        assert "id" in str(exc_info.value)

    def test_csv_file_not_found(self):
        """Test handling of non-existent CSV file."""

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_adapter(CsvAdapter)

        # Test non-existent file
        with pytest.raises(ParseError) as exc_info:
            TestModel.adapt_from(Path("nonexistent.csv"), obj_key="csv")
        assert "Failed to read" in str(exc_info.value)

    def test_csv_dialect_support(self):
        """Test CSV adapter with different dialects."""

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_adapter(CsvAdapter)

        # Test with semicolon delimiter
        csv_data = 'id;name;value\n1;"test";42.5'
        result = TestModel.adapt_from(csv_data, obj_key="csv", delimiter=";")
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].id == 1
        assert result[0].name == "test"
        assert result[0].value == 42.5

        # Test with tab delimiter
        csv_data = 'id\tname\tvalue\n1\t"test"\t42.5'
        result = TestModel.adapt_from(csv_data, obj_key="csv", delimiter="\t")
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].id == 1
        assert result[0].name == "test"
        assert result[0].value == 42.5

    def test_csv_with_special_characters(self):
        """Test CSV adapter with special characters."""

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_adapter(CsvAdapter)

        # Test with commas in quoted fields
        csv_data = 'id,name,value\n1,"name with, comma",42.5'
        result = TestModel.adapt_from(csv_data, obj_key="csv")
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].id == 1
        assert result[0].name == "name with, comma"
        assert result[0].value == 42.5


class TestTomlAdapterErrors:
    """Tests for TOML adapter error handling."""

    def test_invalid_toml(self):
        """Test handling of invalid TOML input."""

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_adapter(TomlAdapter)

        # Test invalid TOML
        with pytest.raises(ParseError) as exc_info:
            TestModel.adapt_from("invalid toml = data", obj_key="toml")
        assert "Invalid TOML" in str(exc_info.value)

    def test_empty_toml(self):
        """Test handling of empty TOML input."""

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_adapter(TomlAdapter)

        # Test empty string
        with pytest.raises(ParseError) as exc_info:
            TestModel.adapt_from("", obj_key="toml")
        assert "Empty TOML content" in str(exc_info.value)

    def test_missing_required_fields(self):
        """Test handling of TOML with missing required fields."""

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_adapter(TomlAdapter)

        # Test TOML with missing required fields
        with pytest.raises(AdapterValidationError) as exc_info:
            TestModel.adapt_from("id = 1\nname = 'test'", obj_key="toml")
        assert "Validation error" in str(exc_info.value)
        assert "value" in str(exc_info.value)

    def test_invalid_field_types(self):
        """Test handling of TOML with invalid field types."""

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_adapter(TomlAdapter)

        # Test TOML with invalid field types
        with pytest.raises(AdapterValidationError) as exc_info:
            TestModel.adapt_from(
                "id = 'not_an_int'\nname = 'test'\nvalue = 42.5", obj_key="toml"
            )
        assert "Validation error" in str(exc_info.value)
        assert "id" in str(exc_info.value)

    def test_toml_file_not_found(self):
        """Test handling of non-existent TOML file."""

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_adapter(TomlAdapter)

        # Test non-existent file
        with pytest.raises(ParseError) as exc_info:
            TestModel.adapt_from(Path("nonexistent.toml"), obj_key="toml")
        assert "Failed to read" in str(exc_info.value)


class TestRegistryErrors:
    """Tests for registry-related errors."""

    def test_unregistered_adapter(self):
        """Test retrieval of unregistered adapter."""
        registry = AdapterRegistry()

        with pytest.raises(
            AdapterNotFoundError, match="No adapter registered for 'nonexistent'"
        ):
            registry.get("nonexistent")

    def test_duplicate_registration(self):
        """Test duplicate adapter registration."""

        class Adapter1:
            obj_key = "duplicate"

            @classmethod
            def from_obj(cls, subj_cls, obj, /, *, many=False, **kw):
                return subj_cls()

            @classmethod
            def to_obj(cls, subj, /, *, many=False, **kw):
                return {}

        class Adapter2:
            obj_key = "duplicate"

            @classmethod
            def from_obj(cls, subj_cls, obj, /, *, many=False, **kw):
                return subj_cls()

            @classmethod
            def to_obj(cls, subj, /, *, many=False, **kw):
                return {}

        registry = AdapterRegistry()
        registry.register(Adapter1)
        registry.register(Adapter2)

        # The second registration should overwrite the first
        assert registry.get("duplicate") == Adapter2


class TestAdaptableErrors:
    """Tests for Adaptable mixin errors."""

    def test_missing_adapter(self):
        """Test using an unregistered adapter with Adaptable."""

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        model = TestModel(id=1, name="test", value=42.5)

        with pytest.raises(
            AdapterNotFoundError, match="No adapter registered for 'nonexistent'"
        ):
            model.adapt_to(obj_key="nonexistent")

        with pytest.raises(
            AdapterNotFoundError, match="No adapter registered for 'nonexistent'"
        ):
            TestModel.adapt_from({}, obj_key="nonexistent")

    def test_invalid_model_data(self):
        """Test handling of invalid model data."""

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_adapter(JsonAdapter)

        # Create a model with valid data
        model = TestModel(id=1, name="test", value=42.5)

        # Serialize the model
        serialized = model.adapt_to(obj_key="json")

        # Modify the serialized data to be invalid
        invalid_data = serialized.replace('"id": 1', '"id": "invalid"')

        # Try to deserialize the invalid data
        with pytest.raises(AdapterValidationError):
            TestModel.adapt_from(invalid_data, obj_key="json")


class TestEdgeCases:
    """Tests for edge cases in adapters."""

    def test_boundary_values(self):
        """Test handling of boundary values."""

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_adapter(JsonAdapter)

        # Test with very large integer
        json_data = (
            '{"id": 9223372036854775807, "name": "test", "value": 42.5}'  # Max int64
        )
        model = TestModel.adapt_from(json_data, obj_key="json")
        assert model.id == 9223372036854775807

        # Test with very small float
        json_data = '{"id": 1, "name": "test", "value": 1e-308}'  # Near min float64
        model = TestModel.adapt_from(json_data, obj_key="json")
        assert model.value == 1e-308

    def test_unicode_characters(self):
        """Test handling of Unicode characters."""

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_adapter(JsonAdapter)
        TestModel.register_adapter(CsvAdapter)

        # Test JSON with Unicode characters
        json_data = '{"id": 1, "name": "测试", "value": 42.5}'
        model = TestModel.adapt_from(json_data, obj_key="json")
        assert model.name == "测试"

        # Test CSV with Unicode characters
        csv_data = 'id,name,value\n1,"测试",42.5'
        model = TestModel.adapt_from(csv_data, obj_key="csv")[0]
        assert model.name == "测试"

    def test_empty_collections(self):
        """Test handling of empty collections."""

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_adapter(JsonAdapter)

        # Test with empty array for many=True
        json_data = "[]"
        result = TestModel.adapt_from(json_data, obj_key="json", many=True)
        assert isinstance(result, list)
        assert len(result) == 0

    def test_very_long_strings(self):
        """Test handling of very long strings."""

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_adapter(JsonAdapter)

        # Test with very long string
        long_name = "x" * 10000
        json_data = f'{{"id": 1, "name": "{long_name}", "value": 42.5}}'
        model = TestModel.adapt_from(json_data, obj_key="json")
        assert model.name == long_name
        assert len(model.name) == 10000
