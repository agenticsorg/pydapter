"""
pydapter.migrations.sql.alembic_adapter - Alembic migration adapter implementation.
"""

import os
import shutil
from typing import Any, ClassVar, Optional

import sqlalchemy as sa
from alembic import command, config
from pydapter.migrations.base import AsyncMigrationAdapter, SyncMigrationAdapter
from pydapter.migrations.exceptions import (
    MigrationCreationError,
    MigrationDowngradeError,
    MigrationError,
    MigrationInitError,
    MigrationUpgradeError,
)
from sqlalchemy.ext.asyncio import create_async_engine


class AlembicAdapter(SyncMigrationAdapter):
    """Alembic implementation of the MigrationAdapter interface."""

    migration_key: ClassVar[str] = "alembic"

    def __init__(self, connection_string: str, models_module: Any = None):
        """
        Initialize the Alembic migration adapter.

        Args:
            connection_string: Database connection string
            models_module: Optional module containing SQLAlchemy models
        """
        super().__init__(connection_string, models_module)
        self.engine = sa.create_engine(connection_string)
        self.alembic_cfg = None

    @classmethod
    def init_migrations(cls, directory: str, **kwargs: Any) -> None:
        """
        Initialize migration environment in the specified directory.

        Args:
            directory: Path to the directory where migrations will be stored
            **kwargs: Additional adapter-specific arguments
                connection_string: Database connection string
                models_module: Optional module containing SQLAlchemy models
                template: Optional template to use for migration environment
        """
        try:
            # Create a new instance with the provided connection string
            connection_string = kwargs.get("connection_string")
            if not connection_string:
                raise MigrationInitError(
                    "Connection string is required for Alembic initialization",
                    directory=directory,
                )

            adapter = cls(connection_string, kwargs.get("models_module"))

            # Check if the directory exists and is not empty
            force_clean = kwargs.get("force_clean", False)
            if os.path.exists(directory) and os.listdir(directory):
                if force_clean:
                    # If force_clean is specified, remove the directory and recreate it
                    shutil.rmtree(directory)
                    os.makedirs(directory)
            else:
                # Create the directory if it doesn't exist
                adapter._ensure_directory(directory)

            # Initialize Alembic directory structure
            template = kwargs.get("template", "generic")

            # Create a temporary config file
            ini_path = os.path.join(directory, "alembic.ini")
            with open(ini_path, "w") as f:
                f.write(
                    f"""
[alembic]
script_location = {directory}
sqlalchemy.url = {connection_string}

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
"""
                )

            # Initialize Alembic in the specified directory
            adapter.alembic_cfg = config.Config(ini_path)
            adapter.alembic_cfg.set_main_option("script_location", directory)
            adapter.alembic_cfg.set_main_option("sqlalchemy.url", connection_string)

            # Initialize Alembic directory structure
            try:
                command.init(adapter.alembic_cfg, directory, template=template)
            except Exception as e:
                if "already exists and is not empty" in str(e) and force_clean:
                    # If the directory exists and is not empty, and force_clean is True,
                    # try to clean it up again and retry
                    shutil.rmtree(directory)
                    os.makedirs(directory)
                    command.init(adapter.alembic_cfg, directory, template=template)
                else:
                    raise

            # Update env.py to use the models_module for autogeneration if provided
            if adapter.models_module:
                env_path = os.path.join(directory, "env.py")
                adapter._update_env_py(env_path)

            adapter._migrations_dir = directory
            adapter._initialized = True

            # Return the adapter instance
            return adapter

        except Exception as exc:
            if isinstance(exc, MigrationError):
                raise
            raise MigrationInitError(
                f"Failed to initialize Alembic migrations: {str(exc)}",
                directory=directory,
                original_error=str(exc),
            ) from exc

    def _update_env_py(self, env_path: str) -> None:
        """
        Update the env.py file to use the models_module for autogeneration.

        Args:
            env_path: Path to the env.py file
        """
        if not os.path.exists(env_path):
            return

        # Read the env.py file
        with open(env_path) as f:
            env_content = f.read()

        # Update the target_metadata
        if "target_metadata = None" in env_content:
            # Import the models module
            import_statement = f"from {self.models_module.__name__} import Base\n"
            env_content = env_content.replace(
                "from alembic import context",
                "from alembic import context\n" + import_statement,
            )

            # Update the target_metadata
            env_content = env_content.replace(
                "target_metadata = None", "target_metadata = Base.metadata"
            )

            # Write the updated env.py file
            with open(env_path, "w") as f:
                f.write(env_content)

    def create_migration(
        self, message: str, autogenerate: bool = True, **kwargs: Any
    ) -> str:
        """
        Create a new migration.

        Args:
            message: Description of the migration
            autogenerate: Whether to auto-generate the migration based on model changes
            **kwargs: Additional adapter-specific arguments

        Returns:
            The revision identifier of the created migration

        Raises:
            MigrationCreationError: If creation fails
        """
        try:
            if not self._initialized:
                raise MigrationCreationError(
                    "Migrations have not been initialized. Call init_migrations first."
                )

            # Create the migration
            command.revision(
                self.alembic_cfg,
                message=message,
                autogenerate=autogenerate,
            )

            # Get the revision ID from the latest revision
            from alembic.script import ScriptDirectory

            script = ScriptDirectory.from_config(self.alembic_cfg)
            revision = script.get_current_head()

            return revision
        except Exception as exc:
            if isinstance(exc, MigrationError):
                raise
            raise MigrationCreationError(
                f"Failed to create migration: {str(exc)}",
                autogenerate=autogenerate,
                original_error=str(exc),
            ) from exc

    def upgrade(self, revision: str = "head", **kwargs: Any) -> None:
        """
        Upgrade to the specified revision.

        Args:
            revision: Revision to upgrade to (default: "head" for latest)
            **kwargs: Additional adapter-specific arguments

        Raises:
            MigrationUpgradeError: If upgrade fails
        """
        try:
            if not self._initialized:
                raise MigrationUpgradeError(
                    "Migrations have not been initialized. Call init_migrations first."
                )

            # Upgrade to the specified revision
            command.upgrade(self.alembic_cfg, revision)

            return None
        except Exception as exc:
            if isinstance(exc, MigrationError):
                raise
            raise MigrationUpgradeError(
                f"Failed to upgrade: {str(exc)}",
                revision=revision,
                original_error=str(exc),
            ) from exc

    def downgrade(self, revision: str, **kwargs: Any) -> None:
        """
        Downgrade to the specified revision.

        Args:
            revision: Revision to downgrade to
            **kwargs: Additional adapter-specific arguments

        Raises:
            MigrationDowngradeError: If downgrade fails
        """
        try:
            if not self._initialized:
                raise MigrationDowngradeError(
                    "Migrations have not been initialized. Call init_migrations first."
                )

            # Downgrade to the specified revision
            command.downgrade(self.alembic_cfg, revision)

            return None
        except Exception as exc:
            if isinstance(exc, MigrationError):
                raise
            raise MigrationDowngradeError(
                f"Failed to downgrade: {str(exc)}",
                revision=revision,
                original_error=str(exc),
            ) from exc

    def get_current_revision(self, **kwargs: Any) -> Optional[str]:
        """
        Get the current revision.

        Args:
            **kwargs: Additional adapter-specific arguments

        Returns:
            The current revision, or None if no migrations have been applied

        Raises:
            MigrationError: If getting the current revision fails
        """
        try:
            if not self._initialized:
                raise MigrationError(
                    "Migrations have not been initialized. Call init_migrations first."
                )

            # Get the current revision
            from alembic.migration import MigrationContext

            # Get the database connection
            connection = self.engine.connect()

            # Create a migration context
            migration_context = MigrationContext.configure(connection)

            # Get the current revision
            current_revision = migration_context.get_current_revision()

            # Close the connection
            connection.close()

            return current_revision
        except Exception as exc:
            if isinstance(exc, MigrationError):
                raise
            raise MigrationError(
                f"Failed to get current revision: {str(exc)}",
                original_error=exc,
            ) from exc

    def get_migration_history(self, **kwargs: Any) -> list[dict]:
        """
        Get the migration history.

        Args:
            **kwargs: Additional adapter-specific arguments

        Returns:
            A list of dictionaries containing migration information

        Raises:
            MigrationError: If getting the migration history fails
        """
        try:
            if not self._initialized:
                raise MigrationError(
                    "Migrations have not been initialized. Call init_migrations first."
                )

            # Get the migration history
            from alembic.script import ScriptDirectory

            script = ScriptDirectory.from_config(self.alembic_cfg)

            # Get all revisions
            revisions = []
            for revision in script.walk_revisions():
                revisions.append({
                    "revision": revision.revision,
                    "message": revision.doc,
                    "created": None,  # Alembic doesn't store creation dates
                })

            return revisions
        except Exception as exc:
            if isinstance(exc, MigrationError):
                raise
            raise MigrationError(
                f"Failed to get migration history: {str(exc)}",
                original_error=exc,
            ) from exc


