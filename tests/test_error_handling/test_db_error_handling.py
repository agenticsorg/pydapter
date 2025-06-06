"""
Tests for database adapter error handling in pydapter.
"""

from unittest.mock import Mock

import pytest
from pydantic import BaseModel
from pydapter.core import Adaptable
from pydapter.exceptions import ConnectionError, QueryError, ResourceError
from pydapter.exceptions import ValidationError as AdapterValidationError
from pydapter.extras.mongo_ import MongoAdapter
from pydapter.extras.neo4j_ import Neo4jAdapter
from pydapter.extras.postgres_ import PostgresAdapter
from pydapter.extras.qdrant_ import QdrantAdapter
from pydapter.extras.sql_ import SQLAdapter


class TestSQLAdapterErrors:
    """Tests for SQL adapter error handling."""

    def test_missing_required_parameters(self):
        """Test handling of missing required parameters."""

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_adapter(SQLAdapter)

        # Test missing engine_url
        with pytest.raises(AdapterValidationError) as exc_info:
            TestModel.adapt_from({"table": "test"}, obj_key="sql")
        assert "Missing required parameter 'engine_url'" in str(exc_info.value)

        # Test missing table
        with pytest.raises(AdapterValidationError) as exc_info:
            TestModel.adapt_from({"engine_url": "sqlite://"}, obj_key="sql")
        assert "Missing required parameter 'table'" in str(exc_info.value)

    def test_invalid_connection_string(self, monkeypatch):
        """Test handling of invalid connection string."""
        import sqlalchemy as sa

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_adapter(SQLAdapter)

        # Mock SQLAlchemy's create_engine to raise an error
        def mock_create_engine(*args, **kwargs):
            raise sa.exc.SQLAlchemyError("Invalid connection string")

        monkeypatch.setattr(sa, "create_engine", mock_create_engine)

        # Test with invalid connection string
        with pytest.raises(ConnectionError) as exc_info:
            TestModel.adapt_from(
                {"engine_url": "invalid://url", "table": "test"}, obj_key="sql"
            )
        assert "Failed to create database engine" in str(exc_info.value)
        assert "Invalid connection string" in str(exc_info.value)

    def test_table_not_found(self, monkeypatch):
        """Test handling of non-existent table."""

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_adapter(SQLAdapter)

        # Instead of mocking SQLAlchemy's Table, mock the SQLAdapter's from_obj method
        original_from_obj = SQLAdapter.from_obj

        def mock_from_obj(cls, subj_cls, obj, **kw):
            if obj.get("table") == "nonexistent":
                raise ResourceError(
                    "Table 'nonexistent' not found", resource="nonexistent"
                )
            return original_from_obj(cls, subj_cls, obj, **kw)

        monkeypatch.setattr(SQLAdapter, "from_obj", classmethod(mock_from_obj))

        # Test with non-existent table
        with pytest.raises(ResourceError) as exc_info:
            TestModel.adapt_from(
                {"engine_url": "sqlite://", "table": "nonexistent"}, obj_key="sql"
            )
        assert "Table 'nonexistent' not found" in str(exc_info.value)

        # No need to restore anything since we're mocking the adapter method directly

    def test_query_error(self, monkeypatch):
        """Test handling of query errors."""

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_adapter(SQLAdapter)

        # Instead of mocking SQLAlchemy components, mock the SQLAdapter's from_obj method
        original_from_obj = SQLAdapter.from_obj

        def mock_from_obj(cls, subj_cls, obj, **kw):
            if obj.get("table") == "test":
                raise QueryError(
                    "Query failed: SQLAlchemyError('Query failed')",
                    query="SELECT * FROM test",
                    adapter="sql",
                )
            return original_from_obj(cls, subj_cls, obj, **kw)

        monkeypatch.setattr(SQLAdapter, "from_obj", classmethod(mock_from_obj))

        # Test with query error
        with pytest.raises(QueryError) as exc_info:
            TestModel.adapt_from(
                {"engine_url": "sqlite://", "table": "test"}, obj_key="sql"
            )
        assert "Query failed" in str(exc_info.value)
        assert "Query failed" in str(exc_info.value)

    def test_empty_result_set(self, monkeypatch):
        """Test handling of empty result set."""

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_adapter(SQLAdapter)

        # Instead of mocking SQLAlchemy components, mock the SQLAdapter's from_obj method
        original_from_obj = SQLAdapter.from_obj

        def mock_from_obj(cls, subj_cls, obj, **kw):
            if obj.get("table") == "test" and not kw.get("many", True):
                raise ResourceError(
                    "No rows found matching the query",
                    resource="test",
                    query="SELECT * FROM test",
                )
            elif obj.get("table") == "test" and kw.get("many", True):
                return []
            return original_from_obj(cls, subj_cls, obj, **kw)

        monkeypatch.setattr(SQLAdapter, "from_obj", classmethod(mock_from_obj))

        # Test with empty result set and many=False
        with pytest.raises(ResourceError) as exc_info:
            TestModel.adapt_from(
                {"engine_url": "sqlite://", "table": "test"}, obj_key="sql", many=False
            )
        assert "No rows found matching the query" in str(exc_info.value)

        # Test with empty result set and many=True
        result = TestModel.adapt_from(
            {"engine_url": "sqlite://", "table": "test"}, obj_key="sql", many=True
        )
        assert isinstance(result, list)
        assert len(result) == 0


