"""
Integration tests for migrations in pydapter.migrations.
"""

import os
import shutil
import tempfile
from typing import ClassVar, Optional

import pytest
import sqlalchemy as sa
from pydapter.migrations.base import SyncMigrationAdapter
from pydapter.migrations.registry import MigrationRegistry
from pydapter.migrations.sql.alembic_adapter import AlembicAdapter
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import declarative_base


class TestMigrationsIntegration:
    """Integration tests for migrations."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for migrations."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def sqlite_engine(self, temp_dir):
        """Create a SQLite engine for testing."""
        db_path = os.path.join(temp_dir, "test.db")
        engine = create_engine(f"sqlite:///{db_path}")
        yield engine
        engine.dispose()

    @pytest.fixture
    def base_model(self):
        """Create a SQLAlchemy declarative base for testing."""
        return declarative_base()

    @pytest.fixture
    def registry(self):
        """Create a migration registry for testing."""
        # Create a new registry
        registry = MigrationRegistry()

        # Clear any existing adapters
        registry._reg.clear()

        # Register the AlembicAdapter
        registry.register(AlembicAdapter)

        return registry

    def test_end_to_end_workflow(self, temp_dir, sqlite_engine, base_model, registry):
        """Test the end-to-end migration workflow."""
        # Create a migrations directory
        migrations_dir = os.path.join(temp_dir, "migrations")

        # Get the AlembicAdapter from the registry
        adapter_cls = registry.get("alembic")

        # Initialize the adapter
        # Create a connection string for the SQLite database
        db_path = os.path.join(temp_dir, "test.db")
        connection_string = f"sqlite:///{db_path}"

        adapter = adapter_cls(
            connection_string=connection_string,
            models_module=None,  # We'll use the base directly
        )

        # Set the base model and engine
        adapter._base = base_model
        adapter._engine = sqlite_engine

        # Initialize migrations
        adapter = adapter.init_migrations(
            migrations_dir, connection_string=connection_string, force_clean=True
        )

        # Check that the migrations directory was created
        assert os.path.exists(migrations_dir)
        assert os.path.isdir(migrations_dir)

        # Define the initial model
        class User(base_model):
            __tablename__ = "users"

            id = Column(Integer, primary_key=True)
            name = Column(String(50), nullable=False)

        # Create the initial migration
        revision1 = adapter.create_migration(
            "Create users table",
            autogenerate=False,
        )

        # Create a migration script with table creation
        with open(
            os.path.join(
                migrations_dir, "versions", f"{revision1}_create_users_table.py"
            ),
            "w",
        ) as f:
            f.write(
                f"""
\"\"\"Create users table

Revision ID: {revision1}
Revises:
Create Date: 2025-05-16 12:00:00.000000

\"\"\"

revision = '{revision1}'
down_revision = None
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade():
    op.drop_table('users')
"""
            )

        # Upgrade to the initial revision
        adapter.upgrade()

        # Check that the table was created
        with sqlite_engine.connect() as conn:
            result = conn.execute(
                sa.text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
                )
            )
            assert result.scalar() == "users"

        # We don't need to define a new model class, just create the migration

        # Create the second migration
        revision2 = adapter.create_migration(
            "Add email column",
            autogenerate=False,
        )

        # Create a migration script with column addition
        with open(
            os.path.join(
                migrations_dir, "versions", f"{revision2}_add_email_column.py"
            ),
            "w",
        ) as f:
            f.write(
                f"""
\"\"\"Add email column

Revision ID: {revision2}
Revises: {revision1}
Create Date: 2025-05-16 12:00:00.000000

\"\"\"

revision = '{revision2}'
down_revision = '{revision1}'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column('users', sa.Column('email', sa.String(length=100), nullable=False))

def downgrade():
    op.drop_column('users', 'email')
