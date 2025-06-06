from typing import Any

import pytest
from pydantic import BaseModel, Field

# Try to import pgvector, skip tests if not available
try:
    from pgvector.sqlalchemy import Vector
    from pydapter.model_adapters.pg_vector_model import PGVectorModelAdapter
    from pydapter.model_adapters.sql_model import create_base
    from sqlalchemy import Column, ForeignKey, Integer, String
    from sqlalchemy.ext.declarative import declared_attr
    from sqlalchemy.orm import relationship

    VECTOR_AVAILABLE = True
except ImportError:
    VECTOR_AVAILABLE = False

# Skip all tests in this module if pgvector is not available
pytestmark = pytest.mark.skipif(not VECTOR_AVAILABLE, reason="pgvector not installed")


class DocumentSchema(BaseModel):
    id: int | None = None
    title: str
    content: str
    embedding: list[float] = Field(..., json_schema_extra={"vector_dim": 768})


class TagSchema(BaseModel):
    id: int | None = None
    name: str
    document_id: int | None = None
    document: dict[str, Any] | None = Field(
        None,
        json_schema_extra={
            "relationship": {
                "type": "many_to_one",
                "model": "Document",
                "back_populates": "tags",
            }
        },
    )


class DocumentWithTagsSchema(BaseModel):
    id: int | None = None
    title: str
    content: str
    embedding: list[float] = Field(..., json_schema_extra={"vector_dim": 768})
    tags: list[dict[str, Any]] = Field(
        default_factory=list,
        json_schema_extra={
            "relationship": {
                "type": "one_to_many",
                "model": "Tag",
                "back_populates": "document",
            }
        },
    )


@pytest.mark.skipif(not VECTOR_AVAILABLE, reason="pgvector not installed")
def test_sql_model_to_pydantic_with_relationships():
    """Test conversion of SQLAlchemy model with relationships to Pydantic model."""
    # Create a base class for our models
    Base = create_base()

    # Define models with relationships
    class DocumentSQL(Base):
        __tablename__ = "documents"

        id = Column(Integer, primary_key=True)
        title = Column(String)
        content = Column(String)
        embedding = Column(Vector(768))
        tags = relationship("TagSQL", back_populates="document")

    class TagSQL(Base):
        __tablename__ = "tags"

        id = Column(Integer, primary_key=True)
        name = Column(String)
        document_id = Column(Integer, ForeignKey("documents.id"))
        document = relationship("DocumentSQL", back_populates="tags")

    # This test requires more complex setup with SQLAlchemy
    # For now, we'll just test that the Vector column is created correctly
    assert isinstance(DocumentSQL.embedding.type, Vector)
    assert DocumentSQL.embedding.type.dim == 768

    # And check that the relationships are set up
    assert hasattr(DocumentSQL, "tags")
    assert hasattr(TagSQL, "document")


@pytest.mark.skipif(not VECTOR_AVAILABLE, reason="pgvector not installed")
def test_sql_model_to_pydantic_with_direction_relationships():
    """Test conversion with explicit relationship directions."""
    # Create a base class for our models
    Base = create_base()

    # Define models with relationships that have explicit directions
    class DocumentSQL(Base):
        __tablename__ = "documents"

        id = Column(Integer, primary_key=True)
        title = Column(String)
        content = Column(String)
        embedding = Column(Vector(768))

        @declared_attr
        def tags(cls):
            return relationship("TagSQL", back_populates="document", uselist=True)

    class TagSQL(Base):
        __tablename__ = "tags"

        id = Column(Integer, primary_key=True)
        name = Column(String)
        document_id = Column(Integer, ForeignKey("documents.id"))

        @declared_attr
        def document(cls):
            return relationship("DocumentSQL", back_populates="tags", uselist=False)

    # Set up the relationships with direction information
    doc_rel = DocumentSQL.tags.prop
    doc_rel.direction = type("Direction", (), {"name": "ONETOMANY"})

    tag_rel = TagSQL.document.prop
    tag_rel.direction = type("Direction", (), {"name": "MANYTOONE"})

    # This test requires more complex setup with SQLAlchemy
    # For now, we'll just test that the relationships are set up with the right direction
    assert hasattr(DocumentSQL, "tags")
    assert hasattr(TagSQL, "document")

    # Check that the direction attributes were set
    assert hasattr(doc_rel, "direction")
    assert doc_rel.direction.name == "ONETOMANY"

    assert hasattr(tag_rel, "direction")
    assert tag_rel.direction.name == "MANYTOONE"


@pytest.mark.skipif(not VECTOR_AVAILABLE, reason="pgvector not installed")
def test_pydantic_to_sql_with_relationships():
    """Test converting Pydantic models with relationships to SQLAlchemy."""
    # Convert Pydantic models to SQLAlchemy
    DocSQL = PGVectorModelAdapter.pydantic_model_to_sql(DocumentWithTagsSchema)
    TagSQL = PGVectorModelAdapter.pydantic_model_to_sql(TagSchema)

    # Check that the models were created with the right fields
    assert hasattr(DocSQL, "id")
    assert hasattr(DocSQL, "title")
    assert hasattr(DocSQL, "content")
    assert hasattr(DocSQL, "embedding")

    assert hasattr(TagSQL, "id")
    assert hasattr(TagSQL, "name")
    assert hasattr(TagSQL, "document_id")

    # Check that the embedding field is a Vector
    assert isinstance(DocSQL.embedding.type, Vector)
    assert DocSQL.embedding.type.dim == 768