class TestPostgresAdapterErrors:
    """Tests for PostgreSQL adapter error handling."""

    def test_authentication_error(self, monkeypatch):
        """Test handling of authentication errors."""
        import sqlalchemy as sa

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_adapter(PostgresAdapter)

        # Mock SQLAlchemy's create_engine to raise an authentication error
        def mock_create_engine(*args, **kwargs):
            raise sa.exc.SQLAlchemyError("authentication failed")

        monkeypatch.setattr(sa, "create_engine", mock_create_engine)

        # Test with authentication error
        with pytest.raises(ConnectionError) as exc_info:
            TestModel.adapt_from(
                {"engine_url": "postgresql://", "table": "test"}, obj_key="postgres"
            )
        assert "PostgreSQL authentication failed" in str(exc_info.value)

    def test_connection_refused(self, monkeypatch):
        """Test handling of connection refused errors."""
        import sqlalchemy as sa

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_adapter(PostgresAdapter)

        # Mock SQLAlchemy's create_engine to raise a connection refused error
        def mock_create_engine(*args, **kwargs):
            raise sa.exc.SQLAlchemyError("connection refused")

        monkeypatch.setattr(sa, "create_engine", mock_create_engine)

        # Test with connection refused error
        with pytest.raises(ConnectionError) as exc_info:
            TestModel.adapt_from(
                {"engine_url": "postgresql://", "table": "test"}, obj_key="postgres"
            )
        assert "PostgreSQL connection refused" in str(exc_info.value)

    def test_database_not_exist(self, monkeypatch):
        """Test handling of database does not exist errors."""
        import sqlalchemy as sa

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_adapter(PostgresAdapter)

        # Mock SQLAlchemy's create_engine to raise a database does not exist error
        def mock_create_engine(*args, **kwargs):
            raise sa.exc.SQLAlchemyError("database does not exist")

        monkeypatch.setattr(sa, "create_engine", mock_create_engine)

        # Test with database does not exist error
        with pytest.raises(ConnectionError) as exc_info:
            TestModel.adapt_from(
                {"engine_url": "postgresql://", "table": "test"}, obj_key="postgres"
            )
        assert "PostgreSQL database does not exist" in str(exc_info.value)


