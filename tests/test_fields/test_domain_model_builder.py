"""Tests for DomainModelBuilder functionality."""

import pytest

from pydapter.fields import ID_TEMPLATE, DomainModelBuilder, FieldTemplate


class TestDomainModelBuilder:
    """Test the DomainModelBuilder class."""

    def test_basic_builder(self):
        """Test basic builder functionality."""
        User = DomainModelBuilder("User").with_entity_fields().build()

        assert User.__name__ == "User"
        assert "id" in User.model_fields
        assert "created_at" in User.model_fields
        assert "updated_at" in User.model_fields

    def test_builder_with_config(self):
        """Test builder with model configuration."""
        User = (
            DomainModelBuilder("User", from_attributes=True, validate_assignment=True)
            .with_entity_fields()
            .build()
        )

        assert User.model_config["from_attributes"] is True
        assert User.model_config["validate_assignment"] is True

    def test_entity_fields(self):
        """Test adding entity fields."""
        # Test naive datetime
        Model1 = (
            DomainModelBuilder("Model1")
            .with_entity_fields(timezone_aware=False)
            .build()
        )

        # Test timezone-aware datetime
        Model2 = (
            DomainModelBuilder("Model2").with_entity_fields(timezone_aware=True).build()
        )

        # Both should have the same fields
        assert set(Model1.model_fields.keys()) == set(Model2.model_fields.keys())

    def test_soft_delete_fields(self):
        """Test adding soft delete fields."""
        # Test naive datetime
        Model1 = (
            DomainModelBuilder("Model1").with_soft_delete(timezone_aware=False).build()
        )

        assert "deleted_at" in Model1.model_fields
        assert "is_deleted" in Model1.model_fields
        assert Model1.model_fields["is_deleted"].default is False

        # Test timezone-aware
        Model2 = (
            DomainModelBuilder("Model2").with_soft_delete(timezone_aware=True).build()
        )

        assert "deleted_at" in Model2.model_fields
        assert "is_deleted" in Model2.model_fields

    def test_all_field_methods(self):
        """Test all core with_* methods."""
        Model = (
            DomainModelBuilder("CompleteModel")
            .with_entity_fields()
            .with_soft_delete()
            .with_audit_fields()
            .build()
        )

        # Check that fields from all families are present
        expected_fields = [
            "id",
            "created_at",
            "updated_at",  # entity
            "deleted_at",
            "is_deleted",  # soft delete
            "created_by",
            "updated_by",
            "version",  # audit
        ]

        for field in expected_fields:
            assert field in Model.model_fields

    def test_custom_family(self):
        """Test adding a custom field family."""
        custom_family = {
            "custom1": FieldTemplate(base_type=str).with_default("test"),
            "custom2": FieldTemplate(base_type=int).with_default(42),
        }

        Model = (
            DomainModelBuilder("Model")
            .with_entity_fields()
            .with_family(custom_family)
            .build()
        )

        assert "custom1" in Model.model_fields
        assert "custom2" in Model.model_fields
        assert Model.model_fields["custom1"].default == "test"
        assert Model.model_fields["custom2"].default == 42

    def test_add_field(self):
        """Test adding individual fields."""
        Model = (
            DomainModelBuilder("Model")
            .with_entity_fields()
            .add_field("status", FieldTemplate(base_type=str).with_default("active"))
            .add_field("priority", FieldTemplate(base_type=int).with_default(0))
            .build()
        )

        assert "status" in Model.model_fields
        assert "priority" in Model.model_fields

    def test_add_field_replace(self):
        """Test field replacement behavior."""
        builder = DomainModelBuilder("Model").with_entity_fields()

        # Add a field
        builder.add_field("custom", FieldTemplate(base_type=str).with_default("v1"))

        # Replace it (default behavior)
        builder.add_field("custom", FieldTemplate(base_type=str).with_default("v2"))

        Model = builder.build()
        assert Model.model_fields["custom"].default == "v2"

        # Test with replace=False
        builder2 = DomainModelBuilder("Model2").with_entity_fields()
        builder2.add_field("custom", FieldTemplate(base_type=str))

        with pytest.raises(ValueError, match="Field 'custom' already exists"):
            builder2.add_field("custom", FieldTemplate(base_type=int), replace=False)

    def test_remove_field(self):
        """Test removing a single field."""
        Model = (
            DomainModelBuilder("Model")
            .with_entity_fields()
            .remove_field("updated_at")
            .build()
        )

        assert "id" in Model.model_fields
        assert "created_at" in Model.model_fields
        assert "updated_at" not in Model.model_fields

        # Test removing non-existent field
        builder = DomainModelBuilder("Model2")
        with pytest.raises(KeyError, match="Field 'nonexistent' not found"):
            builder.remove_field("nonexistent")

    def test_remove_fields(self):
        """Test removing multiple fields."""
        Model = (
            DomainModelBuilder("Model")
            .with_entity_fields()
            .with_audit_fields()
            .remove_fields("updated_at", "version", "nonexistent")
            .build()
        )

        assert "id" in Model.model_fields
        assert "created_by" in Model.model_fields
        assert "updated_at" not in Model.model_fields
        assert "version" not in Model.model_fields

    def test_preview(self):
        """Test preview functionality."""
        builder = (
            DomainModelBuilder("Model")
            .with_entity_fields()
            .add_field(
                "custom", FieldTemplate(base_type=str).with_description("Custom field")
            )
        )

        preview = builder.preview()

        assert isinstance(preview, dict)
        assert "id" in preview
        assert "custom" in preview
        assert preview["custom"] == "Custom field"
        assert preview["id"] == "Unique identifier"

    def test_build_empty(self):
        """Test building with no fields."""
        builder = DomainModelBuilder("EmptyModel")

        with pytest.raises(
            ValueError, match="Cannot build model 'EmptyModel' with no fields"
        ):
            builder.build()

    def test_method_chaining(self):
        """Test that all methods return self for chaining."""
        builder = DomainModelBuilder("Model")

        # All these methods should return the builder instance
        assert builder.with_entity_fields() is builder
        assert builder.with_soft_delete() is builder
        assert builder.with_audit_fields() is builder
        assert builder.add_field("test", ID_TEMPLATE) is builder
        assert builder.remove_field("test") is builder
        assert builder.remove_fields("nonexistent") is builder

    def test_complex_example(self):
        """Test a complex real-world example."""
        AuditedEntity = (
            DomainModelBuilder("AuditedEntity")
            .with_entity_fields(timezone_aware=True)
            .with_soft_delete(timezone_aware=True)
            .with_audit_fields()
            .add_field(
                "name", FieldTemplate(base_type=str).with_description("Entity name")
            )
            .add_field(
                "status",
                FieldTemplate(base_type=str)
                .with_default("active")
                .with_description("Entity status"),
            )
            .add_field(
                "metadata",
                FieldTemplate(base_type=dict)
                .with_default(dict)
                .with_description("Additional metadata"),
            )
            .build(from_attributes=True)
        )

        # Verify the model
        assert AuditedEntity.__name__ == "AuditedEntity"
        assert "id" in AuditedEntity.model_fields
        assert "created_at" in AuditedEntity.model_fields
        assert "deleted_at" in AuditedEntity.model_fields
        assert "version" in AuditedEntity.model_fields
        assert "status" in AuditedEntity.model_fields
        assert "metadata" in AuditedEntity.model_fields

        # Check configuration
        assert AuditedEntity.model_config["from_attributes"] is True

        # Create an instance
        entity = AuditedEntity(
            name="Test Entity", metadata={"tags": ["test", "example"]}
        )
        assert entity.status == "active"
        assert entity.version == 1
        assert entity.is_deleted is False
