# config.py
from __future__ import annotations

from typing import Any, Dict, Literal

from pydantic import BaseModel, Field, field_validator


class VectorIndexConfig(BaseModel):
    """Configuration for vector indexing."""

    index_type: Literal["hnsw", "ivfflat", "exact"] = "hnsw"
    params: Dict[str, Any] = Field(default_factory=dict)

    # HNSW parameters
    m: int = 16  # HNSW parameter: max number of connections per node
    ef_construction: int = 64  # HNSW build-time parameter

    # IVFFlat parameters
    lists: int = 100  # Number of IVF lists (clusters)
    probes: int = 10  # Number of lists to search at query time

    @field_validator("index_type")
    @classmethod
    def validate_index_type(cls, v):
        """Validate that the index type is supported."""
        if v not in ["hnsw", "ivfflat", "exact"]:
            raise ValueError(f"Unsupported index type: {v}")
        return v

    def get_params(self) -> Dict[str, Any]:
        """
        Get the parameters for the specified index type.

        Returns:
            A dictionary of parameters for the index
        """
        params = self.params.copy()

        if self.index_type == "hnsw" and not params:
            params = {
                "m": self.m,
                "ef_construction": self.ef_construction,
            }
        elif self.index_type == "ivfflat" and not params:
            params = {
                "lists": self.lists,
            }

        return params


class PostgresAdapterConfig(BaseModel):
    """Configuration for PostgreSQL adapters."""

    schema: str = "public"
    batch_size: int = Field(default=1000, gt=0)
    vector_index_config: VectorIndexConfig = Field(default_factory=VectorIndexConfig)
    validate_vector_dimensions: bool = True

    @field_validator("batch_size")
    @classmethod
    def validate_batch_size(cls, v):
        """Validate that the batch size is positive."""
        if v <= 0:
            raise ValueError("Batch size must be positive")
        return v
