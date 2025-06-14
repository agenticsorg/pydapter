"""
pydapter - tiny trait + adapter toolkit.
"""

from .async_core import AsyncAdaptable, AsyncAdapter, AsyncAdapterRegistry
from .core import Adaptable, Adapter, AdapterRegistry
from .fields import (
    ID,
    Embedding,
    Execution,
    Field,
    Undefined,
    UndefinedType,
    create_model,
)

# Temporary compatibility layer for protocols -> traits migration
try:
    from .traits.events import Event, as_event
except ImportError:
    # Fallback to protocols if traits not available yet
    try:
        from .protocols import Event, as_event
    except ImportError:
        # Neither available, will be None
        Event = None
        as_event = None

__all__ = (
    "Adaptable",
    "Adapter",
    "AdapterRegistry",
    "AsyncAdaptable",
    "AsyncAdapter",
    "AsyncAdapterRegistry",
    "Field",
    "create_model",
    "Execution",
    "Embedding",
    "ID",
    "Undefined",
    "UndefinedType",
    "Event",
    "as_event",
)

__version__ = "0.3.3"
