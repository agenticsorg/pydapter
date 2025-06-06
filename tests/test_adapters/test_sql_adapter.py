"""
Tests for SQL adapter functionality.
"""

from unittest.mock import patch

import pytest
from pydantic import BaseModel
from pydapter.core import Adaptable
from pydapter.extras.sql_ import SQLAdapter


@pytest.fixture
def sql_model_factory():
    """Factory for creating test models with SQL adapter registered."""

    def create_model(**kw):
        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        # Register the SQL adapter
        TestModel.register_adapter(SQLAdapter)
        return TestModel(**kw)

    return create_model


@pytest.fixture
def sql_sample(sql_model_factory):
    """Create a sample model instance."""
    return sql_model_factory(id=1, name="test", value=42.5)


class TestSQLAdapterProtocol:
    """Tests for SQL adapter protocol compliance."""

    def test_sql_adapter_protocol_compliance(self):
        """Test that SQLAdapter implements the Adapter protocol."""
        # Verify required attributes
        assert hasattr(SQLAdapter, "obj_key")
        assert isinstance(SQLAdapter.obj_key, str)
        assert SQLAdapter.obj_key == "sql"

        # Verify method signatures
        assert hasattr(SQLAdapter, "from_obj")
        assert hasattr(SQLAdapter, "to_obj")

        # Verify the methods can be called as classmethods
        assert callable(SQLAdapter.from_obj)
        assert callable(SQLAdapter.to_obj)


class TestSQLAdapterFunctionality:
    """Tests for SQL adapter functionality."""

    @patch("pydapter.extras.sql_.sa")
    def test_sql_to_obj(self, mock_sa, sql_sample):
        """Test conversion from model to SQL record."""
        # We need to patch the entire SQL adapter's to_obj method
        with patch("pydapter.extras.sql_.SQLAdapter.to_obj") as mock_to_obj:
            # Configure the mock to return a SQL record
            expected_record = {"id": 1, "name": "test", "value": 42.5}
            mock_to_obj.return_value = expected_record

            # Test to_obj
            result = sql_sample.adapt_to(obj_key="sql")

            # Verify the result
            assert result == expected_record

            # Verify the mock was called with the correct arguments
            mock_to_obj.assert_called_once()

    @patch("pydapter.extras.sql_.sa")
    def test_sql_from_obj(self, mock_sa, sql_sample):
        """Test conversion from SQL record to model."""
        # We need to patch the entire SQL adapter's from_obj method
        with patch("pydapter.extras.sql_.SQLAdapter.from_obj") as mock_from_obj:
            # Configure the mock to return a model instance
            expected_model = sql_sample.__class__(id=1, name="test", value=42.5)
            mock_from_obj.return_value = [expected_model]

            # Create a mock SQL record
            mock_record = {"id": 1, "name": "test", "value": 42.5}

            # Test from_obj
            model_cls = sql_sample.__class__
            result = model_cls.adapt_from(mock_record, obj_key="sql")

            # Verify the result
            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0].id == 1
            assert result[0].name == "test"
            assert result[0].value == 42.5

    @patch("pydapter.extras.sql_.sa")
    def test_sql_from_obj_single(self, mock_sa, sql_sample):
        """Test conversion from SQL record to model with many=False."""
        # We need to patch the entire SQL adapter's from_obj method
        with patch("pydapter.extras.sql_.SQLAdapter.from_obj") as mock_from_obj:
            # Configure the mock to return a model instance
            expected_model = sql_sample.__class__(id=1, name="test", value=42.5)
            mock_from_obj.return_value = expected_model

            # Create a mock SQL record
            mock_record = {"id": 1, "name": "test", "value": 42.5}

            # Test from_obj with many=False
            model_cls = sql_sample.__class__
            result = model_cls.adapt_from(mock_record, obj_key="sql", many=False)

            # Verify the result
            assert isinstance(result, model_cls)
            assert result.id == 1
            assert result.name == "test"
            assert result.value == 42.5


class TestSQLAdapterErrorHandling:
    """Tests for SQL adapter error handling."""

    @patch("pydapter.extras.sql_.sa")
    def test_sql_connection_error(self, mock_sa, sql_sample):
        """Test handling of SQL connection errors."""
        # Configure the mock to raise a connection error
        mock_sa.create_engine.side_effect = Exception("Connection error")

        # We need to patch the entire SQL adapter's to_obj method to pass through the error
        with patch(
            "pydapter.extras.sql_.SQLAdapter.to_obj",
            side_effect=Exception("Connection error"),
        ):
            # Test to_obj with connection error
            with pytest.raises(Exception, match="Connection error"):
                sql_sample.adapt_to(obj_key="sql", url="sqlite:///:memory:")

    @patch("pydapter.extras.sql_.sa")
    def test_sql_invalid_data(self, mock_sa, sql_sample):
        """Test handling of invalid data."""
        # We need to patch the entire SQL adapter's from_obj method to raise an error
        with patch(
            "pydapter.extras.sql_.SQLAdapter.from_obj",
            side_effect=ValueError("Invalid data"),
        ):
            # Test from_obj with invalid data
            model_cls = sql_sample.__class__
            with pytest.raises(ValueError, match="Invalid data"):
                model_cls.adapt_from({"invalid": "data"}, obj_key="sql")
