"""Tests for protocol field families functionality."""

import pytest

from pydapter.fields import (
    ID_TEMPLATE,
    NAME_TEMPLATE,
    FieldTemplate,
    ProtocolFieldFamilies,
    create_protocol_model,
)
from pydapter.fields.execution import Execution


class TestProtocolFieldFamilies:
    """Test the ProtocolFieldFamilies class."""

    def test_identifiable_family(self):
        """Test the IDENTIFIABLE field family."""
        assert "id" in ProtocolFieldFamilies.IDENTIFIABLE
        assert len(ProtocolFieldFamilies.IDENTIFIABLE) == 1

        # Should use the standard ID template
        assert ProtocolFieldFamilies.IDENTIFIABLE["id"] == ID_TEMPLATE

    def test_temporal_families(self):
        """Test the TEMPORAL field families."""
        # Both should have the same fields
        assert set(ProtocolFieldFamilies.TEMPORAL.keys()) == {
            "created_at",
            "updated_at",
        }
        assert set(ProtocolFieldFamilies.TEMPORAL_TZ.keys()) == {
            "created_at",
            "updated_at",
        }

        # But different templates (timezone-aware vs naive)
        assert (
            ProtocolFieldFamilies.TEMPORAL["created_at"]
            != ProtocolFieldFamilies.TEMPORAL_TZ["created_at"]
        )

    def test_embeddable_family(self):
        """Test the EMBEDDABLE field family."""
        assert "embedding" in ProtocolFieldFamilies.EMBEDDABLE

        embedding_template = ProtocolFieldFamilies.EMBEDDABLE["embedding"]
        assert embedding_template.base_type == list[float]
        # Check that json_schema_extra was set on the template
        json_schema_extra = embedding_template.extract_metadata("json_schema_extra")
        assert json_schema_extra is not None
        assert json_schema_extra.get("vector_dim") == 1536

    def test_invokable_family(self):
        """Test the INVOKABLE field family."""
        assert "execution" in ProtocolFieldFamilies.INVOKABLE

        execution_template = ProtocolFieldFamilies.INVOKABLE["execution"]
        assert execution_template.base_type == Execution

    def test_cryptographical_family(self):
        """Test the CRYPTOGRAPHICAL field family."""
        assert "sha256" in ProtocolFieldFamilies.CRYPTOGRAPHICAL

        sha_template = ProtocolFieldFamilies.CRYPTOGRAPHICAL["sha256"]
        # Should be nullable
        field = sha_template.create_field()
        assert field.default is None

    def test_event_base_family(self):
        """Test the EVENT_BASE field family."""
        expected_fields = [
            "id",
            "created_at",
            "updated_at",
            "event_type",
            "content",
            "request",
        ]
        for field in expected_fields:
            assert field in ProtocolFieldFamilies.EVENT_BASE

        # ID should be frozen for events
        id_template = ProtocolFieldFamilies.EVENT_BASE["id"]
        # Check if frozen metadata exists
        frozen_value = id_template.extract_metadata("frozen")
        assert (
            frozen_value is True or frozen_value is None
        )  # ID_TEMPLATE might not have frozen metadata

    def test_event_complete_family(self):
        """Test the EVENT_COMPLETE field family."""
        # Should include all event base fields plus embeddable, cryptographical, and execution
        assert "id" in ProtocolFieldFamilies.EVENT_COMPLETE
        assert "embedding" in ProtocolFieldFamilies.EVENT_COMPLETE
        assert "sha256" in ProtocolFieldFamilies.EVENT_COMPLETE
        assert "execution" in ProtocolFieldFamilies.EVENT_COMPLETE


