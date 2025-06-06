"""Tests for params field functionality."""

import pytest
from pydantic import BaseModel
from pydantic_core import PydanticUndefined

from pydapter.fields.params import (
    PARAMS,
    PARAM_TYPE,
    PARAM_TYPE_NULLABLE,
    validate_model_to_params,
    validate_model_to_type,
)
from pydapter.fields.types import Undefined
from pydapter.exceptions import ValidationError


class TestParamsValidation:
    """Test params field validation functions."""

    def test_validate_model_to_params_empty_values(self):
        """Test validation with empty values."""
        assert validate_model_to_params(None) == {}
        assert validate_model_to_params({}) == {}
        assert validate_model_to_params([]) == {}
        assert validate_model_to_params(Undefined) == {}
        assert validate_model_to_params(PydanticUndefined) == {}

    def test_validate_model_to_params_dict(self):
        """Test validation with dictionary."""
        params = {"key": "value", "number": 42}
        assert validate_model_to_params(params) == params

    def test_validate_model_to_params_basemodel(self):
        """Test validation with BaseModel instance."""

        class TestModel(BaseModel):
            name: str
            value: int

        model = TestModel(name="test", value=123)
        result = validate_model_to_params(model)
        assert result == {"name": "test", "value": 123}

    def test_validate_model_to_params_invalid(self):
        """Test validation with invalid input."""
        with pytest.raises(ValidationError, match="Invalid params input"):
            validate_model_to_params("string")

        with pytest.raises(ValidationError, match="Invalid params input"):
            validate_model_to_params(123)

    def test_validate_model_to_type_valid(self):
        """Test type validation with valid inputs."""

        class TestModel(BaseModel):
            name: str

        # Test with class
        assert validate_model_to_type(TestModel) == TestModel
        assert validate_model_to_type(BaseModel) == BaseModel

        # Test with instance
        instance = TestModel(name="test")
        assert validate_model_to_type(instance) == TestModel

    def test_validate_model_to_type_nullable(self):
        """Test type validation with nullable option."""
        # Non-nullable should raise error
        with pytest.raises(ValidationError, match="Model type cannot be None"):
            validate_model_to_type(None, nullable=False)

        # Nullable should return None
        assert validate_model_to_type(None, nullable=True) is None
        assert validate_model_to_type("", nullable=True) is None
        assert validate_model_to_type(0, nullable=True) is None

    def test_validate_model_to_type_invalid(self):
        """Test type validation with invalid inputs."""
        with pytest.raises(ValidationError, match="Invalid model type"):
            validate_model_to_type("string")

        with pytest.raises(ValidationError, match="Invalid model type"):
            validate_model_to_type(dict)

        with pytest.raises(ValidationError, match="Invalid model type"):
            validate_model_to_type(123)


class TestParamsFields:
    """Test the field definitions."""

    def test_params_field(self):
        """Test PARAMS field configuration."""
        assert PARAMS.name == "params"
        assert PARAMS.annotation == dict
        assert PARAMS.default_factory is not None
        assert PARAMS.immutable is True
        assert PARAMS.validator is not None

    def test_param_type_field(self):
        """Test PARAM_TYPE field configuration."""
        assert PARAM_TYPE.name == "param_type"
        assert PARAM_TYPE.annotation == type
        assert PARAM_TYPE.immutable is True
        assert PARAM_TYPE.validator is not None

    def test_param_type_nullable_field(self):
        """Test PARAM_TYPE_NULLABLE field configuration."""
        assert PARAM_TYPE_NULLABLE.name == "param_type_nullable"
        assert PARAM_TYPE_NULLABLE.annotation == type
        assert PARAM_TYPE_NULLABLE.default is None
        assert PARAM_TYPE_NULLABLE.immutable is True
        assert PARAM_TYPE_NULLABLE.validator is not None
