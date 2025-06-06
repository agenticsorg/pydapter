"""
Tests for Excel adapter functionality.
"""

from unittest.mock import MagicMock, patch

import pytest
from pydantic import BaseModel
from pydapter.core import Adaptable
from pydapter.exceptions import AdapterError
from pydapter.extras.excel_ import ExcelAdapter


@pytest.fixture
def excel_model_factory():
    """Factory for creating test models with Excel adapter registered."""

    def create_model(**kw):
        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        # Register the Excel adapter
        TestModel.register_adapter(ExcelAdapter)
        return TestModel(**kw)

    return create_model


@pytest.fixture
def excel_sample(excel_model_factory):
    """Create a sample model instance."""
    return excel_model_factory(id=1, name="test", value=42.5)


class TestExcelAdapterProtocol:
    """Tests for Excel adapter protocol compliance."""

    def test_excel_adapter_protocol_compliance(self):
        """Test that ExcelAdapter implements the Adapter protocol."""
        # Verify required attributes
        assert hasattr(ExcelAdapter, "obj_key")
        assert isinstance(ExcelAdapter.obj_key, str)
        assert ExcelAdapter.obj_key == "xlsx"

        # Verify method signatures
        assert hasattr(ExcelAdapter, "from_obj")
        assert hasattr(ExcelAdapter, "to_obj")

        # Verify the methods can be called as classmethods
        assert callable(ExcelAdapter.from_obj)
        assert callable(ExcelAdapter.to_obj)


class TestExcelAdapterFunctionality:
    """Tests for Excel adapter functionality."""

    @patch("pydapter.extras.excel_.pd")
    def test_excel_to_obj(self, mock_pd, excel_sample, tmp_path):
        """Test conversion from model to Excel."""
        # We need to patch the entire Excel adapter's to_obj method
        with patch("pydapter.extras.excel_.ExcelAdapter.to_obj") as mock_to_obj:
            # Configure the mock to return a path
            mock_to_obj.return_value = {"path": "test.xlsx"}

            # Test to_obj
            result = excel_sample.adapt_to(obj_key="xlsx", path="test.xlsx")

            # Verify the result
            assert result == {"path": "test.xlsx"}

            # Verify the mock was called with the correct arguments
            mock_to_obj.assert_called_once()

    @patch("pydapter.extras.excel_.pd")
    def test_excel_from_obj(self, mock_pd, excel_sample):
        """Test conversion from Excel to model."""
        # We need to patch the entire Excel adapter's from_obj method
        with patch("pydapter.extras.excel_.ExcelAdapter.from_obj") as mock_from_obj:
            # Configure the mock to return a model instance
            expected_model = excel_sample.__class__(id=1, name="test", value=42.5)
            mock_from_obj.return_value = [expected_model]

            # Test from_obj
            model_cls = excel_sample.__class__
            result = model_cls.adapt_from({"path": "test.xlsx"}, obj_key="xlsx")

            # Verify the result
            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0].id == 1
            assert result[0].name == "test"
            assert result[0].value == 42.5

        # Verify result
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].id == 1
        assert result[0].name == "test"
        assert result[0].value == 42.5

    @patch("pydapter.extras.excel_.pd")
    def test_excel_from_obj_single(self, mock_pd, excel_sample):
        """Test conversion from Excel to model with many=False."""
        # We need to patch the entire Excel adapter's from_obj method
        with patch("pydapter.extras.excel_.ExcelAdapter.from_obj") as mock_from_obj:
            # Configure the mock to return a model instance
            expected_model = excel_sample.__class__(id=1, name="test", value=42.5)
            mock_from_obj.return_value = expected_model

            # Test from_obj with many=False
            model_cls = excel_sample.__class__
            result = model_cls.adapt_from(
                {"path": "test.xlsx"}, obj_key="xlsx", many=False
            )

            # Verify the result
            assert isinstance(result, model_cls)
            assert result.id == 1
            assert result.name == "test"
            assert result.value == 42.5

        # Verify result
        assert not isinstance(result, list)
        assert result.id == 1
        assert result.name == "test"
        assert result.value == 42.5


class TestExcelAdapterErrorHandling:
    """Tests for Excel adapter error handling."""

    @patch("pydapter.extras.excel_.pd")
    def test_excel_file_not_found(self, mock_pd, excel_sample):
        """Test handling of file not found error."""
        # Setup mock to raise FileNotFoundError
        mock_pd.read_excel.side_effect = FileNotFoundError("File not found")

        # Test from_obj with non-existent file
        model_cls = excel_sample.__class__
        with pytest.raises(AdapterError, match="File not found"):
            model_cls.adapt_from({"path": "nonexistent.xlsx"}, obj_key="xlsx")

    @patch("pydapter.extras.excel_.pd")
    def test_excel_empty_dataframe(self, mock_pd, excel_sample):
        """Test handling of empty DataFrame."""
        # Setup mock to return empty DataFrame
        mock_df = MagicMock()
        # Properly mock the to_dict method to return an empty list
        mock_df.to_dict.return_value = []
        mock_pd.read_excel.return_value = mock_df

        # Test from_obj with empty DataFrame
        model_cls = excel_sample.__class__
        result = model_cls.adapt_from({"path": "empty.xlsx"}, obj_key="xlsx")

        # Verify result is empty list
        assert isinstance(result, list)
        assert len(result) == 0

    @patch("pydapter.extras.excel_.pd")
    def test_excel_invalid_data(self, mock_pd, excel_sample):
        """Test handling of invalid data."""
        # Configure the mock to raise a ValueError when accessed
        mock_pd.read_excel.side_effect = ValueError("Invalid data")

        # Test from_obj with invalid data
        model_cls = excel_sample.__class__
        with pytest.raises(AdapterError, match="Invalid data"):
            model_cls.adapt_from({"path": "invalid.xlsx"}, obj_key="xlsx")