"""
            )

        # Upgrade to the second revision
        adapter.upgrade()

        # Check that the column was added
        with sqlite_engine.connect() as conn:
            result = conn.execute(sa.text("PRAGMA table_info(users)"))
            columns = [row[1] for row in result.fetchall()]
            assert "email" in columns

        # Get the current revision
        current_revision = adapter.get_current_revision()
        assert current_revision is not None
        assert revision2 in current_revision

        # Get the migration history
        history = adapter.get_migration_history()
        assert len(history) == 2

        # The order of revisions in the history might vary, so we'll check that both revisions are present
        revisions = [h["revision"] for h in history]
        assert revision1 in revisions
        assert revision2 in revisions

        # Downgrade to the first revision
        adapter.downgrade(revision1)

        # Check that the column was removed
        with sqlite_engine.connect() as conn:
            result = conn.execute(sa.text("PRAGMA table_info(users)"))
            columns = [row[1] for row in result.fetchall()]
            assert "email" not in columns

        # Downgrade to the base revision
        adapter.downgrade("base")

        # Check that the table was dropped
        with sqlite_engine.connect() as conn:
            result = conn.execute(
                sa.text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
                )
            )
            assert result.scalar() is None

    def test_multiple_models(self, temp_dir, sqlite_engine, base_model, registry):
        """Test migrations with multiple models."""
        # Create a migrations directory
        migrations_dir = os.path.join(temp_dir, "migrations")

        # Get the AlembicAdapter from the registry
        adapter_cls = registry.get("alembic")

        # Initialize the adapter
        # Create a connection string for the SQLite database
        db_path = os.path.join(temp_dir, "test.db")
        connection_string = f"sqlite:///{db_path}"

        adapter = adapter_cls(
            connection_string=connection_string,
            models_module=None,  # We'll use the base directly
        )

        # Set the base model and engine
        adapter._base = base_model
        adapter._engine = sqlite_engine

        # Initialize migrations
        adapter = adapter.init_migrations(
            migrations_dir, connection_string=connection_string, force_clean=True
        )

        # Define the initial models
        class User(base_model):
            __tablename__ = "users"

            id = Column(Integer, primary_key=True)
            name = Column(String(50), nullable=False)

        class Product(base_model):
            __tablename__ = "products"

            id = Column(Integer, primary_key=True)
            name = Column(String(50), nullable=False)
            price = Column(Integer, nullable=False)

        # Create the initial migration
        revision1 = adapter.create_migration(
            "Create users and products tables",
            autogenerate=False,
        )

        # Create a migration script with table creation
        with open(
            os.path.join(
                migrations_dir,
                "versions",
                f"{revision1}_create_users_and_products_tables.py",
            ),
            "w",
        ) as f:
            f.write(
                f"""
\"\"\"Create users and products tables

Revision ID: {revision1}
Revises:
Create Date: 2025-05-16 12:00:00.000000

\"\"\"