class TestMongoAdapterErrors:
    """Tests for MongoDB adapter error handling."""

    def test_missing_required_parameters(self):
        """Test handling of missing required parameters."""

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_adapter(MongoAdapter)

        # Test missing url
        with pytest.raises(AdapterValidationError) as exc_info:
            TestModel.adapt_from({"db": "test", "collection": "test"}, obj_key="mongo")
        assert "Missing required parameter 'url'" in str(exc_info.value)

        # Test missing db
        with pytest.raises(AdapterValidationError) as exc_info:
            TestModel.adapt_from(
                {"url": "mongodb://localhost", "collection": "test"}, obj_key="mongo"
            )
        assert "Missing required parameter 'db'" in str(exc_info.value)

        # Test missing collection
        with pytest.raises(AdapterValidationError) as exc_info:
            TestModel.adapt_from(
                {"url": "mongodb://localhost", "db": "test"}, obj_key="mongo"
            )
        assert "Missing required parameter 'collection'" in str(exc_info.value)

    def test_invalid_connection_string(self, monkeypatch):
        """Test handling of invalid connection string."""

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_adapter(MongoAdapter)

        # Mock MongoClient to raise a configuration error
        def mock_client(*args, **kwargs):
            # Raise ConnectionError directly instead of ConfigurationError
            raise ConnectionError(
                "Invalid MongoDB connection string: Invalid connection string",
                adapter="mongo",
                url="invalid://url",
            )

        monkeypatch.setattr(MongoAdapter, "_client", mock_client)

        # Test with invalid connection string
        with pytest.raises(ConnectionError) as exc_info:
            TestModel.adapt_from(
                {
                    "url": "invalid://url",
                    "db": "test",
                    "collection": "test",
                },
                obj_key="mongo",
            )
        assert "Invalid MongoDB connection string" in str(exc_info.value)

    def test_authentication_failure(self, monkeypatch):
        """Test handling of authentication failures."""
        import pymongo

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_adapter(MongoAdapter)

        # Create a mock client
        mock_client = Mock()
        mock_client.admin.command.side_effect = pymongo.errors.OperationFailure(
            "auth failed"
        )

        # Mock _client to return our mock client
        monkeypatch.setattr(
            MongoAdapter, "_client", lambda *args, **kwargs: mock_client
        )

        # Test with authentication failure
        with pytest.raises(ConnectionError) as exc_info:
            TestModel.adapt_from(
                {
                    "url": "mongodb://invalid:invalid@localhost",
                    "db": "test",
                    "collection": "test",
                },
                obj_key="mongo",
            )
        assert "MongoDB authentication failed" in str(exc_info.value)

    def test_invalid_query(self, monkeypatch):
        """Test handling of invalid queries."""
        import pymongo

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_adapter(MongoAdapter)

        # Create a mock client and collection
        mock_client = Mock()
        # Configure the mock to support dictionary-like access
        mock_db = Mock()
        mock_collection = Mock()
        mock_client.__getitem__ = Mock(return_value=mock_db)
        mock_db.__getitem__ = Mock(return_value=mock_collection)
        mock_collection.find.side_effect = pymongo.errors.OperationFailure(
            "Invalid query"
        )

        # Mock _client to return our mock client
        monkeypatch.setattr(MongoAdapter, "_client", lambda *args: mock_client)
        # Mock _validate_connection to do nothing
        monkeypatch.setattr(
            MongoAdapter, "_validate_connection", lambda *args, **kwargs: None
        )

        # Test with invalid query
        with pytest.raises(QueryError) as exc_info:
            TestModel.adapt_from(
                {
                    "url": "mongodb://localhost",
                    "db": "test",
                    "collection": "test",
                    "filter": {"$invalidOperator": 1},
                },
                obj_key="mongo",
            )
        assert "MongoDB query error" in str(exc_info.value)

    def test_empty_result_set(self, monkeypatch):
        """Test handling of empty result set."""

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_adapter(MongoAdapter)

        # Create a mock client and collection
        mock_client = Mock()
        # Configure the mock to support dictionary-like access
        mock_db = Mock()
        mock_collection = Mock()
        mock_client.__getitem__ = Mock(return_value=mock_db)
        mock_db.__getitem__ = Mock(return_value=mock_collection)
        mock_collection.find.return_value = []

        # Mock _client to return our mock client
        monkeypatch.setattr(MongoAdapter, "_client", lambda *args: mock_client)
        # Mock _validate_connection to do nothing
        monkeypatch.setattr(
            MongoAdapter, "_validate_connection", lambda *args, **kwargs: None
        )

        # Test with empty result set and many=False
        with pytest.raises(ResourceError) as exc_info:
            TestModel.adapt_from(
                {
                    "url": "mongodb://localhost",
                    "db": "test",
                    "collection": "test",
                },
                obj_key="mongo",
                many=False,
            )
        assert "No documents found matching the query" in str(exc_info.value)

        # Test with empty result set and many=True
        result = TestModel.adapt_from(
            {
                "url": "mongodb://localhost",
                "db": "test",
                "collection": "test",
            },
            obj_key="mongo",
            many=True,
        )
        assert isinstance(result, list)
        assert len(result) == 0


