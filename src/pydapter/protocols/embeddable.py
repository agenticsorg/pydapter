from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from pydantic import BaseModel
from pydapter.fields.types import Embedding

if TYPE_CHECKING:
    pass


@runtime_checkable
class Embeddable(Protocol):
    content: str | None
    embedding: Embedding


class EmbeddableMixin:
    """Mixin class for embedding functionality."""

    if TYPE_CHECKING:
        content: str | None
        embedding: Embedding

    @property
    def n_dim(self) -> int:
        """Get the number of dimensions of the embedding."""
        return len(self.embedding)

    @staticmethod
    def parse_embedding_response(
        x: dict | list | tuple | BaseModel,
    ) -> Embedding:
        """Parse the embedding response from OpenAI or other sources."""
        return parse_embedding_response(x)


def parse_embedding_response(x) -> list[float] | Any:
    # parse openai response
    if (
        isinstance(x, BaseModel)
        and hasattr(x, "data")
        and len(x.data) > 0
        and hasattr(x.data[0], "embedding")
    ):
        return x.data[0].embedding

    if isinstance(x, (list, tuple)):
        if len(x) > 0 and all(isinstance(i, float) for i in x):
            return x  # type: ignore[return-value]
        if len(x) == 1 and isinstance(x[0], (dict, BaseModel)):
            return parse_embedding_response(x[0])

    # parse dict response
    if isinstance(x, dict):
        # parse openai format response

        if "data" in x:
            data = x.get("data")
            if data is not None and len(data) > 0 and isinstance(data[0], dict):
                return parse_embedding_response(data[0])

        # parse {"embedding": []} response
        if "embedding" in x:
            return parse_embedding_response(x["embedding"])

    return x  # type: ignore[return-value]
