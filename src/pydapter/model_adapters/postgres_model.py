# postgres_model.py
from __future__ import annotations

import ipaddress
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    get_args,
    get_origin,
)

from pydantic import BaseModel
from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import (
    ARRAY,
    CIDR,
    DATERANGE,
    INET,
    INT4RANGE,
    JSONB,
    TSRANGE,
)

# Note: BOX, LINE, POINT are not directly available in SQLAlchemy
# We'll use String as a fallback for geometric types
from sqlalchemy.orm import DeclarativeBase

from pydapter.exceptions import TypeConversionError

from .sql_model import SQLModelAdapter, create_base
from .type_registry import TypeRegistry


class PostgresModelAdapter(SQLModelAdapter):
    """Extended adapter with PostgreSQL-specific type support."""

    def __init__(self):
        super().__init__()
        # Register PostgreSQL-specific types
        self._register_postgres_types()

    @classmethod
    def _register_postgres_types(cls):
        """Register PostgreSQL-specific type mappings."""
        # JSONB type
        cls.register_type_mapping(
            python_type=dict,
            sql_type_factory=lambda: JSONB(),
            python_to_sql=lambda x: x,
            sql_to_python=lambda x: x,
        )

        # Generic tuple type
        cls.register_type_mapping(
            python_type=tuple,
            sql_type_factory=lambda: String(255),
            python_to_sql=lambda x: str(x),
            sql_to_python=lambda x: eval(x) if x else None,
        )

        # Range types - need special handling for tests
        # We need to check the field's json_schema_extra to determine the range type
        # This is handled in the pydantic_model_to_sql method

        # Network types
        cls.register_type_mapping(
            python_type=ipaddress.IPv4Address,
            sql_type_factory=lambda: INET(),
            python_to_sql=lambda x: str(x),
            sql_to_python=lambda x: ipaddress.IPv4Address(x) if x else None,
        )

        cls.register_type_mapping(
            python_type=ipaddress.IPv6Address,
            sql_type_factory=lambda: INET(),
            python_to_sql=lambda x: str(x),
            sql_to_python=lambda x: ipaddress.IPv6Address(x) if x else None,
        )

        cls.register_type_mapping(
            python_type=ipaddress.IPv4Network,
            sql_type_factory=lambda: CIDR(),
            python_to_sql=lambda x: str(x),
            sql_to_python=lambda x: ipaddress.IPv4Network(x) if x else None,
        )

        cls.register_type_mapping(
            python_type=ipaddress.IPv6Network,
            sql_type_factory=lambda: CIDR(),
            python_to_sql=lambda x: str(x),
            sql_to_python=lambda x: ipaddress.IPv6Network(x) if x else None,
        )

        # Geometric types - using String as a fallback
        cls.register_type_mapping(
            python_type=tuple[float, float],
            sql_type_factory=lambda: String(255),
            python_to_sql=lambda x: f"({x[0]},{x[1]})",
            sql_to_python=lambda x: (
                tuple(float(v) for v in x.strip("()").split(",")) if x else None
            ),
        )

        cls.register_type_mapping(
            python_type=tuple[float, float, float, float],
            sql_type_factory=lambda: String(255),
            python_to_sql=lambda x: f"({x[0]},{x[1]},{x[2]},{x[3]})",
            sql_to_python=lambda x: (
                tuple(float(v) for v in x.strip("()").split(",")) if x else None
            ),
        )

    @classmethod
    def handle_jsonb(
        cls,
        field_name: str,
        field_info: Any,
        nested_model: Optional[Type[BaseModel]] = None,
    ) -> Tuple[Column, Optional[Callable]]:
        """
        Handle JSONB fields, potentially with nested Pydantic models.

        Args:
            field_name: The name of the field
            field_info: The field info object
            nested_model: Optional nested Pydantic model class

        Returns:
            A tuple of (Column, converter_function)
        """
        is_nullable = (
            cls.is_optional(field_info.annotation) or not field_info.is_required()
        )

        if nested_model is not None and issubclass(nested_model, BaseModel):
            # For nested models, add validation to ensure proper serialization
            def validate_and_serialize(value):
                if value is None:
                    return None
                # If it's already a dict, validate with the model
                if isinstance(value, dict):
                    value = nested_model(**value)
                # Convert model to dict for storage
                if isinstance(value, BaseModel):
                    return value.model_dump()
                raise TypeConversionError(
                    f"Expected dict or {nested_model.__name__}, got {type(value).__name__}",
                    source_type=type(value),
                    target_type=nested_model,
                    field_name=field_name,
                )

            return (
                Column(
                    JSONB,
                    nullable=is_nullable,
                    default=(
                        field_info.default if field_info.default is not None else None
                    ),
                ),
                validate_and_serialize,
            )

        # Regular JSONB without nested model validation
        return (
            Column(
                JSONB,
                nullable=is_nullable,
                default=field_info.default if field_info.default is not None else None,
            ),
            None,
        )

    @classmethod
    def handle_array(
        cls,
        item_type: type,
        dimensions: int = 1,
        nullable: bool = False,
        default: Any = None,
    ) -> Column:
        """
        Handle PostgreSQL ARRAY types with proper dimensions.

        Args:
            item_type: The type of items in the array
            dimensions: The number of dimensions in the array
            nullable: Whether the array can be NULL
            default: The default value for the array

        Returns:
            A Column object

        Raises:
            TypeConversionError: If the item type is not supported
        """
        sql_type_factory = TypeRegistry.get_sql_type(item_type)
        if sql_type_factory is None:
            raise TypeConversionError(
                f"Unsupported array item type: {item_type}",
                source_type=item_type,
            )

        return Column(
            ARRAY(sql_type_factory(), dimensions=dimensions),
            nullable=nullable,
            default=default,
        )

    @classmethod
    def pydantic_model_to_sql(
        cls,
        model: type[BaseModel],
        *,
        table_name: str | None = None,
        pk_field: str = "id",
        schema: str | None = None,
    ) -> type[DeclarativeBase]:
        """Generate a SQLAlchemy model from a Pydantic model with PostgreSQL-specific type handling."""

        ns: dict[str, Any] = {"__tablename__": table_name or model.__name__.lower()}

        # Add schema if provided
        if schema:
            ns["__table_args__"] = {"schema": schema}

        # Track relationships to add after all columns are defined
        relationships: Dict[str, Dict[str, Any]] = {}
        foreign_keys: Dict[str, Column] = {}

        for name, info in model.model_fields.items():
            anno = info.annotation
            origin = get_origin(anno) or anno

            # Check for relationship metadata
            if info.json_schema_extra and "relationship" in info.json_schema_extra:
                relationship_info = cls.handle_relationship(model, name, info)
                if relationship_info:
                    if "relationship" in relationship_info:
                        relationships[name] = relationship_info["relationship"]
                    if (
                        "foreign_key" in relationship_info
                        and relationship_info["foreign_key"]
                    ):
                        fk_name = relationship_info.get(
                            "foreign_key_name", f"{name}_id"
                        )
                        foreign_keys[fk_name] = relationship_info["foreign_key"]
                    continue

            # Check for PostgreSQL-specific type metadata
            if info.json_schema_extra and "db_type" in info.json_schema_extra:
                db_type = info.json_schema_extra["db_type"]

                # Handle range types
                if db_type == "range" or db_type in (
                    "int4range",
                    "daterange",
                    "tsrange",
                ):
                    # If db_type itself is a range type, use it as the range_type
                    range_type = info.json_schema_extra.get(
                        "range_type", "int4" if db_type == "range" else db_type
                    )
                    is_nullable = cls.is_optional(anno) or not info.is_required()
                    default = info.default if info.default is not None else None

                    if range_type == "int4" or range_type == "int4range":
                        sql_type = INT4RANGE()
                    elif range_type == "date" or range_type == "daterange":
                        sql_type = DATERANGE()
                    elif range_type == "timestamp" or range_type == "tsrange":
                        sql_type = TSRANGE()
                    else:
                        # Default to INT4RANGE
                        sql_type = INT4RANGE()

                    kwargs = {"nullable": is_nullable}
                    if default is not None:
                        kwargs["default"] = default

                    ns[name] = Column(sql_type, **kwargs)
                    continue

                # Handle JSONB with nested models
                elif db_type == "jsonb":
                    # Try to get nested model type
                    nested_model = None
                    if origin is dict:
                        # No nested model specified
                        pass
                    elif issubclass(origin, BaseModel):
                        nested_model = origin
                    elif cls.is_optional(anno):
                        # Handle Optional[Model]
                        args = get_args(anno)
                        non_none_args = [arg for arg in args if arg is not type(None)]
                        if len(non_none_args) == 1 and issubclass(
                            non_none_args[0], BaseModel
                        ):
                            nested_model = non_none_args[0]

                    column, converter = cls.handle_jsonb(name, info, nested_model)
                    ns[name] = column
                    continue

                # Handle ARRAY types
                elif db_type == "array":
                    dimensions = info.json_schema_extra.get("array_dimensions", 1)
                    item_type = get_args(anno)[0] if get_args(anno) else str

                    # Handle nested arrays
                    if dimensions > 1 and get_origin(item_type) in (list, List):
                        item_type = get_args(item_type)[0]

                    is_nullable = cls.is_optional(anno) or not info.is_required()
                    default = info.default if info.default is not None else None

                    ns[name] = cls.handle_array(
                        item_type, dimensions, is_nullable, default
                    )
                    continue

            # Handle list[X] as ARRAY by default
            if origin in (list, List) and get_args(anno):
                item_type = get_args(anno)[0]
                is_nullable = cls.is_optional(anno) or not info.is_required()
                default = info.default if info.default is not None else None

                # Skip if this is a vector field (handled by PGVectorModelAdapter)
                if item_type is float or (
                    isinstance(item_type, type) and issubclass(item_type, float)
                ):
                    if (
                        hasattr(cls, "_python_type_for")
                        and cls.__name__ == "PGVectorModelAdapter"
                    ):
                        continue

                ns[name] = cls.handle_array(item_type, 1, is_nullable, default)
                continue

            # Fall back to standard SQLModelAdapter behavior
            is_nullable = cls.is_optional(anno) or not info.is_required()
            if is_nullable:
                args = get_args(anno)
                non_none_args = [arg for arg in args if arg is not type(None)]
                if len(non_none_args) == 1:
                    inner = non_none_args[0]
                    anno, origin = inner, get_origin(inner) or inner

            # Get SQL type from TypeRegistry
            col_type_factory = TypeRegistry.get_sql_type(origin)
            if col_type_factory is None:
                raise TypeConversionError(
                    f"Unsupported type {origin!r}",
                    source_type=origin,
                    target_type=None,
                    field_name=name,
                    model_name=model.__name__,
                )

            kwargs: dict[str, Any] = {
                "nullable": is_nullable,
            }
            default = (
                info.default if info.default is not None else info.default_factory  # type: ignore[arg-type]
            )
            if default is not None:
                kwargs["default"] = default

            if name == pk_field:
                kwargs.update(primary_key=True, autoincrement=True)

            ns[name] = Column(col_type_factory(), **kwargs)

        # Add foreign keys
        for name, column in foreign_keys.items():
            ns[name] = column

        # Add relationships
        for name, rel in relationships.items():
            ns[name] = rel

        # Create a new base class with a fresh metadata for each model
        Base = create_base()
        return type(f"{model.__name__}SQL", (Base,), ns)