revision = '{revision1}'
down_revision = None
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table('products',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('price', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade():
    op.drop_table('products')
    op.drop_table('users')
"""
            )

        # Upgrade to the initial revision
        adapter.upgrade()

        # Check that the tables were created
        with sqlite_engine.connect() as conn:
            result = conn.execute(
                sa.text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
                )
            )
            assert result.scalar() == "users"

            result = conn.execute(
                sa.text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='products'"
                )
            )
            assert result.scalar() == "products"

        # We don't need to define new model classes, just create the migration

        # Create the second migration
        revision2 = adapter.create_migration(
            "Add email and description columns",
            autogenerate=False,
        )

        # Create a migration script with column addition
        with open(
            os.path.join(
                migrations_dir,
                "versions",
                f"{revision2}_add_email_and_description_columns.py",
            ),
            "w",
        ) as f:
            f.write(
                f"""
\"\"\"Add email and description columns

Revision ID: {revision2}
Revises: {revision1}
Create Date: 2025-05-16 12:00:00.000000

\"\"\"

revision = '{revision2}'
down_revision = '{revision1}'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column('users', sa.Column('email', sa.String(length=100), nullable=False))
    op.add_column('products', sa.Column('description', sa.String(length=200), nullable=True))

def downgrade():
    op.drop_column('products', 'description')
    op.drop_column('users', 'email')
"""
            )

        # Upgrade to the second revision
        adapter.upgrade()

        # Check that the column was added
        with sqlite_engine.connect() as conn:
            result = conn.execute(sa.text("PRAGMA table_info(users)"))
            columns = [row[1] for row in result.fetchall()]
            assert "email" in columns

            result = conn.execute(sa.text("PRAGMA table_info(products)"))
            product_columns = [row[1] for row in result.fetchall()]
            assert "description" in product_columns

        # Downgrade to the first revision
        adapter.downgrade(revision1)

        # Check that the columns were removed
        with sqlite_engine.connect() as conn:
            result = conn.execute(sa.text("PRAGMA table_info(users)"))
            user_columns = [row[1] for row in result.fetchall()]
            assert "email" not in user_columns

            result = conn.execute(sa.text("PRAGMA table_info(products)"))
            product_columns = [row[1] for row in result.fetchall()]
            assert "description" not in product_columns

    def test_custom_migration_adapter(self, temp_dir):
        """Test creating and using a custom migration adapter."""
        # Create a migrations directory
        migrations_dir = os.path.join(temp_dir, "migrations")

        # Create a custom migration adapter
        class CustomMigrationAdapter(SyncMigrationAdapter):
            migration_key: ClassVar[str] = "custom"

            _migrations: ClassVar[list[str]] = []
            _current_revision: ClassVar[Optional[str]] = None

            @classmethod
            def init_migrations(cls, directory: str, **kwargs) -> None:
                cls._migrations = []
                cls._current_revision = None
                os.makedirs(directory, exist_ok=True)
                return None

            @classmethod
            def create_migration(
                cls, message: str, autogenerate: bool = True, **kwargs
            ) -> str:
                revision = f"rev_{len(cls._migrations) + 1}"
                cls._migrations.append((revision, message))
                return revision

            @classmethod
            def upgrade(cls, revision: str = "head", **kwargs) -> None:
                if revision == "head":
                    cls._current_revision = (
                        cls._migrations[-1][0] if cls._migrations else None
                    )
                else:
                    for i, (rev, _) in enumerate(cls._migrations):
                        if rev == revision:
                            cls._current_revision = rev
                            break
                return None

            @classmethod
            def downgrade(cls, revision: str, **kwargs) -> None:
                if revision == "base":
                    cls._current_revision = None
                else:
                    for i, (rev, _) in enumerate(cls._migrations):
                        if rev == revision:
                            cls._current_revision = rev
                            break
                return None

            @classmethod
            def get_current_revision(cls, **kwargs) -> Optional[str]:
                return cls._current_revision

            @classmethod
            def get_migration_history(cls, **kwargs) -> list[dict]:
                return [
                    {"revision": rev, "message": msg} for rev, msg in cls._migrations
                ]

        # Register the custom adapter
        registry = MigrationRegistry()
        registry.register(CustomMigrationAdapter)

        # Get the custom adapter from the registry
        adapter_cls = registry.get("custom")

        # Initialize the adapter
        adapter = adapter_cls(connection_string="dummy")

        # Initialize migrations
        adapter.init_migrations(migrations_dir)

        # Create migrations
        revision1 = adapter.create_migration("First migration")
        revision2 = adapter.create_migration("Second migration")

        # Check that the migrations were created
        assert revision1 == "rev_1"
        assert revision2 == "rev_2"

        # Upgrade to the latest revision
        adapter.upgrade()

        # Check the current revision
        assert adapter.get_current_revision() == "rev_2"

        # Downgrade to the first revision
        adapter.downgrade(revision1)

        # Check the current revision
        assert adapter.get_current_revision() == "rev_1"

        # Downgrade to the base revision
        adapter.downgrade("base")

        # Check the current revision
        assert adapter.get_current_revision() is None

        # Get the migration history
        history = adapter.get_migration_history()
        assert len(history) == 2

        # Check that both revisions are present with correct messages
        rev1_entry = next((h for h in history if h["revision"] == "rev_1"), None)
        rev2_entry = next((h for h in history if h["revision"] == "rev_2"), None)

        assert rev1_entry is not None
        assert rev1_entry["message"] == "First migration"
        assert rev2_entry is not None
        assert rev2_entry["message"] == "Second migration"
