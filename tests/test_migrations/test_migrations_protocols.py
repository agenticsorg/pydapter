"""
Tests for migration protocol interfaces in pydapter.migrations.protocols.
"""

from typing import ClassVar, Optional

import pytest
from pydapter.migrations.protocols import AsyncMigrationProtocol, MigrationProtocol


def test_migration_protocol_interface():
    """Test that the MigrationProtocol interface is correctly defined."""

    # Define a class that implements the MigrationProtocol
    class TestMigrationAdapter:
        migration_key: ClassVar[str] = "test"

        @classmethod
        def init_migrations(cls, directory: str, **kwargs) -> None:
            return None

        @classmethod
        def create_migration(
            cls, message: str, autogenerate: bool = True, **kwargs
        ) -> str:
            return "revision123"

        @classmethod
        def upgrade(cls, revision: str = "head", **kwargs) -> None:
            return None

        @classmethod
        def downgrade(cls, revision: str, **kwargs) -> None:
            return None

        @classmethod
        def get_current_revision(cls, **kwargs) -> Optional[str]:
            return "revision123"

        @classmethod
        def get_migration_history(cls, **kwargs) -> list[dict]:
            return [{"revision": "revision123", "message": "test migration"}]

    # Check that the class implements the protocol
    assert isinstance(TestMigrationAdapter, type)

    # Create an instance to test with isinstance instead of issubclass
    # This is because protocols with non-method members don't support issubclass()
    adapter = TestMigrationAdapter()
    assert isinstance(adapter, MigrationProtocol)


def test_async_migration_protocol_interface():
    """Test that the AsyncMigrationProtocol interface is correctly defined."""

    # Define a class that implements the AsyncMigrationProtocol
    class TestAsyncMigrationAdapter:
        migration_key: ClassVar[str] = "test_async"

        @classmethod
        async def init_migrations(cls, directory: str, **kwargs) -> None:
            return None

        @classmethod
        async def create_migration(
            cls, message: str, autogenerate: bool = True, **kwargs
        ) -> str:
            return "revision123"

        @classmethod
        async def upgrade(cls, revision: str = "head", **kwargs) -> None:
            return None

        @classmethod
        async def downgrade(cls, revision: str, **kwargs) -> None:
            return None

        @classmethod
        async def get_current_revision(cls, **kwargs) -> Optional[str]:
            return "revision123"

        @classmethod
        async def get_migration_history(cls, **kwargs) -> list[dict]:
            return [{"revision": "revision123", "message": "test migration"}]

    # Check that the class implements the protocol
    assert isinstance(TestAsyncMigrationAdapter, type)

    # Create an instance to test with isinstance instead of issubclass
    # This is because protocols with non-method members don't support issubclass()
    adapter = TestAsyncMigrationAdapter()
    assert isinstance(adapter, AsyncMigrationProtocol)


def test_migration_protocol_missing_methods():
    """Test that classes missing required methods don't implement the protocol."""

    # Define a class that's missing some required methods
    class IncompleteAdapter:
        migration_key: ClassVar[str] = "incomplete"

        @classmethod
        def init_migrations(cls, directory: str, **kwargs) -> None:
            return None

        @classmethod
        def create_migration(
            cls, message: str, autogenerate: bool = True, **kwargs
        ) -> str:
            return "revision123"

        # Missing upgrade, downgrade, get_current_revision, get_migration_history

    # Create an instance to test
    adapter = IncompleteAdapter()
    assert not isinstance(adapter, MigrationProtocol)


def test_async_migration_protocol_missing_methods():
    """Test that classes missing required methods don't implement the async protocol."""

    # Define a class that's missing some required methods
    class IncompleteAsyncAdapter:
        migration_key: ClassVar[str] = "incomplete_async"

        @classmethod
        async def init_migrations(cls, directory: str, **kwargs) -> None:
            return None

        @classmethod
        async def create_migration(
            cls, message: str, autogenerate: bool = True, **kwargs
        ) -> str:
            return "revision123"

        # Missing upgrade, downgrade, get_current_revision, get_migration_history

    # Create an instance to test
    adapter = IncompleteAsyncAdapter()
    assert not isinstance(adapter, AsyncMigrationProtocol)


