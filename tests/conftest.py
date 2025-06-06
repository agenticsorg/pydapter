import pytest
from pydapter import Adaptable
from pydapter.adapters import CsvAdapter, JsonAdapter, TomlAdapter
from pydapter.async_core import AsyncAdaptable


@pytest.fixture
def _ModelFactory():  # type: ignore[no-redef]
    class Factory:
        def __call__(self, **kw):
            from pydantic import BaseModel

            class M(Adaptable, BaseModel):
                id: int
                name: str
                value: float

            M.register_adapter(JsonAdapter)
            M.register_adapter(CsvAdapter)
            M.register_adapter(TomlAdapter)
            return M(**kw)

    return Factory()


@pytest.fixture
def sample(_ModelFactory):  # pylint: disable=invalid-name
    return _ModelFactory(id=1, name="foo", value=42.5)


@pytest.fixture(scope="session")
def pg_url():
    from testcontainers.postgres import PostgresContainer

    with PostgresContainer("postgres:16-alpine") as pg:
        # Convert the URL to use asyncpg instead of psycopg2
        url = pg.get_connection_url()  # postgresql://user:pass@host:port/db
        url = url.replace("postgresql://", "postgresql+asyncpg://")
        yield url


@pytest.fixture(scope="session")
def qdrant_url():
    from testcontainers.qdrant import QdrantContainer

    with QdrantContainer("qdrant/qdrant:v1.8.1") as qc:
        yield f"http://{qc.get_container_host_ip()}:{qc.get_exposed_port(6333)}"


@pytest.fixture(scope="session")
def mongo_url():
    from testcontainers.mongodb import MongoDbContainer

    # Use MongoDB container with authentication
    with (
        MongoDbContainer("mongo:6.0")
        .with_env("MONGO_INITDB_ROOT_USERNAME", "test")
        .with_env("MONGO_INITDB_ROOT_PASSWORD", "test") as mongo
    ):
        yield f"mongodb://test:test@{mongo.get_container_host_ip()}:{mongo.get_exposed_port(27017)}"


@pytest.fixture(scope="session")
def neo4j_container():
    """Neo4j container fixture for tests."""
    from testcontainers.neo4j import Neo4jContainer

    # Set Neo4j auth using username and password parameters
    with Neo4jContainer("neo4j:5.9", username="neo4j", password="password") as neo4j:
        yield neo4j


@pytest.fixture(scope="session")
def weaviate_container():
    """Weaviate container fixture for tests."""
    try:
        from testcontainers.weaviate import WeaviateContainer

        # Create Weaviate container
        try:
            container = WeaviateContainer()
            container.start()

            yield container

            container.stop()
        except Exception:
            # If container fails to start, yield None
            yield None
    except (ImportError, AttributeError):
        # If weaviate or testcontainers is not available, yield None
        yield None


@pytest.fixture(scope="session")
def weaviate_client(weaviate_container):
    """Get Weaviate client."""
    if weaviate_container is None:
        yield None
        return

    try:
        with weaviate_container.get_client() as client:
            yield client
    except Exception:
        # If client creation fails, yield None
        yield None


@pytest.fixture(scope="session")
def weaviate_url(weaviate_container):
    """Get Weaviate connection URL."""
    if weaviate_container is None:
        return "http://localhost:8080"  # Return a default URL

    try:
        # Extract URL from container
        host = weaviate_container.get_container_host_ip()
        port = weaviate_container.get_exposed_port(8080)
        return f"http://{host}:{port}"
    except Exception:
        # If URL extraction fails, return a default URL
        return "http://localhost:8080"


@pytest.fixture(scope="session")
def neo4j_url(neo4j_container):
    """Get Neo4j connection URL."""
    return neo4j_container.get_connection_url()


@pytest.fixture(scope="session")
def neo4j_auth():
    """Get Neo4j authentication credentials."""
    return ("neo4j", "password")


@pytest.fixture
def async_model_factory():
    from pydantic import BaseModel
    from pydapter.extras.async_mongo_ import AsyncMongoAdapter
    from pydapter.extras.async_postgres_ import AsyncPostgresAdapter
    from pydapter.extras.async_qdrant_ import AsyncQdrantAdapter

    class AsyncModel(AsyncAdaptable, BaseModel):
        id: int
        name: str
        value: float
        embedding: list[float] = [0.1, 0.2, 0.3, 0.4, 0.5]  # For vector DBs

    # Register async adapters
    AsyncModel.register_async_adapter(AsyncPostgresAdapter)
    AsyncModel.register_async_adapter(AsyncMongoAdapter)
    AsyncModel.register_async_adapter(AsyncQdrantAdapter)

    return AsyncModel


@pytest.fixture
def async_sample(async_model_factory):
    return async_model_factory(id=1, name="foo", value=42.5)


@pytest.fixture
def sync_model_factory():
    """Factory for creating test models with adapters registered."""
    from pydantic import BaseModel
    from pydapter.core import Adaptable

    def create_model(**kw):
        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        return TestModel(**kw)

    return create_model


@pytest.fixture
def sync_vector_model_factory():
    """Factory for creating test models with vector field."""
    from pydantic import BaseModel
    from pydapter.core import Adaptable

    def create_model(**kw):
        class VectorModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float
            embedding: list[float] = [
                0.1,
                0.2,
                0.3,
                0.4,
                0.5,
            ]  # Default embedding for vector DBs

        return VectorModel(**kw)

    return create_model


@pytest.fixture
def sync_sample(sync_model_factory):
    """Create a sample model instance."""
    return sync_model_factory(id=1, name="foo", value=42.5)
