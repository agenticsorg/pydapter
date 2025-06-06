# pg_vector_model.py
from __future__ import annotations

from typing import (
    Annotated,
    Any,
    Dict,
    List,
    Literal,
    Optional,
    cast,
    get_args,
    get_origin,
)

from pgvector.sqlalchemy import Vector
from pydantic import BaseModel, Field, create_model
from pydapter.exceptions import ConfigurationError, TypeConversionError, ValidationError
from sqlalchemy import Column, Index, func, inspect, select
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Session

from .sql_model import SQLModelAdapter, create_base
from .type_registry import TypeRegistry


class PGVectorModelAdapter(SQLModelAdapter):
    """Adapter that adds pgvector (list[float]) and JSONB support with optimizations."""

    def __init__(self):
        super().__init__()
        # Register dict types for JSONB
        self._register_json_types()

    @classmethod
    def _register_json_types(cls):
        """Register dict and Dict types for JSONB support."""
        # Register plain dict
        cls.register_type_mapping(
            python_type=dict,
            sql_type_factory=lambda: JSONB(),
            python_to_sql=lambda x: x,
            sql_to_python=lambda x: x,
        )

        # Register Dict[str, Any]
        cls.register_type_mapping(
            python_type=Dict[str, Any],
            sql_type_factory=lambda: JSONB(),
            python_to_sql=lambda x: x,
            sql_to_python=lambda x: x,
        )

    # override / extend mappings ------------------------------------------------
    @classmethod
    def _python_type_for(cls, column) -> type:
        if isinstance(column.type, Vector):
            return list[float]
        return super()._python_type_for(column)

    @classmethod
    def sql_model_to_pydantic(
        cls,
        orm_cls: type[DeclarativeBase],
        *,
        name_suffix: str = "Schema",
    ):
        """Add vector_dim metadata when converting back to Pydantic."""

        mapper = cast(Any, inspect(orm_cls))
        fields: dict[str, tuple[type, Any]] = {}

        for col in mapper.columns:
            if isinstance(col.type, Vector):
                py_type = list[float] | (None if col.nullable else Any)
                extra = {"vector_dim": col.type.dim}
                default_val = None if col.nullable else ...
                fields[col.key] = (
                    Annotated[py_type, Field(json_schema_extra=extra)],
                    default_val,
                )
            else:
                py_type = cls._python_type_for(col)
                if col.nullable:
                    py_type = py_type | None
                default_val = (
                    col.default.arg
                    if col.default is not None
                    and getattr(col.default, "is_scalar", False)
                    else (None if col.nullable or col.primary_key else ...)
                )
                fields[col.key] = (py_type, default_val)

        # Process relationships
        if hasattr(mapper, "relationships"):
            for name, rel in mapper.relationships.items():
                # Skip if already processed as a column
                if name in fields:
                    continue

                target_cls = rel.mapper.class_
                target_name = target_cls.__name__

                # Handle relationship types
                if rel.uselist:
                    # One-to-many or many-to-many
                    py_type = list[target_name]  # type: ignore
                    default_val = Field(default_factory=list)
                else:
                    # One-to-one or many-to-one
                    py_type = Optional[target_name]  # type: ignore
                    default_val = None

                # Add relationship metadata
                rel_type = "one_to_many" if rel.uselist else "one_to_one"
                if hasattr(rel, "direction"):
                    if rel.direction.name == "MANYTOONE":
                        rel_type = "many_to_one"
                    elif rel.direction.name == "ONETOMANY":
                        rel_type = "one_to_many"

                extra = {
                    "relationship": {
                        "type": rel_type,
                        "model": target_name,
                    }
                }

                if rel.back_populates:
                    extra["relationship"]["back_populates"] = rel.back_populates

                fields[name] = (
                    Annotated[py_type, Field(json_schema_extra=extra)],  # type: ignore
                    default_val,
                )

        pyd_cls = create_model(
            f"{orm_cls.__name__}{name_suffix}",
            __base__=BaseModel,
            **fields,
        )

        # Set model_config for Pydantic v2 compatibility
        pyd_cls.model_config = {"from_attributes": True}

        # For backward compatibility
        pyd_cls.model_config["orm_mode"] = True

        return pyd_cls

    @classmethod
    def validate_vector_dimensions(
        cls, vector: list[float] | None, expected_dim: int | None
    ) -> list[float] | None:
        """
        Validate that the vector has the expected dimensions.

        Args:
            vector: The vector to validate
            expected_dim: The expected dimension of the vector

        Returns:
            The validated vector

        Raises:
            ValidationError: If the vector has incorrect dimensions
            TypeConversionError: If the vector is not a list
        """
        if vector is None:
            return None

        if not isinstance(vector, list):
            raise TypeConversionError(
                f"Expected list for vector, got {type(vector)}",
                source_type=type(vector),
                target_type=list,
            )

        if expected_dim is not None and len(vector) != expected_dim:
            raise ValidationError(
                f"Vector has {len(vector)} dimensions, expected {expected_dim}",
                data=vector,
            )

        return vector

    @classmethod
    def create_index(
        cls,
        model: type[DeclarativeBase],
        field: str,
        index_type: str = "hnsw",
        params: dict[str, Any] | None = None,
    ) -> Index:
        """
        Create an appropriate index for vector search.

        Args:
            model: The SQLAlchemy model class
            field: The name of the vector field
            index_type: The type of index to create ("hnsw", "ivfflat", or "exact")
            params: Additional parameters for the index

        Returns:
            An Index object

        Raises:
            ConfigurationError: If the index type is not supported
        """
        params = params or {}
        col = getattr(model, field)

        if index_type == "hnsw":
            return Index(
                f"idx_{field}_hnsw",
                col,
                postgresql_using="hnsw",
                postgresql_with=params,
            )
        elif index_type == "ivfflat":
            return Index(
                f"idx_{field}_ivfflat",
                col,
                postgresql_using="ivfflat",
                postgresql_with=params,
            )
        elif index_type == "exact":
            # No specialized index, use standard btree
            return Index(f"idx_{field}", col)
        else:
            raise ConfigurationError(
                f"Unsupported index type: {index_type}",
                config={"index_type": index_type, "params": params},
            )

    @classmethod
    def find_similar(
        cls,
        session: Session,
        model: type[DeclarativeBase],
        field: str,
        vector: list[float],
        limit: int = 10,
        metric: str = "l2",
    ) -> Any:
        """
        Find similar vectors using specified distance metric.

        Args:
            session: The SQLAlchemy session
            model: The SQLAlchemy model class
            field: The name of the vector field
            vector: The query vector
            limit: The maximum number of results to return
            metric: The distance metric to use ("l2", "cosine", or "inner")

        Returns:
            A SQLAlchemy query object

        Raises:
            ConfigurationError: If the metric is not supported
        """
        col = getattr(model, field)

        if metric == "l2":
            return session.execute(
                select(model).order_by(func.l2_distance(col, vector)).limit(limit)
            )
        elif metric == "cosine":
            return session.execute(
                select(model).order_by(func.cosine_distance(col, vector)).limit(limit)
            )
        elif metric == "inner":
            # For inner product, we want to maximize the value, so we negate it
            return session.execute(
                select(model)
                .order_by(func.inner_product(col, vector).desc())
                .limit(limit)
            )
        else:
            raise ConfigurationError(
                f"Unsupported similarity metric: {metric}",
                config={"metric": metric},
            )

    @classmethod
    def batch_insert(
        cls,
        session: Session,
        model: type[DeclarativeBase],
        items: list[dict[str, Any]],
        batch_size: int = 1000,
    ) -> None:
        """
        Insert multiple items in batches for better performance.

        Args:
            session: The SQLAlchemy session
            model: The SQLAlchemy model class
            items: A list of dictionaries with item data
            batch_size: The number of items to insert in each batch
        """
        # Process items in batches
        for i in range(0, len(items), batch_size):
            batch = items[i : i + batch_size]

            # Create model instances
            instances = [model(**item) for item in batch]

            # Add all instances to the session
            session.add_all(instances)

            # Flush to the database
            session.flush()

        # Commit the transaction
        session.commit()

    @classmethod
    def pydantic_model_to_sql(
        cls,
        model: type[BaseModel],
        *,
        table_name: str | None = None,
        pk_field: str = "id",
        schema: str | None = None,
    ) -> type[DeclarativeBase]:
        """
        Generate a SQLAlchemy model from a Pydantic model.

        This method extends the base SQLModelAdapter to also handle:
        - list[float] fields with vector_dim metadata as pgvector Vector columns
        - dict and Dict[str, Any] types as JSONB
        - List[str] and other list types as PostgreSQL arrays
        """

        # First, register JSON types if not already registered
        cls._register_json_types()

        ns: dict[str, Any] = {"__tablename__": table_name or model.__name__.lower()}

        # Add schema if provided
        if schema:
            ns["__table_args__"] = {"schema": schema}

        # Process each field
        for name, info in model.model_fields.items():
            anno = info.annotation
            origin = get_origin(anno) or anno

            # Check for nullable
            is_nullable = cls.is_optional(anno) or not info.is_required()
            if is_nullable:
                args = get_args(anno)
                non_none_args = [arg for arg in args if arg is not type(None)]
                if len(non_none_args) == 1:
                    inner = non_none_args[0]
                    anno, origin = inner, get_origin(inner) or inner

            # Handle vector fields (list[float])
            if origin in (list, List) and get_args(anno):
                item_type = get_args(anno)[0]
                if item_type is float:
                    # Check for vector_dim metadata
                    vector_dim = None
                    if info.json_schema_extra:
                        vector_dim = info.json_schema_extra.get("vector_dim")

                    if vector_dim:
                        # Create Vector column
                        kwargs = {"nullable": is_nullable}
                        default = (
                            info.default
                            if info.default is not None
                            else info.default_factory
                        )
                        if default is not None:
                            kwargs["default"] = default

                        ns[name] = Column(Vector(vector_dim), **kwargs)
                        continue

            # Handle dict types as JSONB
            if origin is dict or origin is Dict:
                kwargs = {"nullable": is_nullable}
                default = (
                    info.default if info.default is not None else info.default_factory
                )
                if default is not None:
                    kwargs["default"] = default

                ns[name] = Column(JSONB(), **kwargs)
                continue

            # Handle Literal types as String
            if origin is Literal:
                kwargs = {"nullable": is_nullable}
                default = (
                    info.default if info.default is not None else info.default_factory
                )
                if default is not None:
                    kwargs["default"] = default

                # Get the max length from literal values
                literal_values = get_args(anno)
                max_length = (
                    max(len(str(v)) for v in literal_values) if literal_values else 50
                )

                ns[name] = Column(TypeRegistry._PY_TO_SQL[str](), **kwargs)
                continue

            # Handle List[str] and other list types as arrays
            if origin in (list, List):
                args = get_args(anno)
                if args:
                    item_type = args[0]
                else:
                    # Default to string for untyped lists
                    item_type = str

                # Get SQL type for item
                sql_type_factory = TypeRegistry.get_sql_type(item_type)
                if sql_type_factory:
                    kwargs = {"nullable": is_nullable}
                    default = (
                        info.default
                        if info.default is not None
                        else info.default_factory
                    )
                    if default is not None:
                        kwargs["default"] = default

                    ns[name] = Column(ARRAY(sql_type_factory()), **kwargs)
                    continue

            # Default handling for other types
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
            default = info.default if info.default is not None else info.default_factory
            if default is not None:
                kwargs["default"] = default

            if name == pk_field:
                kwargs.update(primary_key=True, autoincrement=True)

            ns[name] = Column(col_type_factory(), **kwargs)

        # Create the SQL model class
        Base = create_base()
        return type(f"{model.__name__}SQL", (Base,), ns)