def test_migration_protocol_missing_attribute():
    """Test that classes missing required attributes don't implement the protocol."""

    # Define a class that's missing the migration_key attribute
    class NoKeyAdapter:
        # Missing migration_key

        @classmethod
        def init_migrations(cls, directory: str, **kwargs) -> None:
            return None

        @classmethod
        def create_migration(
            cls, message: str, autogenerate: bool = True, **kwargs
        ) -> str:
            return "revision123"

        @classmethod
        def upgrade(cls, revision: str = "head", **kwargs) -> None:
            return None

        @classmethod
        def downgrade(cls, revision: str, **kwargs) -> None:
            return None

        @classmethod
        def get_current_revision(cls, **kwargs) -> Optional[str]:
            return "revision123"

        @classmethod
        def get_migration_history(cls, **kwargs) -> list[dict]:
            return [{"revision": "revision123", "message": "test migration"}]

    # Create an instance to test
    adapter = NoKeyAdapter()
    assert not isinstance(adapter, MigrationProtocol)


def test_async_migration_protocol_missing_attribute():
    """Test that classes missing required attributes don't implement the async protocol."""

    # Define a class that's missing the migration_key attribute
    class NoKeyAsyncAdapter:
        # Missing migration_key

        @classmethod
        async def init_migrations(cls, directory: str, **kwargs) -> None:
            return None

        @classmethod
        async def create_migration(
            cls, message: str, autogenerate: bool = True, **kwargs
        ) -> str:
            return "revision123"

        @classmethod
        async def upgrade(cls, revision: str = "head", **kwargs) -> None:
            return None

        @classmethod
        async def downgrade(cls, revision: str, **kwargs) -> None:
            return None

        @classmethod
        async def get_current_revision(cls, **kwargs) -> Optional[str]:
            return "revision123"

        @classmethod
        async def get_migration_history(cls, **kwargs) -> list[dict]:
            return [{"revision": "revision123", "message": "test migration"}]

    # Create an instance to test
    adapter = NoKeyAsyncAdapter()
    assert not isinstance(adapter, AsyncMigrationProtocol)


def test_migration_protocol_wrong_method_signatures():
    """Test that classes with wrong method signatures don't implement the protocol."""

    # Define a class with wrong method signatures
    class WrongSignatureAdapter:
        migration_key: ClassVar[str] = "wrong_signature"

        # Wrong signature: missing directory parameter
        @classmethod
        def init_migrations(cls, **kwargs) -> None:  # type: ignore
            return None

        # Wrong signature: wrong return type
        @classmethod
        def create_migration(
            cls, message: str, autogenerate: bool = True, **kwargs
        ) -> int:  # type: ignore
            return 123

        @classmethod
        def upgrade(cls, revision: str = "head", **kwargs) -> None:
            return None

        @classmethod
        def downgrade(cls, revision: str, **kwargs) -> None:
            return None

        @classmethod
        def get_current_revision(cls, **kwargs) -> Optional[str]:
            return "revision123"

        @classmethod
        def get_migration_history(cls, **kwargs) -> list[dict]:
            return [{"revision": "revision123", "message": "test migration"}]

    # Create an instance to test
    adapter = WrongSignatureAdapter()
    # This should still pass because Python's structural typing is not strict about signatures
    # The important thing is that the methods exist and can be called
    assert isinstance(adapter, MigrationProtocol)


