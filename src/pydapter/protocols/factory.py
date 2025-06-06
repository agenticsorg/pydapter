"""Factory functions for creating protocol-compliant models."""

from typing import Any, Union

from pydantic import BaseModel
from pydapter.protocols.constants import ProtocolType
from pydapter.protocols.registry import get_mixin_registry


def create_protocol_model_class(
    name: str,
    *protocols: Union[ProtocolType, str],
    base_model: type[BaseModel] = BaseModel,
    **namespace: Any,
) -> type[BaseModel]:
    """Create a model class with both structural fields and behavioral methods.

    This is a convenience function that combines create_protocol_model (for fields)
    with the appropriate protocol mixins (for behavior) to create a fully functional
    protocol-compliant model class.

    Args:
        name: Name for the generated model class
        *protocols: Protocol names to implement (e.g., IDENTIFIABLE, TEMPORAL)
        base_model: Base model class to inherit from (default: BaseModel)
        **namespace: Additional class attributes/methods to include

    Returns:
        A new model class with both protocol fields and behaviors

    Example:
        ```python
        from pydapter.protocols import create_protocol_model_class, IDENTIFIABLE, TEMPORAL
        from pydapter.fields import FieldTemplate

        # Create a model with both fields and behaviors
        User = create_protocol_model_class(
            "User",
            IDENTIFIABLE,
            TEMPORAL,
            username=FieldTemplate(base_type=str),
            email=FieldTemplate(base_type=str)
        )

        # Now you can use it
        user = User(username="john", email="john@example.com")
        user.update_timestamp()  # Method from TemporalMixin
        ```
    """
    from pydapter.fields import create_protocol_model

    # Extract field templates from namespace
    field_templates = {}
    class_attrs = {}

    for key, value in namespace.items():
        # Check if it's a FieldTemplate (avoid circular import)
        if hasattr(value, "create_field") and hasattr(value, "base_type"):
            field_templates[key] = value
        else:
            class_attrs[key] = value

    # Create the structural model with fields
    structural_model = create_protocol_model(
        f"_{name}Structure", *protocols, **field_templates
    )

    # Collect the mixin classes
    mixins = []
    for protocol in protocols:
        protocol_str = str(protocol).lower()
        if protocol_str in get_mixin_registry():
            mixins.append(get_mixin_registry()[protocol_str])

    # Create the final class with mixins
    # Order: structural_model -> mixins -> base_model
    bases = (structural_model, *mixins, base_model)

    return type(name, bases, class_attrs)


def combine_with_mixins(
    model_class: type[BaseModel],
    *protocols: Union[ProtocolType, str],
    name: str = None,
) -> type[BaseModel]:
    """Add protocol mixins to an existing model class.

    This is useful when you already have a model with the required fields
    (e.g., from create_protocol_model) and want to add behavioral methods.

    Args:
        model_class: The model class to enhance with mixins
        *protocols: Protocol names whose mixins to add
        name: Optional name for the new class (defaults to original name)

    Returns:
        A new model class with the added behavioral mixins

    Example:
        ```python
        from pydapter.fields import create_protocol_model
        from pydapter.protocols import combine_with_mixins, IDENTIFIABLE, TEMPORAL

        # First create structure
        UserStructure = create_protocol_model(
            "UserStructure",
            IDENTIFIABLE,
            TEMPORAL,
            username=FieldTemplate(base_type=str)
        )

        # Then add behaviors
        User = combine_with_mixins(UserStructure, IDENTIFIABLE, TEMPORAL)
        ```
    """
    # Collect the mixin classes
    mixins = []
    for protocol in protocols:
        protocol_str = str(protocol).lower()
        if protocol_str in get_mixin_registry():
            mixins.append(get_mixin_registry()[protocol_str])

    # Determine the new class name
    class_name = name or model_class.__name__

    # Create new class with mixins
    return type(class_name, (model_class, *mixins), {})


__all__ = [
    "create_protocol_model_class",
    "combine_with_mixins",
]
