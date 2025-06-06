"""
Tests for Pandas adapter functionality.
"""

from unittest.mock import MagicMock, patch

import pytest
from pydantic import BaseModel
from pydapter.core import Adaptable
from pydapter.extras.pandas_ import DataFrameAdapter


@pytest.fixture
def pandas_model_factory():
    """Factory for creating test models with Pandas adapter registered."""

    def create_model(**kw):
        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        # Register the Pandas adapter
        TestModel.register_adapter(DataFrameAdapter)
        return TestModel(**kw)

    return create_model


@pytest.fixture
def pandas_sample(pandas_model_factory):
    """Create a sample model instance."""
    return pandas_model_factory(id=1, name="test", value=42.5)


class TestPandasAdapterProtocol:
    """Tests for Pandas adapter protocol compliance."""

    def test_pandas_adapter_protocol_compliance(self):
        """Test that DataFrameAdapter implements the Adapter protocol."""
        # Verify required attributes
        assert hasattr(DataFrameAdapter, "obj_key")
        assert isinstance(DataFrameAdapter.obj_key, str)
        assert DataFrameAdapter.obj_key == "pd.DataFrame"

        # Verify method signatures
        assert hasattr(DataFrameAdapter, "from_obj")
        assert hasattr(DataFrameAdapter, "to_obj")

        # Verify the methods can be called as classmethods
        assert callable(DataFrameAdapter.from_obj)
        assert callable(DataFrameAdapter.to_obj)


class TestPandasAdapterFunctionality:
    """Tests for Pandas adapter functionality."""

    @patch("pydapter.extras.pandas_.pd")
    def test_pandas_to_obj(self, mock_pd, pandas_sample):
        """Test conversion from model to DataFrame."""
        # We need to patch the entire Pandas adapter's to_obj method
        with patch("pydapter.extras.pandas_.DataFrameAdapter.to_obj") as mock_to_obj:
            # Configure the mock to return a DataFrame
            mock_df = MagicMock()
            mock_to_obj.return_value = mock_df

            # Test to_obj
            result = pandas_sample.adapt_to(obj_key="pd.DataFrame")

            # Verify the result
            assert result == mock_df

            # Verify the mock was called with the correct arguments
            mock_to_obj.assert_called_once()

    @patch("pydapter.extras.pandas_.pd")
    def test_pandas_from_obj(self, mock_pd, pandas_sample):
        """Test conversion from DataFrame to model."""
        # We need to patch the entire Pandas adapter's from_obj method
        with patch(
            "pydapter.extras.pandas_.DataFrameAdapter.from_obj"
        ) as mock_from_obj:
            # Configure the mock to return a model instance
            expected_model = pandas_sample.__class__(id=1, name="test", value=42.5)
            mock_from_obj.return_value = [expected_model]

            # Create a mock DataFrame
            mock_df = MagicMock()

            # Test from_obj
            model_cls = pandas_sample.__class__
            result = model_cls.adapt_from(mock_df, obj_key="pd.DataFrame")

            # Verify the result
            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0].id == 1
            assert result[0].name == "test"
            assert result[0].value == 42.5

    @patch("pydapter.extras.pandas_.pd")
    def test_pandas_from_obj_single(self, mock_pd, pandas_sample):
        """Test conversion from DataFrame to model with many=False."""
        # We need to patch the entire Pandas adapter's from_obj method
        with patch(
            "pydapter.extras.pandas_.DataFrameAdapter.from_obj"
        ) as mock_from_obj:
            # Configure the mock to return a model instance
            expected_model = pandas_sample.__class__(id=1, name="test", value=42.5)
            mock_from_obj.return_value = expected_model

            # Create a mock DataFrame
            mock_df = MagicMock()

            # Test from_obj with many=False
            model_cls = pandas_sample.__class__
            result = model_cls.adapt_from(mock_df, obj_key="pd.DataFrame", many=False)

            # Verify the result
            assert isinstance(result, model_cls)
            assert result.id == 1
            assert result.name == "test"
            assert result.value == 42.5


class TestPandasAdapterErrorHandling:
    """Tests for Pandas adapter error handling."""

    @patch("pydapter.extras.pandas_.pd")
    def test_pandas_empty_dataframe(self, mock_pd, pandas_sample):
        """Test handling of empty DataFrame."""
        # Create a mock DataFrame with no rows
        mock_df = MagicMock()
        mock_df.to_dict.return_value = []

        # We need to patch the entire Pandas adapter's from_obj method
        with patch(
            "pydapter.extras.pandas_.DataFrameAdapter.from_obj",
            side_effect=lambda subj_cls, obj, **kw: [],
        ):
            # Test from_obj with empty DataFrame
            model_cls = pandas_sample.__class__
            result = model_cls.adapt_from(mock_df, obj_key="pd.DataFrame")

            # Verify result is empty list
            assert isinstance(result, list)
            assert len(result) == 0

    @patch("pydapter.extras.pandas_.pd")
    def test_pandas_invalid_data(self, mock_pd, pandas_sample):
        """Test handling of invalid data."""
        # Create a mock DataFrame with invalid data
        mock_df = MagicMock()

        # We need to patch the entire Pandas adapter's from_obj method to raise an error
        with patch(
            "pydapter.extras.pandas_.DataFrameAdapter.from_obj",
            side_effect=ValueError("Invalid data"),
        ):
            # Test from_obj with invalid data
            model_cls = pandas_sample.__class__
            with pytest.raises(ValueError, match="Invalid data"):
                model_cls.adapt_from(mock_df, obj_key="pd.DataFrame")