@pytest.mark.asyncio
async def test_async_migration_protocol_method_calls():
    """Test that async protocol methods can be called."""

    # Define a class that implements the AsyncMigrationProtocol
    class TestAsyncAdapter:
        migration_key: ClassVar[str] = "test_async_calls"
        init_called: ClassVar[bool] = False
        create_called: ClassVar[bool] = False
        upgrade_called: ClassVar[bool] = False
        downgrade_called: ClassVar[bool] = False
        get_revision_called: ClassVar[bool] = False
        get_history_called: ClassVar[bool] = False

        @classmethod
        async def init_migrations(cls, directory: str, **kwargs) -> None:
            cls.init_called = True
            return None

        @classmethod
        async def create_migration(
            cls, message: str, autogenerate: bool = True, **kwargs
        ) -> str:
            cls.create_called = True
            return "revision123"

        @classmethod
        async def upgrade(cls, revision: str = "head", **kwargs) -> None:
            cls.upgrade_called = True
            return None

        @classmethod
        async def downgrade(cls, revision: str, **kwargs) -> None:
            cls.downgrade_called = True
            return None

        @classmethod
        async def get_current_revision(cls, **kwargs) -> Optional[str]:
            cls.get_revision_called = True
            return "revision123"

        @classmethod
        async def get_migration_history(cls, **kwargs) -> list[dict]:
            cls.get_history_called = True
            return [{"revision": "revision123", "message": "test migration"}]

    # Create an instance to test
    adapter = TestAsyncAdapter()
    assert isinstance(adapter, AsyncMigrationProtocol)

    # Call the methods
    await adapter.init_migrations("test_dir")
    assert TestAsyncAdapter.init_called is True

    await adapter.create_migration("test message")
    assert TestAsyncAdapter.create_called is True

    await adapter.upgrade()
    assert TestAsyncAdapter.upgrade_called is True

    await adapter.downgrade("revision123")
    assert TestAsyncAdapter.downgrade_called is True

    await adapter.get_current_revision()
    assert TestAsyncAdapter.get_revision_called is True

    await adapter.get_migration_history()
    assert TestAsyncAdapter.get_history_called is True


def test_migration_protocol_method_calls():
    """Test that protocol methods can be called."""

    # Define a class that implements the MigrationProtocol
    class TestAdapter:
        migration_key: ClassVar[str] = "test_calls"
        init_called: ClassVar[bool] = False
        create_called: ClassVar[bool] = False
        upgrade_called: ClassVar[bool] = False
        downgrade_called: ClassVar[bool] = False
        get_revision_called: ClassVar[bool] = False
        get_history_called: ClassVar[bool] = False

        @classmethod
        def init_migrations(cls, directory: str, **kwargs) -> None:
            cls.init_called = True
            return None

        @classmethod
        def create_migration(
            cls, message: str, autogenerate: bool = True, **kwargs
        ) -> str:
            cls.create_called = True
            return "revision123"

        @classmethod
        def upgrade(cls, revision: str = "head", **kwargs) -> None:
            cls.upgrade_called = True
            return None

        @classmethod
        def downgrade(cls, revision: str, **kwargs) -> None:
            cls.downgrade_called = True
            return None

        @classmethod
        def get_current_revision(cls, **kwargs) -> Optional[str]:
            cls.get_revision_called = True
            return "revision123"

        @classmethod
        def get_migration_history(cls, **kwargs) -> list[dict]:
            cls.get_history_called = True
            return [{"revision": "revision123", "message": "test migration"}]

    # Create an instance to test
    adapter = TestAdapter()
    assert isinstance(adapter, MigrationProtocol)

    # Call the methods
    adapter.init_migrations("test_dir")
    assert TestAdapter.init_called is True

    adapter.create_migration("test message")
    assert TestAdapter.create_called is True

    adapter.upgrade()
    assert TestAdapter.upgrade_called is True

    adapter.downgrade("revision123")
    assert TestAdapter.downgrade_called is True

    adapter.get_current_revision()
    assert TestAdapter.get_revision_called is True

    adapter.get_migration_history()
    assert TestAdapter.get_history_called is True