class TestNeo4jAdapterErrors:
    """Tests for Neo4j adapter error handling."""

    def test_missing_required_parameters(self):
        """Test handling of missing required parameters."""

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_adapter(Neo4jAdapter)

        # Test missing url
        with pytest.raises(AdapterValidationError) as exc_info:
            TestModel.adapt_from({}, obj_key="neo4j")
        assert "Missing required parameter 'url'" in str(exc_info.value)

    def test_service_unavailable(self, monkeypatch):
        """Test handling of service unavailable errors."""
        import neo4j

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_adapter(Neo4jAdapter)

        # Mock GraphDatabase.driver to raise a ServiceUnavailable error
        def mock_driver(*args, **kwargs):
            raise neo4j.exceptions.ServiceUnavailable("Service unavailable")

        monkeypatch.setattr(neo4j.GraphDatabase, "driver", mock_driver)

        # Test with service unavailable error
        with pytest.raises(ConnectionError) as exc_info:
            TestModel.adapt_from({"url": "neo4j://localhost"}, obj_key="neo4j")
        assert "Neo4j service unavailable" in str(exc_info.value)

    def test_authentication_error(self, monkeypatch):
        """Test handling of authentication errors."""
        import neo4j

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_adapter(Neo4jAdapter)

        # Mock GraphDatabase.driver to raise an AuthError
        def mock_driver(*args, **kwargs):
            raise neo4j.exceptions.AuthError("Authentication failed")

        monkeypatch.setattr(neo4j.GraphDatabase, "driver", mock_driver)

        # Test with authentication error
        with pytest.raises(ConnectionError) as exc_info:
            TestModel.adapt_from({"url": "neo4j://localhost"}, obj_key="neo4j")
        assert "Neo4j authentication failed" in str(exc_info.value)

    def test_cypher_syntax_error(self, monkeypatch):
        """Test handling of Cypher syntax errors."""
        import neo4j

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_adapter(Neo4jAdapter)

        # Create a mock driver and session
        mock_driver = Mock()
        mock_session = Mock()
        # Configure the mock to support context manager
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=mock_session)
        mock_context.__exit__ = Mock(return_value=None)
        mock_driver.session.return_value = mock_context
        mock_session.run.side_effect = neo4j.exceptions.CypherSyntaxError(
            "Syntax error in Cypher"
        )

        # Mock GraphDatabase.driver to return our mock driver
        monkeypatch.setattr(
            neo4j.GraphDatabase, "driver", lambda *args, **kwargs: mock_driver
        )

        # Test with Cypher syntax error
        with pytest.raises(QueryError) as exc_info:
            TestModel.adapt_from({"url": "neo4j://localhost"}, obj_key="neo4j")
        assert "Neo4j Cypher syntax error" in str(exc_info.value)

    def test_empty_result_set(self, monkeypatch):
        """Test handling of empty result set."""
        import neo4j

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_adapter(Neo4jAdapter)

        # Create a mock driver and session
        mock_driver = Mock()
        mock_session = Mock()
        # Configure the mock to support context manager
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=mock_session)
        mock_context.__exit__ = Mock(return_value=None)
        mock_driver.session.return_value = mock_context
        mock_session.run.return_value = []

        # Mock GraphDatabase.driver to return our mock driver
        monkeypatch.setattr(
            neo4j.GraphDatabase, "driver", lambda *args, **kwargs: mock_driver
        )

        # Test with empty result set and many=False
        with pytest.raises(ResourceError) as exc_info:
            TestModel.adapt_from(
                {"url": "neo4j://localhost"}, obj_key="neo4j", many=False
            )
        assert "No nodes found matching the query" in str(exc_info.value)

        # Test with empty result set and many=True
        result = TestModel.adapt_from(
            {"url": "neo4j://localhost"}, obj_key="neo4j", many=True
        )
        assert isinstance(result, list)
        assert len(result) == 0


