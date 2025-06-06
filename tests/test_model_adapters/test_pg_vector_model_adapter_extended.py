import pytest
from pydantic import BaseModel, Field

# Try to import pgvector, skip tests if not available
try:
    from pgvector.sqlalchemy import Vector
    from pydapter.exceptions import ConfigurationError, TypeConversionError
    from pydapter.model_adapters.pg_vector_model import PGVectorModelAdapter
    from sqlalchemy import Column, String

    VECTOR_AVAILABLE = True
except ImportError:
    VECTOR_AVAILABLE = False

# Skip all tests in this module if pgvector is not available
pytestmark = pytest.mark.skipif(not VECTOR_AVAILABLE, reason="pgvector not installed")


class EmbeddingSchema(BaseModel):
    id: int | None = None
    text: str
    embedding: list[float] = Field(..., json_schema_extra={"vector_dim": 1536})


# Define a simple model for testing relationships
class RelatedItem(BaseModel):
    id: int | None = None
    name: str


class EmbeddingWithRelationship(BaseModel):
    id: int | None = None
    text: str
    embedding: list[float] = Field(..., json_schema_extra={"vector_dim": 1536})


@pytest.mark.skipif(not VECTOR_AVAILABLE, reason="pgvector not installed")
def test_python_type_for():
    """Test the _python_type_for method with Vector column."""
    # Create a Vector column
    vector_column = Column("embedding", Vector(1536))

    # Test that the method correctly identifies the column as a list[float]
    assert PGVectorModelAdapter._python_type_for(vector_column) == list[float]

    # Test with a non-Vector column - should return a type without error
    string_column = Column("text", String())
    result = PGVectorModelAdapter._python_type_for(string_column)
    # The result should be a type or a generic alias (like tuple[float, ...])
    assert result is not None
    # Check if it's a proper type or a generic alias
    assert isinstance(result, type) or hasattr(result, "__origin__")


@pytest.mark.skipif(not VECTOR_AVAILABLE, reason="pgvector not installed")
def test_sql_model_to_pydantic_basic():
    """Test conversion of SQLAlchemy model to Pydantic model."""
    # Create a model
    EmbSQL = PGVectorModelAdapter.pydantic_model_to_sql(EmbeddingSchema)

    # Convert back to Pydantic
    EmbSchemaRT = PGVectorModelAdapter.sql_model_to_pydantic(EmbSQL)

    # Check that the vector field is correctly mapped
    field = EmbSchemaRT.model_fields["embedding"]
    assert field.json_schema_extra and field.json_schema_extra["vector_dim"] == 1536

    # Check model config
    assert EmbSchemaRT.model_config["from_attributes"] is True
    assert EmbSchemaRT.model_config["orm_mode"] is True


@pytest.mark.skipif(not VECTOR_AVAILABLE, reason="pgvector not installed")
def test_validate_vector_dimensions_edge_cases():
    """Test edge cases for vector dimension validation."""
    # Test with None vector
    assert PGVectorModelAdapter.validate_vector_dimensions(None, 1536) is None

    # Test with non-list vector
    with pytest.raises(TypeConversionError) as excinfo:
        PGVectorModelAdapter.validate_vector_dimensions("not a list", 1536)
    assert "Expected list for vector" in str(excinfo.value)

    # Test with None dimension (should pass any dimension)
    vector = [0.1] * 100
    result = PGVectorModelAdapter.validate_vector_dimensions(vector, None)
    assert result is vector


@pytest.mark.skipif(not VECTOR_AVAILABLE, reason="pgvector not installed")
def test_create_index_invalid_type():
    """Test create_index with invalid index type."""
    EmbSQL = PGVectorModelAdapter.pydantic_model_to_sql(EmbeddingSchema)

    # Test with invalid index type
    with pytest.raises(ConfigurationError) as excinfo:
        PGVectorModelAdapter.create_index(
            EmbSQL, "embedding", index_type="invalid_type"
        )

    assert "Unsupported index type: invalid_type" in str(excinfo.value)


@pytest.mark.skipif(not VECTOR_AVAILABLE, reason="pgvector not installed")
def test_find_similar_invalid_metric(mocker):
    """Test find_similar with invalid metric."""
    EmbSQL = PGVectorModelAdapter.pydantic_model_to_sql(EmbeddingSchema)

    # Mock session
    mock_session = mocker.Mock()

    # Test with invalid metric
    vector = [0.1] * 1536
    with pytest.raises(ConfigurationError) as excinfo:
        PGVectorModelAdapter.find_similar(
            mock_session, EmbSQL, "embedding", vector, metric="invalid_metric"
        )

    assert "Unsupported similarity metric: invalid_metric" in str(excinfo.value)


@pytest.mark.skipif(not VECTOR_AVAILABLE, reason="pgvector not installed")
def test_batch_insert_empty_list(mocker):
    """Test batch_insert with empty list."""
    EmbSQL = PGVectorModelAdapter.pydantic_model_to_sql(EmbeddingSchema)

    # Mock session
    mock_session = mocker.Mock()

    # Call batch_insert with empty list
    PGVectorModelAdapter.batch_insert(mock_session, EmbSQL, [])

    # Verify no calls were made
    assert mock_session.add_all.call_count == 0
    assert mock_session.flush.call_count == 0
    assert mock_session.commit.call_count == 1  # Still commits the transaction


@pytest.mark.skipif(not VECTOR_AVAILABLE, reason="pgvector not installed")
def test_batch_insert_custom_batch_size(mocker):
    """Test batch_insert with custom batch size."""
    EmbSQL = PGVectorModelAdapter.pydantic_model_to_sql(EmbeddingSchema)

    # Mock session
    mock_session = mocker.Mock()

    # Create test data - 10 items
    items = [
        {"text": f"Item {i}", "embedding": [float(i)] * 1536} for i in range(1, 11)
    ]

    # Call batch_insert with batch_size=3
    PGVectorModelAdapter.batch_insert(mock_session, EmbSQL, items, batch_size=3)

    # Verify add_all was called 4 times (10 items / 3 batch size = 4 batches)
    assert mock_session.add_all.call_count == 4

    # Verify flush was called 4 times
    assert mock_session.flush.call_count == 4

    # Verify commit was called once
    assert mock_session.commit.call_count == 1