class AsyncAlembicAdapter(AsyncMigrationAdapter):
    """Async implementation of the Alembic migration adapter."""

    migration_key: ClassVar[str] = "async_alembic"

    def __init__(self, connection_string: str, models_module: Any = None):
        """
        Initialize the async Alembic migration adapter.

        Args:
            connection_string: Database connection string
            models_module: Optional module containing SQLAlchemy models
        """
        super().__init__(connection_string, models_module)
        self.engine = create_async_engine(connection_string)
        self.alembic_cfg = None

    async def _update_env_py_async(self, env_path: str) -> None:
        """
        Update the env.py file to use the models_module for autogeneration.

        Args:
            env_path: Path to the env.py file
        """
        if not os.path.exists(env_path):
            return

        # Read the env.py file
        with open(env_path) as f:
            env_content = f.read()

        # Update the target_metadata
        if "target_metadata = None" in env_content:
            # Import the models module
            import_statement = f"from {self.models_module.__name__} import Base\n"
            env_content = env_content.replace(
                "from alembic import context",
                "from alembic import context\n" + import_statement,
            )

            # Update the target_metadata
            env_content = env_content.replace(
                "target_metadata = None", "target_metadata = Base.metadata"
            )

            # Write the updated env.py file
            with open(env_path, "w") as f:
                f.write(env_content)
