"""
Property-based tests for pydapter adapters.
"""

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from pydantic import BaseModel
from pydapter.adapters import CsvAdapter, JsonAdapter, TomlAdapter
from pydapter.core import Adaptable


def create_test_model(**kw):
    """Create a test model with adapters registered."""

    class TestModel(Adaptable, BaseModel):
        id: int
        name: str
        value: float

    # Register standard adapters
    TestModel.register_adapter(JsonAdapter)
    TestModel.register_adapter(CsvAdapter)
    TestModel.register_adapter(TomlAdapter)

    return TestModel(**kw)


class TestPropertyBasedAdapters:
    """Property-based tests for adapter implementations."""

    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        id=st.integers(),
        name=st.text(min_size=1, max_size=50),
        value=st.floats(allow_nan=False, allow_infinity=False),
    )
    def test_json_adapter_roundtrip(self, id, name, value):
        """Test that objects can be round-tripped through the JsonAdapter."""
        model = create_test_model(id=id, name=name, value=value)
        serialized = model.adapt_to(obj_key="json")
        deserialized = model.__class__.adapt_from(serialized, obj_key="json")
        assert deserialized == model

    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        id=st.integers(),
        name=st.text(
            min_size=1,
            max_size=50,
            alphabet=st.characters(
                blacklist_categories=("Cc", "Cs")
            ),  # Exclude control chars
        ).filter(lambda x: "," not in x and "\n" not in x),
        value=st.floats(allow_nan=False, allow_infinity=False),
    )
    def test_csv_adapter_roundtrip(self, id, name, value):
        """Test that objects can be round-tripped through the CsvAdapter."""
        model = create_test_model(id=id, name=name, value=value)
        serialized = model.adapt_to(obj_key="csv")
        deserialized = model.__class__.adapt_from(serialized, obj_key="csv", many=False)
        assert deserialized == model

    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        id=st.integers(),
        # Use a safe subset of ASCII characters for TOML
        name=st.text(
            min_size=1,
            max_size=50,
            alphabet=st.characters(
                whitelist_categories=("Lu", "Ll", "Nd"),  # Uppercase, lowercase, digits
                whitelist_characters=" _-",  # Safe punctuation
            ),
        ),
        value=st.floats(allow_nan=False, allow_infinity=False),
    )
    def test_toml_adapter_roundtrip(self, id, name, value):
        """Test that objects can be round-tripped through the TomlAdapter."""
        model = create_test_model(id=id, name=name, value=value)
        serialized = model.adapt_to(obj_key="toml")
        deserialized = model.__class__.adapt_from(serialized, obj_key="toml")
        assert deserialized == model


class TestEdgeCases:
    """Property-based tests for edge cases."""

    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        name=st.one_of(st.just(""), st.text(min_size=1, max_size=50)),
        value=st.one_of(st.just(0.0), st.floats(allow_nan=False, allow_infinity=False)),
    )
    def test_adapter_empty_values(self, name, value):
        """Test handling of empty values in adapters."""
        model = create_test_model(id=0, name=name, value=value)
        serialized = model.adapt_to(obj_key="json")
        deserialized = model.__class__.adapt_from(serialized, obj_key="json")
        assert deserialized == model

    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        name=st.text(
            alphabet=st.characters(blacklist_categories=("Cs",)),
            min_size=1,
            max_size=50,
        ),
        value=st.floats(allow_nan=False, allow_infinity=False),
    )
    def test_adapter_special_characters(self, name, value):
        """Test handling of special characters in adapters."""
        model = create_test_model(id=1, name=name, value=value)
        serialized = model.adapt_to(obj_key="json")
        deserialized = model.__class__.adapt_from(serialized, obj_key="json")
        assert deserialized == model

    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        id=st.integers(min_value=-1000000, max_value=1000000),
        value=st.floats(
            min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False
        ),
    )
    def test_adapter_extreme_values(self, id, value):
        """Test handling of extreme values in adapters."""
        model = create_test_model(id=id, name="extreme", value=value)
        serialized = model.adapt_to(obj_key="json")
        deserialized = model.__class__.adapt_from(serialized, obj_key="json")
        assert deserialized == model


class TestCrossAdapterConsistency:
    """Tests for consistency across different adapter implementations."""

    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        id=st.integers(),
        # Use a safe subset of ASCII characters for TOML
        name=st.text(
            min_size=1,
            max_size=50,
            alphabet=st.characters(
                whitelist_categories=("Lu", "Ll", "Nd"),  # Uppercase, lowercase, digits
                whitelist_characters=" _-",  # Safe punctuation
            ),
        ),
        value=st.floats(allow_nan=False, allow_infinity=False),
    )
    def test_cross_adapter_consistency(self, id, name, value):
        """Test that different adapters produce consistent results."""
        import json

        import toml

        model = create_test_model(id=id, name=name, value=value)

        # Get JSON representation
        json_obj = model.adapt_to(obj_key="json")
        json_data = json.loads(json_obj)

        # Get TOML representation
        toml_obj = model.adapt_to(obj_key="toml")
        toml_data = toml.loads(toml_obj)

        # Compare data
        assert json_data["id"] == toml_data["id"]
        assert json_data["name"] == toml_data["name"]
        assert json_data["value"] == toml_data["value"]


# Configure Hypothesis profiles
settings.register_profile("ci", max_examples=100, deadline=None)

settings.register_profile("dev", max_examples=10, deadline=None)

# Load the appropriate profile based on environment
# In a real implementation, this would check for CI environment
settings.load_profile("dev")
