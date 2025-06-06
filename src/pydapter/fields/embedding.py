import orjson
from pydapter.fields.types import Field
from pydapter.fields.template import FieldTemplate

__all__ = (
    "EMBEDDING",
    "EMBEDDING_TEMPLATE",
    "validate_embedding",
)


def validate_embedding(value: list[float] | str | None) -> list[float] | None:
    if value is None:
        return []
    if isinstance(value, str):
        try:
            loaded = orjson.loads(value)
            return [float(x) for x in loaded]
        except Exception as e:
            raise ValueError("Invalid embedding string.") from e
    if isinstance(value, list):
        try:
            return [float(x) for x in value]
        except Exception as e:
            raise ValueError("Invalid embedding list.") from e
    raise ValueError("Invalid embedding type; must be list or JSON-encoded string.")


def embedding_validator(cls, v):
    return validate_embedding(v)


# Create as template first for reusability
EMBEDDING_TEMPLATE = FieldTemplate(
    base_type=list[float],
    default_factory=list,
    title="Embedding",
    description="List of floats representing the embedding vector.",
    validator=embedding_validator,
    immutable=True,
    json_schema_extra={"vector_dim": 1536},  # Default OpenAI dimension
)

# Legacy Field for backward compatibility
EMBEDDING = Field(
    name="embedding",
    annotation=list[float],
    default_factory=list,
    title="Embedding",
    description="List of floats representing the embedding vector.",
    immutable=True,
)
