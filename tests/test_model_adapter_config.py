import pytest
from pydantic import ValidationError

from pydapter.model_adapters.config import PostgresAdapterConfig, VectorIndexConfig


def test_vector_index_config_defaults():
    """Test VectorIndexConfig default values."""
    config = VectorIndexConfig()

    assert config.index_type == "hnsw"
    assert isinstance(config.params, dict)
    assert len(config.params) == 0
    assert config.m == 16
    assert config.ef_construction == 64
    assert config.lists == 100
    assert config.probes == 10


def test_vector_index_config_custom_values():
    """Test VectorIndexConfig with custom values."""
    config = VectorIndexConfig(
        index_type="ivfflat",
        m=32,
        ef_construction=128,
        lists=200,
        probes=20,
    )

    assert config.index_type == "ivfflat"
    assert config.m == 32
    assert config.ef_construction == 128
    assert config.lists == 200
    assert config.probes == 20


def test_vector_index_config_params():
    """Test VectorIndexConfig with custom params."""
    config = VectorIndexConfig(
        index_type="hnsw",
        params={"m": 24, "ef_construction": 96},
    )

    assert config.index_type == "hnsw"
    assert config.params == {"m": 24, "ef_construction": 96}

    # get_params should return the custom params
    params = config.get_params()
    assert params == {"m": 24, "ef_construction": 96}


def test_vector_index_config_get_params():
    """Test VectorIndexConfig.get_params method."""
    # Test HNSW params
    hnsw_config = VectorIndexConfig(index_type="hnsw", m=32, ef_construction=128)
    hnsw_params = hnsw_config.get_params()

    assert hnsw_params == {"m": 32, "ef_construction": 128}

    # Test IVFFlat params
    ivf_config = VectorIndexConfig(index_type="ivfflat", lists=200)
    ivf_params = ivf_config.get_params()

    assert ivf_params == {"lists": 200}

    # Test exact params (should be empty)
    exact_config = VectorIndexConfig(index_type="exact")
    exact_params = exact_config.get_params()

    assert exact_params == {}


def test_vector_index_config_validation():
    """Test VectorIndexConfig validation."""
    # Test valid index types
    VectorIndexConfig(index_type="hnsw")
    VectorIndexConfig(index_type="ivfflat")
    VectorIndexConfig(index_type="exact")

    # Test invalid index type
    with pytest.raises(ValidationError):
        VectorIndexConfig(index_type="invalid")


def test_postgres_adapter_config_defaults():
    """Test PostgresAdapterConfig default values."""
    config = PostgresAdapterConfig()

    assert config.schema == "public"
    assert config.batch_size == 1000
    assert isinstance(config.vector_index_config, VectorIndexConfig)
    assert config.validate_vector_dimensions is True


def test_postgres_adapter_config_custom_values():
    """Test PostgresAdapterConfig with custom values."""
    config = PostgresAdapterConfig(
        schema="custom_schema",
        batch_size=500,
        validate_vector_dimensions=False,
        vector_index_config=VectorIndexConfig(
            index_type="ivfflat",
            lists=200,
        ),
    )

    assert config.schema == "custom_schema"
    assert config.batch_size == 500
    assert config.validate_vector_dimensions is False
    assert config.vector_index_config.index_type == "ivfflat"
    assert config.vector_index_config.lists == 200


def test_postgres_adapter_config_validation():
    """Test PostgresAdapterConfig validation."""
    # Test valid batch size
    PostgresAdapterConfig(batch_size=1)
    PostgresAdapterConfig(batch_size=10000)

    # Test invalid batch size (must be positive)
    with pytest.raises(ValidationError):
        PostgresAdapterConfig(batch_size=0)

    with pytest.raises(ValidationError):
        PostgresAdapterConfig(batch_size=-1)
