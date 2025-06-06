import pytest
from pydantic import BaseModel, Field
from sqlalchemy import inspect

# Try to import pgvector, skip tests if not available
try:
    from pgvector.sqlalchemy import Vector
    from pydapter.model_adapters.sql_vector_model import SQLVectorModelAdapter

    VECTOR_AVAILABLE = True
except ImportError:
    VECTOR_AVAILABLE = False

# Skip all tests in this module if pgvector is not available
pytestmark = pytest.mark.skipif(not VECTOR_AVAILABLE, reason="pgvector not installed")


# ---------- Sample Pydantic models with vector fields -----------------------------------
class EmbeddingSchema(BaseModel):
    id: int | None = None
    text: str
    embedding: list[float] = Field(..., json_schema_extra={"vector_dim": 1536})


class OptionalEmbeddingSchema(BaseModel):
    id: int | None = None
    text: str
    embedding: list[float] | None = Field(None, json_schema_extra={"vector_dim": 768})


# ---------- Tests for SQLVectorModelAdapter ---------------------------------------------
@pytest.mark.skipif(not VECTOR_AVAILABLE, reason="pgvector not installed")
def test_vector_column_mapping():
    """Test conversion of Pydantic model with vector field to SQLAlchemy model"""
    EmbSQL = SQLVectorModelAdapter.pydantic_model_to_sql(EmbeddingSchema)
    mapper = inspect(EmbSQL)
    emb_col = mapper.columns["embedding"]

    assert isinstance(emb_col.type, Vector)
    assert emb_col.type.dim == 1536
    assert emb_col.nullable is False


@pytest.mark.skipif(not VECTOR_AVAILABLE, reason="pgvector not installed")
def test_optional_vector_column_mapping():
    """Test conversion of Pydantic model with optional vector field"""
    EmbSQL = SQLVectorModelAdapter.pydantic_model_to_sql(OptionalEmbeddingSchema)
    mapper = inspect(EmbSQL)
    emb_col = mapper.columns["embedding"]

    assert isinstance(emb_col.type, Vector)
    assert emb_col.type.dim == 768
    assert emb_col.nullable is True


@pytest.mark.skipif(not VECTOR_AVAILABLE, reason="pgvector not installed")
def test_vector_round_trip_metadata():
    """Test that vector dimension metadata is preserved in round-trip conversion"""
    EmbSQL = SQLVectorModelAdapter.pydantic_model_to_sql(EmbeddingSchema)
    EmbSchemaRT = SQLVectorModelAdapter.sql_model_to_pydantic(EmbSQL)

    field = EmbSchemaRT.model_fields["embedding"]
    # extra metadata about dimension should survive
    assert field.json_schema_extra and field.json_schema_extra["vector_dim"] == 1536


@pytest.mark.skipif(not VECTOR_AVAILABLE, reason="pgvector not installed")
def test_vector_without_dimension():
    """Test handling of vector fields without explicit dimension"""

    class SimpleVectorSchema(BaseModel):
        id: int | None = None
        embedding: list[float]

    EmbSQL = SQLVectorModelAdapter.pydantic_model_to_sql(SimpleVectorSchema)
    mapper = inspect(EmbSQL)
    emb_col = mapper.columns["embedding"]

    assert isinstance(emb_col.type, Vector)
    assert not hasattr(emb_col.type, "dim") or emb_col.type.dim is None


@pytest.mark.skipif(not VECTOR_AVAILABLE, reason="pgvector not installed")
def test_mixed_model_conversion():
    """Test model with both vector and scalar fields"""

    class MixedSchema(BaseModel):
        id: int | None = None
        name: str
        description: str | None = None
        embedding: list[float] = Field(..., json_schema_extra={"vector_dim": 384})

    MixedSQL = SQLVectorModelAdapter.pydantic_model_to_sql(MixedSchema)
    mapper = inspect(MixedSQL)
    cols = {c.key: c for c in mapper.columns}

    # Check vector field
    assert isinstance(cols["embedding"].type, Vector)
    assert cols["embedding"].type.dim == 384

    # Check scalar fields
    assert cols["id"].primary_key  # Check it's a primary key instead of type
    assert cols["name"].nullable is False  # Check it's not nullable
    assert cols["description"].nullable is True

    # Round-trip
    MixedSchemaRT = SQLVectorModelAdapter.sql_model_to_pydantic(MixedSQL)
    fields = MixedSchemaRT.model_fields

    assert (
        fields["embedding"].json_schema_extra
        and fields["embedding"].json_schema_extra["vector_dim"] == 384
    )
    assert fields["name"].is_required()
    assert not fields["description"].is_required()


@pytest.mark.skipif(not VECTOR_AVAILABLE, reason="pgvector not installed")
def test_inheritance_from_base_adapter():
    """Test that SQLVectorModelAdapter inherits and extends SQLModelAdapter functionality"""

    # Should handle regular scalar types just like the base adapter
    class UserSchema(BaseModel):
        id: int | None = None
        name: str
        email: str | None = None

    UserSQL = SQLVectorModelAdapter.pydantic_model_to_sql(UserSchema)
    mapper = inspect(UserSQL)
    cols = {c.key: c for c in mapper.columns}

    assert cols["id"].primary_key  # Check it's a primary key
    assert cols["name"].nullable is False
    assert cols["email"].nullable is True