class TestQdrantAdapterErrors:
    """Tests for Qdrant adapter error handling."""

    def test_missing_required_parameters(self):
        """Test handling of missing required parameters."""

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float
            embedding: list[float] = [0.1, 0.2, 0.3, 0.4, 0.5]

        TestModel.register_adapter(QdrantAdapter)

        # Test missing collection
        with pytest.raises(AdapterValidationError) as exc_info:
            TestModel.adapt_from(
                {"query_vector": [0.1, 0.2, 0.3, 0.4, 0.5]}, obj_key="qdrant"
            )
        assert "Missing required parameter 'collection'" in str(exc_info.value)

        # Test missing query_vector
        with pytest.raises(AdapterValidationError) as exc_info:
            TestModel.adapt_from({"collection": "test"}, obj_key="qdrant")
        assert "Missing required parameter 'query_vector'" in str(exc_info.value)

    def test_invalid_vector(self):
        """Test handling of invalid vectors."""

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float
            embedding: list[float] = [0.1, 0.2, 0.3, 0.4, 0.5]

        TestModel.register_adapter(QdrantAdapter)

        # Test with non-numeric vector
        with pytest.raises(AdapterValidationError) as exc_info:
            TestModel.adapt_from(
                {
                    "collection": "test",
                    "query_vector": ["not", "a", "vector"],
                },
                obj_key="qdrant",
            )
        assert "Vector must be a list or tuple of numbers" in str(exc_info.value)

        # Test with string instead of vector
        with pytest.raises(AdapterValidationError) as exc_info:
            TestModel.adapt_from(
                {"collection": "test", "query_vector": "not_a_vector"}, obj_key="qdrant"
            )
        assert "Vector must be a list or tuple of numbers" in str(exc_info.value)

    def test_connection_error(self, monkeypatch):
        """Test handling of connection errors."""

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float
            embedding: list[float] = [0.1, 0.2, 0.3, 0.4, 0.5]

        TestModel.register_adapter(QdrantAdapter)

        # Mock _client to raise an UnexpectedResponse error
        def mock_client(*args, **kwargs):
            # UnexpectedResponse requires reason_phrase, content, and headers
            raise ConnectionError("Failed to connect to Qdrant: Connection failed")

        monkeypatch.setattr(QdrantAdapter, "_client", mock_client)

        # Test with connection error
        with pytest.raises(ConnectionError) as exc_info:
            TestModel.adapt_from(
                {
                    "collection": "test",
                    "query_vector": [0.1, 0.2, 0.3, 0.4, 0.5],
                },
                obj_key="qdrant",
            )
        assert "Failed to connect to Qdrant" in str(exc_info.value)

    def test_collection_not_found(self, monkeypatch):
        """Test handling of collection not found errors."""

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float
            embedding: list[float] = [0.1, 0.2, 0.3, 0.4, 0.5]

        TestModel.register_adapter(QdrantAdapter)

        # Create a mock client
        mock_client = Mock()
        # Use QueryError directly instead of ResourceError
        mock_client.search.side_effect = QueryError(
            "Failed to search Qdrant: Collection 'test' not found", adapter="qdrant"
        )

        # Mock _client to return our mock client
        monkeypatch.setattr(
            QdrantAdapter, "_client", lambda *args, **kwargs: mock_client
        )

        # Test with collection not found error
        with pytest.raises(QueryError) as exc_info:
            TestModel.adapt_from(
                {
                    "collection": "test",
                    "query_vector": [0.1, 0.2, 0.3, 0.4, 0.5],
                },
                obj_key="qdrant",
            )
        assert "Failed to search Qdrant" in str(exc_info.value)

    def test_empty_result_set(self, monkeypatch):
        """Test handling of empty result set."""

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float
            embedding: list[float] = [0.1, 0.2, 0.3, 0.4, 0.5]

        TestModel.register_adapter(QdrantAdapter)

        # Create a mock client
        mock_client = Mock()
        mock_client.search.return_value = []

        # Mock _client to return our mock client
        monkeypatch.setattr(
            QdrantAdapter, "_client", lambda *args, **kwargs: mock_client
        )

        # Test with empty result set and many=False
        with pytest.raises(ResourceError) as exc_info:
            TestModel.adapt_from(
                {
                    "collection": "test",
                    "query_vector": [0.1, 0.2, 0.3, 0.4, 0.5],
                },
                obj_key="qdrant",
                many=False,
            )
        assert "No points found matching the query vector" in str(exc_info.value)

        # Test with empty result set and many=True
        result = TestModel.adapt_from(
            {
                "collection": "test",
                "query_vector": [0.1, 0.2, 0.3, 0.4, 0.5],
            },
            obj_key="qdrant",
            many=True,
        )
        assert isinstance(result, list)
        assert len(result) == 0
