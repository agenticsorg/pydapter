"""Example of using the new FieldTemplate system in pydapter.

This example demonstrates how to use FieldTemplate instead of the deprecated Field class.
"""

from pydapter.fields import FieldTemplate, create_model
from pydapter.fields.common_templates import (
    ID_TEMPLATE,
    NAME_TEMPLATE,
    EMAIL_TEMPLATE,
    CREATED_AT_TZ_TEMPLATE,
    UPDATED_AT_TZ_TEMPLATE,
)
from pydapter.fields.families import FieldFamilies, create_field_dict


def example_basic_field_template():
    """Example 1: Basic FieldTemplate usage"""
    print("Example 1: Basic FieldTemplate usage")
    print("-" * 50)
    
    # Create individual field templates
    age_field = FieldTemplate(int, description="Person's age", default=0)
    
    # Create a nullable field
    nickname_field = FieldTemplate(str, description="Optional nickname", nullable=True, default=None)
    
    # Create a field with validation
    def validate_positive(value: int) -> bool:
        return value >= 0
    
    score_field = FieldTemplate(
        int,
        description="Test score",
        validator=validate_positive,
        default=0,
    )
    
    # Create a model with these fields
    Person = create_model(
        "Person",
        fields={
            "id": ID_TEMPLATE,
            "name": NAME_TEMPLATE,
            "email": EMAIL_TEMPLATE,
            "age": age_field,
            "nickname": nickname_field,
            "score": score_field,
        }
    )
    
    # Create an instance
    person = Person(name="John Doe", email="john@example.com", age=30)
    print(f"Created person: {person}")
    print(f"Person ID: {person.id}")
    print()


def example_field_families():
    """Example 2: Using field families"""
    print("Example 2: Using field families")
    print("-" * 50)
    
    # Create a model using field families
    TrackedEntity = create_model(
        "TrackedEntity",
        fields=create_field_dict(
            FieldFamilies.ENTITY_TZ,  # id, created_at, updated_at with timezone
            FieldFamilies.SOFT_DELETE_TZ,  # deleted_at, is_deleted
            FieldFamilies.AUDIT,  # created_by, updated_by, version
            # Add custom fields
            title=FieldTemplate(str, description="Entity title"),
            description=FieldTemplate(str, description="Entity description", default=""),
        )
    )
    
    # Create an instance
    entity = TrackedEntity(title="Important Document")
    print(f"Created entity: {entity.title}")
    print(f"Entity ID: {entity.id}")
    print(f"Created at: {entity.created_at}")
    print(f"Version: {entity.version}")
    print()


def example_builder_pattern():
    """Example 3: Using DomainModelBuilder for fluent API"""
    print("Example 3: Using DomainModelBuilder")
    print("-" * 50)
    
    from pydapter.fields.builder import DomainModelBuilder
    
    # Build a model using the fluent API
    UserProfile = (
        DomainModelBuilder("UserProfile")
        .with_entity_fields(timezone_aware=True)
        .with_soft_delete(timezone_aware=True)
        .with_audit_fields()
        .add_field("username", FieldTemplate(str, description="Unique username"))
        .add_field("bio", FieldTemplate(str, description="User biography", default=""))
        .add_field("followers_count", FieldTemplate(int, default=0))
        .build()
    )
    
    # Create an instance
    user = UserProfile(username="alice_wonder")
    print(f"Created user: {user.username}")
    print(f"User ID: {user.id}")
    print(f"Followers: {user.followers_count}")
    print()


def example_advanced_templates():
    """Example 4: Advanced template features"""
    print("Example 4: Advanced template features")
    print("-" * 50)
    
    # Create a list field
    tags_field = FieldTemplate(str, listable=True, description="List of tags", default=list)
    
    # Create a nullable dict field
    config_field = FieldTemplate(
        dict,
        description="Configuration settings",
        default=dict,
        nullable=True,
    )
    
    # Create model with advanced fields
    Article = create_model(
        "Article",
        fields={
            "id": ID_TEMPLATE,
            "title": NAME_TEMPLATE,
            "tags": tags_field,
            "config": config_field,
            "created_at": CREATED_AT_TZ_TEMPLATE,
            "updated_at": UPDATED_AT_TZ_TEMPLATE,
        }
    )
    
    # Create an instance
    article = Article(
        title="Introduction to FieldTemplate",
        tags=["python", "pydapter", "fields"],
        config={"featured": True, "comments_enabled": False}
    )
    print(f"Article: {article.title}")
    print(f"Tags: {article.tags}")
    print(f"Config: {article.config}")
    print()


def example_migration_from_field():
    """Example 5: Migrating from old Field to FieldTemplate"""
    print("Example 5: Migration from Field to FieldTemplate")
    print("-" * 50)
    
    # Old way (deprecated):
    # from pydapter.fields import Field
    # old_field = Field(
    #     name="status",
    #     annotation=str,
    #     default="active",
    #     description="Status of the record"
    # )
    
    # New way with FieldTemplate:
    status_field = FieldTemplate(str, description="Status of the record", default="active")
    
    # Create model with new approach
    StatusModel = create_model(
        "StatusModel",
        fields={
            "id": ID_TEMPLATE,
            "status": status_field,
        }
    )
    
    instance = StatusModel()
    print(f"Status: {instance.status}")
    print(f"ID: {instance.id}")
    print()


if __name__ == "__main__":
    example_basic_field_template()
    example_field_families()
    example_builder_pattern()
    example_advanced_templates()
    example_migration_from_field()
    
    print("All examples completed successfully!")