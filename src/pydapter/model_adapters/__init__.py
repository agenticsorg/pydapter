"""
Model adapters for converting between Pydantic and SQLAlchemy models.
"""

from .config import PostgresAdapterConfig, VectorIndexConfig
from .pg_vector_model import PGVectorModelAdapter
from .postgres_model import PostgresModelAdapter
from .sql_model import SQLModelAdapter

# For backward compatibility
from .sql_vector_model import SQLVectorModelAdapter
from .type_registry import TypeRegistry

__all__ = [
    "SQLModelAdapter",
    "PGVectorModelAdapter",
    "PostgresModelAdapter",
    "SQLVectorModelAdapter",  # Deprecated, use PGVectorModelAdapter instead
    "TypeRegistry",
    "VectorIndexConfig",
    "PostgresAdapterConfig",
]
