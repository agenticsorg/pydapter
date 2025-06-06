"""
Benchmark tests for pydapter adapters.
"""

import csv
import io
import json

import pytest
import toml
from pydantic import BaseModel
from pydapter.adapters import CsvAdapter, JsonAdapter, TomlAdapter
from pydapter.core import Adaptable, AdapterRegistry


@pytest.fixture
def sample_model():
    """Create a sample model for benchmarking."""

    class TestModel(Adaptable, BaseModel):
        id: int
        name: str
        value: float

    TestModel.register_adapter(JsonAdapter)
    TestModel.register_adapter(CsvAdapter)
    TestModel.register_adapter(TomlAdapter)

    return TestModel(id=1, name="test", value=42.5)


@pytest.fixture
def large_model():
    """Create a larger model for benchmarking."""

    class LargeModel(Adaptable, BaseModel):
        id: int
        name: str
        description: str
        values: list[float]
        metadata: dict[str, str]

    LargeModel.register_adapter(JsonAdapter)
    LargeModel.register_adapter(CsvAdapter)
    LargeModel.register_adapter(TomlAdapter)

    return LargeModel(
        id=1,
        name="large_test",
        description="A larger model for benchmarking with more fields and nested data structures",
        values=[1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0],
        metadata={
            "created_by": "benchmark",
            "version": "1.0",
            "category": "test",
            "tags": "benchmark,test,performance",
            "notes": "This is a test model for benchmarking adapter performance",
        },
    )


class TestSerializationBenchmarks:
    """Benchmark tests for serialization operations."""

    def test_json_serialization(self, benchmark, sample_model):
        """Benchmark JsonAdapter serialization."""
        benchmark(sample_model.adapt_to, obj_key="json")

    def test_csv_serialization(self, benchmark, sample_model):
        """Benchmark CsvAdapter serialization."""
        benchmark(sample_model.adapt_to, obj_key="csv")

    def test_toml_serialization(self, benchmark, sample_model):
        """Benchmark TomlAdapter serialization."""
        benchmark(sample_model.adapt_to, obj_key="toml")

    def test_large_json_serialization(self, benchmark, large_model):
        """Benchmark JsonAdapter serialization with a larger model."""
        benchmark(large_model.adapt_to, obj_key="json")

    def test_native_json_serialization(self, benchmark, sample_model):
        """Benchmark native json.dumps for comparison."""
        benchmark(json.dumps, sample_model.model_dump(), indent=2, sort_keys=True)

    def test_native_toml_serialization(self, benchmark, sample_model):
        """Benchmark native toml.dumps for comparison."""
        benchmark(toml.dumps, sample_model.model_dump())

    def test_native_csv_serialization(self, benchmark, sample_model):
        """Benchmark native csv writing for comparison."""

        def write_csv():
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=["id", "name", "value"])
            writer.writeheader()
            writer.writerow(sample_model.model_dump())
            return output.getvalue()

        benchmark(write_csv)


class TestDeserializationBenchmarks:
    """Benchmark tests for deserialization operations."""

    @pytest.fixture
    def json_data(self, sample_model):
        """Create JSON data for benchmarking."""
        return sample_model.adapt_to(obj_key="json")

    @pytest.fixture
    def csv_data(self, sample_model):
        """Create CSV data for benchmarking."""
        return sample_model.adapt_to(obj_key="csv")

    @pytest.fixture
    def toml_data(self, sample_model):
        """Create TOML data for benchmarking."""
        return sample_model.adapt_to(obj_key="toml")

    @pytest.fixture
    def large_json_data(self, large_model):
        """Create large JSON data for benchmarking."""
        return large_model.adapt_to(obj_key="json")

    def test_json_deserialization(self, benchmark, json_data, sample_model):
        """Benchmark JsonAdapter deserialization."""
        benchmark(sample_model.__class__.adapt_from, json_data, obj_key="json")

    def test_csv_deserialization(self, benchmark, csv_data, sample_model):
        """Benchmark CsvAdapter deserialization."""
        benchmark(sample_model.__class__.adapt_from, csv_data, obj_key="csv")

    def test_toml_deserialization(self, benchmark, toml_data, sample_model):
        """Benchmark TomlAdapter deserialization."""
        benchmark(sample_model.__class__.adapt_from, toml_data, obj_key="toml")

    def test_large_json_deserialization(self, benchmark, large_json_data, large_model):
        """Benchmark JsonAdapter deserialization with a larger model."""
        benchmark(large_model.__class__.adapt_from, large_json_data, obj_key="json")

    def test_native_json_deserialization(self, benchmark, json_data, sample_model):
        """Benchmark native json.loads for comparison."""
        model_cls = sample_model.__class__

        def parse_json():
            data = json.loads(json_data)
            return model_cls(**data)

        benchmark(parse_json)

    def test_native_toml_deserialization(self, benchmark, toml_data, sample_model):
        """Benchmark native toml.loads for comparison."""
        model_cls = sample_model.__class__

        def parse_toml():
            data = toml.loads(toml_data)
            return model_cls(**data)

        benchmark(parse_toml)


class TestRegistryBenchmarks:
    """Benchmark tests for registry operations."""

    @pytest.fixture
    def populated_registry(self):
        """Create a populated registry for benchmarking."""
        registry = AdapterRegistry()
        registry.register(JsonAdapter)
        registry.register(CsvAdapter)
        registry.register(TomlAdapter)

        # Add some more adapters for a more realistic benchmark
        for i in range(10):

            class DummyAdapter:
                obj_key = f"dummy_{i}"

                @classmethod
                def from_obj(cls, subj_cls, obj, /, *, many=False, **kw):
                    return subj_cls()

                @classmethod
                def to_obj(cls, subj, /, *, many=False, **kw):
                    return {}

            registry.register(DummyAdapter)

        return registry

    def test_registry_get(self, benchmark, populated_registry):
        """Benchmark registry lookup."""
        benchmark(populated_registry.get, "json")

    def test_registry_registration(self, benchmark):
        """Benchmark adapter registration."""
        registry = AdapterRegistry()

        class BenchmarkAdapter:
            obj_key = "benchmark"

            @classmethod
            def from_obj(cls, subj_cls, obj, /, *, many=False, **kw):
                return subj_cls()

            @classmethod
            def to_obj(cls, subj, /, *, many=False, **kw):
                return {}

        benchmark(registry.register, BenchmarkAdapter)
