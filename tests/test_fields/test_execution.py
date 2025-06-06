"""Tests for execution field functionality."""

import pytest
from datetime import datetime, timezone
from pydantic import BaseModel

from pydapter.fields.execution import EXECUTION, Execution, ExecutionStatus
from pydapter.exceptions import ValidationError


class TestExecutionStatus:
    """Test ExecutionStatus enum."""

    def test_execution_status_values(self):
        """Test all execution status values."""
        assert ExecutionStatus.PENDING == "pending"
        assert ExecutionStatus.PROCESSING == "processing"
        assert ExecutionStatus.COMPLETED == "completed"
        assert ExecutionStatus.FAILED == "failed"


class TestExecution:
    """Test Execution model."""

    def test_execution_defaults(self):
        """Test default execution values."""
        execution = Execution()
        assert execution.duration is None
        assert execution.response is None
        assert execution.status == ExecutionStatus.PENDING
        assert execution.error is None
        assert execution.response_obj is None
        assert isinstance(execution.updated_at, datetime)
        assert execution.updated_at.tzinfo == timezone.utc

    def test_execution_with_values(self):
        """Test execution with custom values."""
        execution = Execution(
            duration=1.5,
            response={"result": "success"},
            status=ExecutionStatus.COMPLETED,
            error=None,
        )
        assert execution.duration == 1.5
        assert execution.response == {"result": "success"}
        assert execution.status == ExecutionStatus.COMPLETED

    def test_response_validation_with_dict(self):
        """Test response validation with dictionary."""
        execution = Execution(response={"key": "value"})
        assert execution.response == {"key": "value"}

    def test_response_validation_with_basemodel(self):
        """Test response validation with BaseModel."""

        class ResponseModel(BaseModel):
            message: str
            code: int

        response_model = ResponseModel(message="test", code=200)
        execution = Execution(response=response_model)
        assert execution.response == {"message": "test", "code": 200}

    def test_validate_response_method_with_none(self):
        """Test validate_response method when both response and response_obj are None."""
        execution = Execution()
        with pytest.raises(
            ValidationError, match="Response and response_obj are both None"
        ):
            execution.validate_response()

    def test_validate_response_method_with_response_obj(self):
        """Test validate_response method with response_obj."""

        class ResponseModel(BaseModel):
            status: str
            data: dict

        response_obj = ResponseModel(status="ok", data={"id": 123})
        execution = Execution(response_obj=response_obj)

        # Initially response is None
        assert execution.response is None

        # validate_response should convert response_obj to response
        execution.validate_response()
        assert execution.response == {"status": "ok", "data": {"id": 123}}

    def test_execution_field_definition(self):
        """Test EXECUTION field configuration."""
        assert EXECUTION.name == "execution"
        assert EXECUTION.annotation == Execution
        assert EXECUTION.default_factory == Execution
        assert EXECUTION.immutable is True
        assert EXECUTION.validator is not None

    def test_execution_field_validator(self):
        """Test EXECUTION field validator."""
        # Should create new Execution if None
        result = EXECUTION.validator(None, None)
        assert isinstance(result, Execution)

        # Should return existing Execution
        existing = Execution(status=ExecutionStatus.COMPLETED)
        result = EXECUTION.validator(None, existing)
        assert result is existing

    def test_execution_serialization(self):
        """Test execution serialization excludes certain fields."""
        execution = Execution(
            duration=2.0,
            response={"test": "data"},
            status=ExecutionStatus.COMPLETED,
            response_obj={"excluded": "field"},
        )

        data = execution.model_dump()
        assert "response_obj" not in data  # excluded
        assert "updated_at" not in data  # excluded
        assert data["duration"] == 2.0
        assert data["response"] == {"test": "data"}
        assert data["status"] == "completed"
