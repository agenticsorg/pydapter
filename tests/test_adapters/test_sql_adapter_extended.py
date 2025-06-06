"""
Extended tests for SQL adapter functionality.
"""

from unittest.mock import MagicMock, patch

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


class TestSQLAdapterExtended:
    """Extended tests for SQL adapter functionality."""

    @patch("pydapter.extras.sql_.sa")
    def test_sql_table_helper(self, mock_sa, sql_sample):
        """Test the _table helper method."""
        # Create mock metadata and bind
        mock_metadata = MagicMock()
        mock_table = MagicMock()
        mock_sa.Table.return_value = mock_table

        # Call the _table helper
        result = SQLAdapter._table(mock_metadata, "test_table")

        # Verify the result
        assert result == mock_table

        # Verify sa.Table was called with correct arguments
        mock_sa.Table.assert_called_once_with(
            "test_table", mock_metadata, autoload_with=mock_metadata.bind
        )

    @patch("pydapter.extras.sql_.sa")
    def test_sql_from_obj_with_selectors(self, mock_sa, sql_sample):
        """Test conversion from SQL record to model with selectors."""
        # Setup mocks
        mock_engine = MagicMock()
        mock_sa.create_engine.return_value = mock_engine

        mock_metadata = MagicMock()
        mock_sa.MetaData.return_value = mock_metadata

        mock_table = MagicMock()
        mock_sa.Table.return_value = mock_table

        mock_select = MagicMock()
        mock_sa.select.return_value = mock_select

        mock_conn = MagicMock()
        mock_engine.begin.return_value.__enter__.return_value = mock_conn

        mock_result = MagicMock()
        mock_conn.execute.return_value = mock_result

        # Mock the fetchall result
        mock_row = MagicMock()
        mock_row._mapping = {"id": 1, "name": "test", "value": 42.5}
        mock_result.fetchall.return_value = [mock_row]

        # Test from_obj with selectors
        model_cls = sql_sample.__class__
        result = model_cls.adapt_from(
            {
                "engine_url": "sqlite:///:memory:",
                "table": "test_table",
                "selectors": {"id": 1},
            },
            obj_key="sql",
        )

        # Verify the result
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].id == 1
        assert result[0].name == "test"
        assert result[0].value == 42.5

        # Verify the select was called with the selectors
        mock_select.filter_by.assert_called_once_with(id=1)

    @patch("pydapter.extras.sql_.sa")
    def test_sql_from_obj_single(self, mock_sa, sql_sample):
        """Test conversion from SQL record to model with many=False."""
        # Setup mocks
        mock_engine = MagicMock()
        mock_sa.create_engine.return_value = mock_engine

        mock_metadata = MagicMock()
        mock_sa.MetaData.return_value = mock_metadata

        mock_table = MagicMock()
        mock_sa.Table.return_value = mock_table

        mock_select = MagicMock()
        mock_sa.select.return_value = mock_select

        mock_conn = MagicMock()
        mock_engine.begin.return_value.__enter__.return_value = mock_conn

        mock_result = MagicMock()
        mock_conn.execute.return_value = mock_result

        # Mock the fetchall result
        mock_row = MagicMock()
        mock_row._mapping = {"id": 1, "name": "test", "value": 42.5}
        mock_result.fetchall.return_value = [mock_row]

        # Test from_obj with many=False
        model_cls = sql_sample.__class__
        result = model_cls.adapt_from(
            {"engine_url": "sqlite:///:memory:", "table": "test_table"},
            obj_key="sql",
            many=False,
        )

        # Verify the result
        assert not isinstance(result, list)
        assert result.id == 1
        assert result.name == "test"
        assert result.value == 42.5

    @patch("pydapter.extras.sql_.sa")
    def test_sql_to_obj_multiple_items(self, mock_sa, sql_model_factory):
        """Test conversion from multiple models to SQL records."""
        # Create multiple models
        model1 = sql_model_factory(id=1, name="test1", value=42.5)
        model2 = sql_model_factory(id=2, name="test2", value=43.5)

        # Setup mocks
        mock_engine = MagicMock()
        mock_sa.create_engine.return_value = mock_engine

        mock_metadata = MagicMock()
        mock_sa.MetaData.return_value = mock_metadata

        mock_table = MagicMock()
        mock_sa.Table.return_value = mock_table

        mock_conn = MagicMock()
        mock_engine.begin.return_value.__enter__.return_value = mock_conn

        mock_insert = MagicMock()
        mock_sa.insert.return_value = mock_insert

        # Directly test the adapter's to_obj method with multiple items
        SQLAdapter.to_obj(
            [model1, model2], engine_url="sqlite:///:memory:", table="test_table"
        )

        # Verify sa.insert was called with the table
        mock_sa.insert.assert_called_once_with(mock_table)

        # Verify conn.execute was called with the insert and the rows
        expected_rows = [
            {"id": 1, "name": "test1", "value": 42.5},
            {"id": 2, "name": "test2", "value": 43.5},
        ]
        mock_conn.execute.assert_called_once_with(mock_insert, expected_rows)

    @patch("pydapter.extras.sql_.sa")
    def test_sql_to_obj_with_single_item(self, mock_sa, sql_sample):
        """Test conversion from a single model to SQL record."""
        # Setup mocks
        mock_engine = MagicMock()
        mock_sa.create_engine.return_value = mock_engine

        mock_metadata = MagicMock()
        mock_sa.MetaData.return_value = mock_metadata

        mock_table = MagicMock()
        mock_sa.Table.return_value = mock_table

        mock_conn = MagicMock()
        mock_engine.begin.return_value.__enter__.return_value = mock_conn

        mock_insert = MagicMock()
        mock_sa.insert.return_value = mock_insert

        # Test to_obj with a single item and many=False
        sql_sample.adapt_to(
            obj_key="sql",
            engine_url="sqlite:///:memory:",
            table="test_table",
            many=False,
        )

        # Verify sa.insert was called with the table
        mock_sa.insert.assert_called_once_with(mock_table)

        # Verify conn.execute was called with the insert and the row
        expected_rows = [{"id": 1, "name": "test", "value": 42.5}]
        mock_conn.execute.assert_called_once_with(mock_insert, expected_rows)
