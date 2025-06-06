"""
Tests for the context manager behavior of AsyncNeo4jAdapter.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from neo4j.exceptions import CypherSyntaxError
from pydapter.exceptions import QueryError
from pydapter.extras.async_neo4j_ import AsyncNeo4jAdapter


class TestAsyncNeo4jContextManager:
    """Test suite for AsyncNeo4jAdapter context manager behavior."""

    @pytest.mark.asyncio
    async def test_async_context_manager_basic(self):
        """Test basic context manager behavior."""
        # Setup mock driver and session
        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()

        # Configure mocks for async context managers
        mock_driver.__aenter__.return_value = mock_driver
        mock_driver.__aexit__.return_value = None
        # Make sure session() returns a regular mock, not a coroutine
        mock_driver.session = MagicMock(return_value=mock_session)
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        # Configure the run method to return a mock result
        # Make sure run() returns a regular mock, not a coroutine
        mock_session.run = MagicMock(return_value=mock_result)

        # Mock the async iterator for result
        mock_record = MagicMock()
        mock_record.__getitem__.return_value = MagicMock(_properties={"id": 1})
        mock_result.__aiter__ = MagicMock(return_value=mock_result)
        mock_result.__anext__ = AsyncMock()
        mock_result.__anext__.side_effect = [mock_record, StopAsyncIteration]

        # Patch the _create_driver method
        with patch.object(
            AsyncNeo4jAdapter, "_create_driver", return_value=mock_driver
        ):
            # Use the adapter as a context manager
            async with AsyncNeo4jAdapter(url="bolt://localhost:7687") as adapter:
                # Execute a query
                result = await adapter.query("MATCH (n) RETURN n")

                # Verify the query was executed
                mock_session.run.assert_called_once_with("MATCH (n) RETURN n")

                # Verify the result
                assert result is not None
                assert len(result) == 1
                assert result[0]["id"] == 1

            # Verify the session was closed
            mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_context_manager_error_handling(self):
        """Test context manager error handling."""
        # Setup mock driver and session
        mock_driver = AsyncMock()
        mock_session = AsyncMock()

        # Configure mocks for async context managers
        mock_driver.__aenter__.return_value = mock_driver
        mock_driver.__aexit__.return_value = None
        # Make sure session() returns a regular mock, not a coroutine
        mock_driver.session = MagicMock(return_value=mock_session)
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        # Configure the run method to raise an exception
        mock_session.run = MagicMock(side_effect=CypherSyntaxError("Syntax error"))

        # Patch the _create_driver method
        with patch.object(
            AsyncNeo4jAdapter, "_create_driver", return_value=mock_driver
        ):
            # Use the adapter as a context manager
            async with AsyncNeo4jAdapter(url="bolt://localhost:7687") as adapter:
                # Execute a query and expect an exception
                with pytest.raises(QueryError) as exc_info:
                    await adapter.query("INVALID QUERY")

                # Verify the exception
                assert "Neo4j Cypher syntax error" in str(exc_info.value)

            # Verify the session was closed even though an error occurred
            mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_context_manager_session_error(self):
        """Test context manager behavior when session creation fails."""
        # Setup mock driver
        mock_driver = AsyncMock()

        # Configure mock driver to raise an exception when creating a session
        mock_driver.__aenter__.return_value = mock_driver
        mock_driver.__aexit__.return_value = None
        mock_driver.session = MagicMock(
            side_effect=Exception("Session creation failed")
        )

        # Patch the _create_driver method
        with patch.object(
            AsyncNeo4jAdapter, "_create_driver", return_value=mock_driver
        ):
            # Use the adapter as a context manager
            with pytest.raises(Exception) as exc_info:
                async with AsyncNeo4jAdapter(url="bolt://localhost:7687") as adapter:  # noqa: F841
                    # This should not be executed
                    pass

            # Verify the exception
            assert "Session creation failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_async_context_manager_driver_error(self):
        """Test context manager behavior when driver creation fails."""
        # Patch the _create_driver method to raise an exception
        with patch.object(
            AsyncNeo4jAdapter,
            "_create_driver",
            side_effect=Exception("Driver creation failed"),
        ):
            # Use the adapter as a context manager
            with pytest.raises(Exception) as exc_info:
                async with AsyncNeo4jAdapter(url="bolt://localhost:7687") as adapter:  # noqa: F841
                    # This should not be executed
                    pass

            # Verify the exception
            assert "Driver creation failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_async_context_manager_session_close_error(self):
        """Test context manager behavior when session close fails."""
        # Setup mock driver and session
        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()

        # Configure mocks for async context managers
        mock_driver.__aenter__.return_value = mock_driver
        mock_driver.__aexit__.return_value = None
        # Make sure session() returns a regular mock, not a coroutine
        mock_driver.session = MagicMock(return_value=mock_session)
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        # Configure the run method to return a mock result
        # Make sure run() returns a regular mock, not a coroutine
        mock_session.run = MagicMock(return_value=mock_result)

        # Configure the session close method to raise an exception
        mock_session.close = MagicMock(side_effect=Exception("Session close failed"))

        # Patch the _create_driver method
        with patch.object(
            AsyncNeo4jAdapter, "_create_driver", return_value=mock_driver
        ):
            # Use the adapter as a context manager
            async with AsyncNeo4jAdapter(url="bolt://localhost:7687") as adapter:
                # Execute a simple query
                await adapter.query("MATCH (n) RETURN n")

            # Verify the session close was called
            mock_session.close.assert_called_once()
            # The context manager should suppress the session close error

    @pytest.mark.asyncio
    async def test_async_context_manager_multiple_queries(self):
        """Test context manager with multiple queries."""
        # Setup mock driver and session
        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()

        # Configure mocks for async context managers
        mock_driver.__aenter__.return_value = mock_driver
        mock_driver.__aexit__.return_value = None
        # Make sure session() returns a regular mock, not a coroutine
        mock_driver.session = MagicMock(return_value=mock_session)
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        # Configure the run method to return a mock result
        # Make sure run() returns a regular mock, not a coroutine
        mock_session.run = MagicMock(return_value=mock_result)

        # Mock the async iterator for result
        mock_record = MagicMock()
        mock_record.__getitem__.return_value = MagicMock(_properties={"id": 1})
        mock_result.__aiter__ = MagicMock(return_value=mock_result)
        mock_result.__anext__ = AsyncMock()
        mock_result.__anext__.side_effect = [mock_record, StopAsyncIteration]

        # Patch the _create_driver method
        with patch.object(
            AsyncNeo4jAdapter, "_create_driver", return_value=mock_driver
        ):
            # Use the adapter as a context manager
            async with AsyncNeo4jAdapter(url="bolt://localhost:7687") as adapter:
                # Execute multiple queries
                await adapter.query("MATCH (n:Label1) RETURN n")
                await adapter.query("MATCH (n:Label2) RETURN n")
                await adapter.query("MATCH (n:Label3) RETURN n")

                # Verify the query was executed multiple times
                assert mock_session.run.call_count == 3

            # Verify the session was closed only once
            mock_session.close.assert_called_once()
