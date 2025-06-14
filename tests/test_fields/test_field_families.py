"""Tests for field families functionality."""

from pydapter.fields import (
    FieldFamilies,
    FieldTemplate,
    create_field_dict,
    create_model,
)


class TestFieldFamilies:
    """Test the FieldFamilies class and predefined field families."""

    def test_entity_family(self):
        """Test the ENTITY field family."""
        assert "id" in FieldFamilies.ENTITY
        assert "created_at" in FieldFamilies.ENTITY
        assert "updated_at" in FieldFamilies.ENTITY

        # Create a model with entity fields
        fields = create_field_dict(FieldFamilies.ENTITY)
        EntityModel = create_model("EntityModel", fields=fields)

        # Check that the model has the expected fields
        assert "id" in EntityModel.model_fields
        assert "created_at" in EntityModel.model_fields
        assert "updated_at" in EntityModel.model_fields

    def test_entity_tz_family(self):
        """Test the ENTITY_TZ field family with timezone-aware timestamps."""
        assert "id" in FieldFamilies.ENTITY_TZ
        assert "created_at" in FieldFamilies.ENTITY_TZ
        assert "updated_at" in FieldFamilies.ENTITY_TZ

        # The timezone-aware templates should be different from naive ones
        assert (
            FieldFamilies.ENTITY_TZ["created_at"] != FieldFamilies.ENTITY["created_at"]
        )

    def test_soft_delete_family(self):
        """Test the SOFT_DELETE field family."""
        assert "deleted_at" in FieldFamilies.SOFT_DELETE
        assert "is_deleted" in FieldFamilies.SOFT_DELETE

        # Create a model with soft delete fields
        fields = create_field_dict(FieldFamilies.SOFT_DELETE)
        SoftDeleteModel = create_model("SoftDeleteModel", fields=fields)

        # Check field types and defaults
        assert SoftDeleteModel.model_fields["is_deleted"].default is False
        assert SoftDeleteModel.model_fields["deleted_at"].default is None

    def test_audit_family(self):
        """Test the AUDIT field family."""
        expected_fields = ["created_by", "updated_by", "version"]
        for field in expected_fields:
            assert field in FieldFamilies.AUDIT

        # Create a model with audit fields
        fields = create_field_dict(FieldFamilies.AUDIT)
        AuditModel = create_model("AuditModel", fields=fields)

        # Check defaults
        assert AuditModel.model_fields["version"].default == 1
        assert AuditModel.model_fields["created_by"].default is None


class TestCreateFieldDict:
    """Test the create_field_dict function."""

    def test_single_family(self):
        """Test creating field dict from a single family."""
        fields = create_field_dict(FieldFamilies.ENTITY)

        assert "id" in fields
        assert "created_at" in fields
        assert "updated_at" in fields

        # Fields should be FieldTemplate instances
        for field in fields.values():
            assert isinstance(field, FieldTemplate)

    def test_multiple_families(self):
        """Test merging multiple field families."""
        fields = create_field_dict(
            FieldFamilies.ENTITY, FieldFamilies.AUDIT, FieldFamilies.SOFT_DELETE
        )

        # Should have fields from all families
        assert "id" in fields  # From ENTITY
        assert "version" in fields  # From AUDIT
        assert "is_deleted" in fields  # From SOFT_DELETE

    def test_family_override(self):
        """Test that later families override earlier ones."""
        # Create two families with overlapping fields
        family1 = {
            "name": FieldTemplate(base_type=str).with_description("Name from family1"),
            "value": FieldTemplate(base_type=int).with_default(1),
        }
        family2 = {
            "name": FieldTemplate(base_type=str).with_description("Name from family2"),
            "other": FieldTemplate(base_type=str).with_default("test"),
        }

        fields = create_field_dict(family1, family2)

        # family2's name should override family1's
        assert fields["name"].extract_metadata("description") == "Name from family2"
        assert "value" in fields
        assert "other" in fields

    def test_individual_overrides(self):
        """Test adding individual field overrides."""
        custom_id = FieldTemplate(base_type=str, description="Custom string ID")

        fields = create_field_dict(
            FieldFamilies.ENTITY,
            id=custom_id,
            custom_field=FieldTemplate(base_type=bool, default=True),
        )

        # Custom ID should override the one from ENTITY
        assert fields["id"].extract_metadata("description") == "Custom string ID"
        assert "custom_field" in fields

    def test_none_templates_ignored(self):
        """Test that None templates are ignored."""
        family = {
            "field1": FieldTemplate(base_type=str),
            "field2": None,
            "field3": FieldTemplate(base_type=int),
        }

        fields = create_field_dict(family)

        assert "field1" in fields
        assert "field2" not in fields
        assert "field3" in fields

    def test_create_model_with_families(self):
        """Test creating a complete model using field families."""
        # Combine multiple families
        fields = create_field_dict(
            FieldFamilies.ENTITY,
            FieldFamilies.AUDIT,
            FieldFamilies.SOFT_DELETE,
            name=FieldTemplate(base_type=str).with_default("unnamed"),
        )

        # Create the model
        TrackedEntity = create_model("TrackedEntity", fields=fields)

        # Verify the model has all expected fields
        assert "id" in TrackedEntity.model_fields
        assert "created_at" in TrackedEntity.model_fields
        assert "updated_at" in TrackedEntity.model_fields
        assert "version" in TrackedEntity.model_fields
        assert "is_deleted" in TrackedEntity.model_fields
        assert "name" in TrackedEntity.model_fields

        # Create an instance
        entity = TrackedEntity(name="test_entity")
        assert entity.name == "test_entity"
        assert entity.version == 1  # Default from AUDIT
        assert entity.is_deleted is False  # Default from SOFT_DELETE
