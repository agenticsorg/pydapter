import pytest
from pydantic import BaseModel, Field
from sqlalchemy import inspect

# Try to import pgvector, skip tests if not available
try:
    from pgvector.sqlalchemy import Vector

    from pydapter.exceptions import ValidationError
    from pydapter.model_adapters.pg_vector_model import PGVectorModelAdapter

    VECTOR_AVAILABLE = True
except ImportError:
    VECTOR_AVAILABLE = False

# Skip all tests in this module if pgvector is not available
pytestmark = pytest.mark.skipif(not VECTOR_AVAILABLE, reason="pgvector not installed")


class EmbeddingSchema(BaseModel):
    id: int | None = None
    text: str
    embedding: list[float] = Field(..., json_schema_extra={"vector_dim": 1536})


class OptionalEmbeddingSchema(BaseModel):
    id: int | None = None
    text: str
    embedding: list[float] | None = Field(None, json_schema_extra={"vector_dim": 768})


@pytest.mark.skipif(not VECTOR_AVAILABLE, reason="pgvector not installed")
def test_vector_column_mapping():
    """Test conversion of Pydantic model with vector field to SQLAlchemy model."""
    EmbSQL = PGVectorModelAdapter.pydantic_model_to_sql(EmbeddingSchema)
    mapper = inspect(EmbSQL)
    emb_col = mapper.columns["embedding"]

    assert isinstance(emb_col.type, Vector)
    assert emb_col.type.dim == 1536
    assert emb_col.nullable is False


@pytest.mark.skipif(not VECTOR_AVAILABLE, reason="pgvector not installed")
def test_optional_vector_column_mapping():
    """Test conversion of Pydantic model with optional vector field."""
    EmbSQL = PGVectorModelAdapter.pydantic_model_to_sql(OptionalEmbeddingSchema)
    mapper = inspect(EmbSQL)
    emb_col = mapper.columns["embedding"]

    assert isinstance(emb_col.type, Vector)
    assert emb_col.type.dim == 768
    assert emb_col.nullable is True


@pytest.mark.skipif(not VECTOR_AVAILABLE, reason="pgvector not installed")
def test_vector_round_trip_metadata():
    """Test that vector dimension metadata is preserved in round-trip conversion."""
    EmbSQL = PGVectorModelAdapter.pydantic_model_to_sql(EmbeddingSchema)
    EmbSchemaRT = PGVectorModelAdapter.sql_model_to_pydantic(EmbSQL)

    field = EmbSchemaRT.model_fields["embedding"]
    # extra metadata about dimension should survive
    assert field.json_schema_extra and field.json_schema_extra["vector_dim"] == 1536


@pytest.mark.skipif(not VECTOR_AVAILABLE, reason="pgvector not installed")
def test_vector_dimension_validation():
    """Test vector dimension validation."""
    # Create a vector with correct dimensions
    valid_vector = [0.1] * 1536
    result = PGVectorModelAdapter.validate_vector_dimensions(valid_vector, 1536)
    assert result is valid_vector

    # Create a vector with incorrect dimensions
    invalid_vector = [0.1] * 1024
    with pytest.raises(ValidationError) as excinfo:
        PGVectorModelAdapter.validate_vector_dimensions(invalid_vector, 1536)

    assert "Vector has 1024 dimensions, expected 1536" in str(excinfo.value)


@pytest.mark.skipif(not VECTOR_AVAILABLE, reason="pgvector not installed")
def test_create_index():
    """Test creating vector indexes."""
    EmbSQL = PGVectorModelAdapter.pydantic_model_to_sql(EmbeddingSchema)

    # Test HNSW index
    hnsw_index = PGVectorModelAdapter.create_index(
        EmbSQL, "embedding", index_type="hnsw", params={"m": 16, "ef_construction": 64}
    )

    assert hnsw_index.name == "idx_embedding_hnsw"
    assert hnsw_index.columns[0].name == "embedding"
    assert hnsw_index.kwargs["postgresql_using"] == "hnsw"
    assert hnsw_index.kwargs["postgresql_with"] == {"m": 16, "ef_construction": 64}

    # Test IVFFlat index
    ivf_index = PGVectorModelAdapter.create_index(
        EmbSQL, "embedding", index_type="ivfflat", params={"lists": 100}
    )

    assert ivf_index.name == "idx_embedding_ivfflat"
    assert ivf_index.columns[0].name == "embedding"
    assert ivf_index.kwargs["postgresql_using"] == "ivfflat"
    assert ivf_index.kwargs["postgresql_with"] == {"lists": 100}

    # Test exact index
    exact_index = PGVectorModelAdapter.create_index(
        EmbSQL, "embedding", index_type="exact"
    )

    assert exact_index.name == "idx_embedding"
    assert exact_index.columns[0].name == "embedding"


@pytest.mark.skipif(not VECTOR_AVAILABLE, reason="pgvector not installed")
def test_find_similar(mocker):
    """Test find_similar method."""
    EmbSQL = PGVectorModelAdapter.pydantic_model_to_sql(EmbeddingSchema)

    # Mock session and execute
    mock_session = mocker.Mock()
    mock_execute = mocker.Mock()
    mock_session.execute = mock_execute

    # Test L2 distance
    vector = [0.1] * 1536
    PGVectorModelAdapter.find_similar(
        mock_session, EmbSQL, "embedding", vector, limit=5, metric="l2"
    )

    # Verify the query was executed
    assert mock_execute.call_count == 1

    # Reset mock
    mock_execute.reset_mock()

    # Test cosine distance
    PGVectorModelAdapter.find_similar(
        mock_session, EmbSQL, "embedding", vector, limit=10, metric="cosine"
    )

    # Verify the query was executed
    assert mock_execute.call_count == 1

    # Reset mock
    mock_execute.reset_mock()

    # Test inner product
    PGVectorModelAdapter.find_similar(
        mock_session, EmbSQL, "embedding", vector, limit=15, metric="inner"
    )

    # Verify the query was executed
    assert mock_execute.call_count == 1


@pytest.mark.skipif(not VECTOR_AVAILABLE, reason="pgvector not installed")
def test_batch_insert(mocker):
    """Test batch_insert method."""
    EmbSQL = PGVectorModelAdapter.pydantic_model_to_sql(EmbeddingSchema)

    # Mock session
    mock_session = mocker.Mock()

    # Create test data
    items = [
        {"text": f"Item {i}", "embedding": [float(i)] * 1536} for i in range(1, 2501)
    ]

    # Call batch_insert
    PGVectorModelAdapter.batch_insert(mock_session, EmbSQL, items, batch_size=1000)

    # Verify add_all was called 3 times (2500 items / 1000 batch size = 3 batches)
    assert mock_session.add_all.call_count == 3

    # Verify flush was called 3 times
    assert mock_session.flush.call_count == 3

    # Verify commit was called once
    assert mock_session.commit.call_count == 1
