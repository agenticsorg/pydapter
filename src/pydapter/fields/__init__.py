from pydapter.fields.builder import DomainModelBuilder
from pydapter.fields.common_templates import (
    CREATED_AT_TEMPLATE,
    CREATED_AT_TZ_TEMPLATE,
    DELETED_AT_TEMPLATE,
    DELETED_AT_TZ_TEMPLATE,
    DESCRIPTION_TEMPLATE,
    EMAIL_TEMPLATE,
    ID_TEMPLATE,
    JSON_TEMPLATE,
    METADATA_TEMPLATE,
    NAME_TEMPLATE,
    NONNEGATIVE_INT_TEMPLATE,
    PERCENTAGE_TEMPLATE,
    PHONE_TEMPLATE,
    POSITIVE_FLOAT_TEMPLATE,
    POSITIVE_INT_TEMPLATE,
    STRING_TEMPLATE,
    TAGS_TEMPLATE,
    UPDATED_AT_TEMPLATE,
    UPDATED_AT_TZ_TEMPLATE,
    URL_TEMPLATE,
    USERNAME_TEMPLATE,
)
from pydapter.fields.dts import (
    DATETIME,
    DATETIME_NULLABLE,
    datetime_serializer,
    validate_datetime,
)
from pydapter.fields.embedding import EMBEDDING, validate_embedding
from pydapter.fields.execution import EXECUTION, Execution
from pydapter.fields.families import FieldFamilies, create_field_dict
from pydapter.fields.ids import (
    ID_FROZEN,
    ID_MUTABLE,
    ID_NULLABLE,
    serialize_uuid,
    validate_uuid,
)
from pydapter.fields.params import (
    PARAM_TYPE,
    PARAM_TYPE_NULLABLE,
    PARAMS,
    validate_model_to_params,
    validate_model_to_type,
)
from pydapter.fields.protocol_families import (
    ProtocolFieldFamilies,
    create_protocol_model,
)

# Import new trait families
from pydapter.fields.trait_families import (
    TraitFieldFamilies,
    create_trait_model,
)
from pydapter.fields.template import FieldTemplate
from pydapter.fields.types import Field  # Deprecated - kept for backwards compatibility
from pydapter.fields.types import (
    ID,
    Embedding,
    Metadata,
    Undefined,
    UndefinedType,
    create_model,
)
from pydapter.fields.validation_patterns import (
    ValidationPatterns,
    create_pattern_template,
    create_range_template,
)

__all__ = (
    "DATETIME",
    "DATETIME_NULLABLE",
    "validate_datetime",
    "datetime_serializer",
    "ID_FROZEN",
    "ID_MUTABLE",
    "ID_NULLABLE",
    "validate_uuid",
    "serialize_uuid",
    "PARAMS",
    "PARAM_TYPE",
    "PARAM_TYPE_NULLABLE",
    "validate_model_to_params",
    "validate_model_to_type",
    "EMBEDDING",
    "validate_embedding",
    "UndefinedType",
    "Undefined",
    "Field",
    "create_model",
    "Execution",
    "EXECUTION",
    "ID",
    "Embedding",
    "Metadata",
    "FieldTemplate",
    "ID_TEMPLATE",
    "STRING_TEMPLATE",
    "EMAIL_TEMPLATE",
    "USERNAME_TEMPLATE",
    "CREATED_AT_TEMPLATE",
    "UPDATED_AT_TEMPLATE",
    "DELETED_AT_TEMPLATE",
    "CREATED_AT_TZ_TEMPLATE",
    "UPDATED_AT_TZ_TEMPLATE",
    "DELETED_AT_TZ_TEMPLATE",
    "NAME_TEMPLATE",
    "DESCRIPTION_TEMPLATE",
    "URL_TEMPLATE",
    "PHONE_TEMPLATE",
    "POSITIVE_INT_TEMPLATE",
    "NONNEGATIVE_INT_TEMPLATE",
    "POSITIVE_FLOAT_TEMPLATE",
    "PERCENTAGE_TEMPLATE",
    "JSON_TEMPLATE",
    "TAGS_TEMPLATE",
    "METADATA_TEMPLATE",
    "FieldFamilies",
    "create_field_dict",
    "DomainModelBuilder",
    "ProtocolFieldFamilies",  # Deprecated
    "create_protocol_model",  # Deprecated
    "TraitFieldFamilies",
    "create_trait_model",
    "ValidationPatterns",
    "create_pattern_template",
    "create_range_template",
)
