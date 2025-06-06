from typing import Any

import pytest
from pydantic import BaseModel, Field

# Try to import pgvector, skip tests if not available
try:
    from pgvector.sqlalchemy import Vector
    from pydapter.model_adapters.pg_vector_model import PGVectorModelAdapter
    from pydapter.model_adapters.sql_model import create_base
    from sqlalchemy import Column, Integer, String

    VECTOR_AVAILABLE = True
except ImportError:
    VECTOR_AVAILABLE = False

# Skip all tests in this module if pgvector is not available
pytestmark = pytest.mark.skipif(not VECTOR_AVAILABLE, reason="pgvector not installed")


class EmbeddingSchema(BaseModel):
    id: int | None = None
    text: str
    embedding: list[float] = Field(..., json_schema_extra={"vector_dim": 1536})


class RelatedItem(BaseModel):
    id: int | None = None
    name: str


class EmbeddingWithRelationship(BaseModel):
    id: int | None = None
    text: str
    embedding: list[float] = Field(..., json_schema_extra={"vector_dim": 1536})
    related_items: list[dict[str, Any]] = Field(
        default_factory=list,
        json_schema_extra={
            "relationship": {
                "type": "one_to_many",
                "model": "RelatedItem",
                "back_populates": "embedding",
            }
        },
    )


@pytest.mark.skipif(not VECTOR_AVAILABLE, reason="pgvector not installed")
def test_sql_model_to_pydantic_simple():
    """Test conversion of SQLAlchemy model to Pydantic model."""
    # Create a base class for our models
    Base = create_base()

    # Define a simple model with a vector field
    class EmbeddingSQL(Base):
        __tablename__ = "embeddings"

        id = Column(Integer, primary_key=True)
        text = Column(String)
        embedding = Column(Vector(1536))

    # Convert back to Pydantic
    EmbSchemaRT = PGVectorModelAdapter.sql_model_to_pydantic(EmbeddingSQL)

    # Check that the vector field is correctly mapped
    field = EmbSchemaRT.model_fields["embedding"]
    assert field.json_schema_extra and field.json_schema_extra["vector_dim"] == 1536

    # Check model config
    assert EmbSchemaRT.model_config["from_attributes"] is True
    assert EmbSchemaRT.model_config["orm_mode"] is True
    assert EmbSchemaRT.model_config["orm_mode"] is True


@pytest.mark.skipif(not VECTOR_AVAILABLE, reason="pgvector not installed")
def test_validate_vector_dimensions_with_none_expected_dim():
    """Test vector dimension validation with None expected dimension."""
    # Test with None expected dimension (should pass any dimension)
    vector = [0.1] * 100
    result = PGVectorModelAdapter.validate_vector_dimensions(vector, None)
    assert result is vector

    # Test with a different dimension
    vector = [0.1] * 768
    result = PGVectorModelAdapter.validate_vector_dimensions(vector, None)
    assert result is vector


@pytest.mark.skipif(not VECTOR_AVAILABLE, reason="pgvector not installed")
def test_create_index_with_default_params():
    """Test create_index with default parameters."""
    EmbSQL = PGVectorModelAdapter.pydantic_model_to_sql(EmbeddingSchema)

    # Test HNSW index with default params
    hnsw_index = PGVectorModelAdapter.create_index(
        EmbSQL, "embedding", index_type="hnsw"
    )

    assert hnsw_index.name == "idx_embedding_hnsw"
    assert hnsw_index.columns[0].name == "embedding"
    assert hnsw_index.kwargs["postgresql_using"] == "hnsw"
    assert hnsw_index.kwargs["postgresql_with"] == {}

    # Test IVFFlat index with default params
    ivf_index = PGVectorModelAdapter.create_index(
        EmbSQL, "embedding", index_type="ivfflat"
    )

    assert ivf_index.name == "idx_embedding_ivfflat"
    assert ivf_index.columns[0].name == "embedding"
    assert ivf_index.kwargs["postgresql_using"] == "ivfflat"
    assert ivf_index.kwargs["postgresql_with"] == {}


@pytest.mark.skipif(not VECTOR_AVAILABLE, reason="pgvector not installed")
def test_batch_insert_with_small_batch(mocker):
    """Test batch_insert with a small batch."""
    EmbSQL = PGVectorModelAdapter.pydantic_model_to_sql(EmbeddingSchema)

    # Mock session
    mock_session = mocker.Mock()

    # Create test data - 5 items
    items = [{"text": f"Item {i}", "embedding": [float(i)] * 1536} for i in range(1, 6)]

    # Call batch_insert with default batch_size (1000)
    PGVectorModelAdapter.batch_insert(mock_session, EmbSQL, items)

    # Verify add_all was called once (5 items < 1000 batch size = 1 batch)
    assert mock_session.add_all.call_count == 1

    # Verify flush was called once
    assert mock_session.flush.call_count == 1

    # Verify commit was called once
    assert mock_session.commit.call_count == 1
