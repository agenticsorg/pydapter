from importlib.util import find_spec
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Type checking imports
    from .base import AsyncMigrationAdapter, BaseMigrationAdapter, SyncMigrationAdapter
    from .exceptions import (
        MigrationCreationError,
        MigrationDowngradeError,
        MigrationError,
        MigrationInitError,
        MigrationNotFoundError,
        MigrationUpgradeError,
    )
    from .protocols import AsyncMigrationProtocol, MigrationProtocol
    from .registry import MigrationRegistry
else:
    try:
        # Runtime imports
        from .base import (
            AsyncMigrationAdapter,
            BaseMigrationAdapter,
            SyncMigrationAdapter,
        )
        from .exceptions import (
            MigrationCreationError,
            MigrationDowngradeError,
            MigrationError,
            MigrationInitError,
            MigrationNotFoundError,
            MigrationUpgradeError,
        )
        from .protocols import AsyncMigrationProtocol, MigrationProtocol
        from .registry import MigrationRegistry
    except ImportError:
        # Import error handling
        from ..utils.dependencies import check_migrations_dependencies

        def __getattr__(name):
            check_migrations_dependencies()
            raise ImportError(f"Cannot import {name} because dependencies are missing")


__all__ = [
    "BaseMigrationAdapter",
    "SyncMigrationAdapter",
    "AsyncMigrationAdapter",
    "MigrationProtocol",
    "AsyncMigrationProtocol",
    "MigrationError",
    "MigrationInitError",
    "MigrationCreationError",
    "MigrationUpgradeError",
    "MigrationDowngradeError",
    "MigrationNotFoundError",
    "MigrationRegistry",
]

# Optional imports based on available dependencies
if find_spec("sqlalchemy") is not None and find_spec("alembic") is not None:
    try:
        from .sql.alembic_adapter import (
            AlembicAdapter,  # noqa: F401
            AsyncAlembicAdapter,
        )

        __all__.extend(["AlembicAdapter", "AsyncAlembicAdapter"])
    except ImportError:
        pass