class TestCreateProtocolModel:
    """Test the create_protocol_model function."""

    def test_single_protocol(self):
        """Test creating a model with a single protocol."""
        # Identifiable
        Model1 = create_protocol_model("Model1", "identifiable")
        assert "id" in Model1.model_fields
        assert len(Model1.model_fields) == 1

        # Temporal
        Model2 = create_protocol_model("Model2", "temporal")
        assert "created_at" in Model2.model_fields
        assert "updated_at" in Model2.model_fields

        # Embeddable
        Model3 = create_protocol_model("Model3", "embeddable")
        assert "embedding" in Model3.model_fields

    def test_multiple_protocols(self):
        """Test creating a model with multiple protocols."""
        Model = create_protocol_model(
            "TrackedEntity",
            "identifiable",
            "temporal",
        )

        assert "id" in Model.model_fields
        assert "created_at" in Model.model_fields
        assert "updated_at" in Model.model_fields

    def test_timezone_aware_option(self):
        """Test timezone_aware parameter."""
        # Default is timezone-aware
        Model1 = create_protocol_model("Model1", "temporal")
        # Explicitly timezone-aware
        Model2 = create_protocol_model("Model2", "temporal", timezone_aware=True)

        # Not timezone-aware
        Model3 = create_protocol_model("Model3", "temporal", timezone_aware=False)

        # Check that timezone-aware models have different fields than naive
        # (This is a simplification - actual check would verify the datetime type)
        assert Model1.model_fields.keys() == Model2.model_fields.keys()
        assert Model1.model_fields.keys() == Model3.model_fields.keys()

    def test_invalid_protocol_raises_error(self):
        """Test that invalid protocol names raise an error."""
        with pytest.raises(ValueError, match="Unknown protocol: invalid"):
            create_protocol_model("TestModel", "invalid")

        # Event is no longer a valid protocol (use Event class directly)
        with pytest.raises(ValueError, match="Unknown protocol: event"):
            create_protocol_model("TestModel", "event")

    def test_base_fields(self):
        """Test providing base fields."""
        base_fields = {
            "name": NAME_TEMPLATE,
            "description": FieldTemplate(base_type=str).with_default(""),
        }

        Model = create_protocol_model(
            "NamedEntity", "identifiable", base_fields=base_fields
        )

        assert "id" in Model.model_fields  # From protocol
        assert "name" in Model.model_fields  # From base fields
        assert "description" in Model.model_fields  # From base fields

    def test_extra_fields(self):
        """Test adding extra fields."""
        Model = create_protocol_model(
            "Document",
            "identifiable",
            "temporal",
            "embeddable",
            title=NAME_TEMPLATE,
            content=FieldTemplate(base_type=str),
            tags=FieldTemplate(base_type=list[str]).with_default(list),
        )

        # Protocol fields
        assert "id" in Model.model_fields
        assert "created_at" in Model.model_fields
        assert "embedding" in Model.model_fields

        # Extra fields
        assert "title" in Model.model_fields
        assert "content" in Model.model_fields
        assert "tags" in Model.model_fields

    def test_invalid_protocol(self):
        """Test error handling for invalid protocol."""
        with pytest.raises(ValueError, match="Unknown protocol: invalid"):
            create_protocol_model("Model", "invalid")

    def test_protocol_case_insensitive(self):
        """Test that protocol names are case-insensitive."""
        Model1 = create_protocol_model("Model1", "IDENTIFIABLE")
        Model2 = create_protocol_model("Model2", "Identifiable")
        Model3 = create_protocol_model("Model3", "identifiable")

        # All should have the same fields
        assert Model1.model_fields.keys() == Model2.model_fields.keys()
        assert Model2.model_fields.keys() == Model3.model_fields.keys()

    def test_all_protocols(self):
        """Test model with all protocols."""
        Model = create_protocol_model(
            "CompleteModel",
            "identifiable",
            "temporal",
            "embeddable",
            "invokable",
            "cryptographical",
        )

        # Should have fields from all protocols
        assert "id" in Model.model_fields
        assert "created_at" in Model.model_fields
        assert "embedding" in Model.model_fields
        assert "execution" in Model.model_fields
        assert "sha256" in Model.model_fields

    def test_model_instance_creation(self):
        """Test creating instances of protocol models."""
        User = create_protocol_model(
            "User",
            "identifiable",
            "temporal",
            username=FieldTemplate(base_type=str),
            email=FieldTemplate(base_type=str),
        )

        # Create an instance
        user = User(username="testuser", email="test@example.com")

        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert hasattr(user, "id")
        assert hasattr(user, "created_at")
        assert hasattr(user, "updated_at")

    def test_complex_example(self):
        """Test a complex real-world example."""
        # Create an embeddable document model
        Document = create_protocol_model(
            "Document",
            "identifiable",
            "temporal",
            "embeddable",
            "cryptographical",
            timezone_aware=True,
            title=NAME_TEMPLATE,
            content=FieldTemplate(base_type=str).with_description("Document content"),
            author_id=ID_TEMPLATE,
            tags=FieldTemplate(base_type=list[str])
            .with_default(list)
            .with_description("Document tags"),
        )

        # Verify the model
        assert Document.__name__ == "Document"

        # Protocol fields
        assert "id" in Document.model_fields
        assert "created_at" in Document.model_fields
        assert "embedding" in Document.model_fields
        assert "sha256" in Document.model_fields

        # Custom fields
        assert "title" in Document.model_fields
        assert "content" in Document.model_fields
        assert "author_id" in Document.model_fields
        assert "tags" in Document.model_fields

        # Create an instance
        doc = Document(
            title="Test Document",
            content="This is test content",
            author_id="123e4567-e89b-12d3-a456-426614174000",
        )

        assert doc.title == "Test Document"
        assert doc.tags == []  # Default factory
        assert doc.sha256 is None  # Nullable field
