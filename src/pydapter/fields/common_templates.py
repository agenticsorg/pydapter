from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated, Any

from pydantic import AwareDatetime, EmailStr
from pydantic import Field as PydanticField
from pydantic import HttpUrl, NaiveDatetime, confloat, conint, constr

from pydapter.fields.template import FieldTemplate

__all__ = (
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
)


# ID Templates
ID_TEMPLATE = FieldTemplate(
    base_type=uuid.UUID,
    description="Unique identifier",
    default=uuid.uuid4,
)

# String Templates
STRING_TEMPLATE = FieldTemplate(
    base_type=str,
    description="String field",
)

# Using Pydantic v2 EmailStr for email validation
EMAIL_TEMPLATE = FieldTemplate(
    base_type=EmailStr,
    description="Email address",
)

# Username with pattern constraint using constr
USERNAME_TEMPLATE = FieldTemplate(
    base_type=constr(pattern=r"^[a-zA-Z0-9_-]{3,32}$"),
    description="Username",
)

NAME_TEMPLATE = FieldTemplate(
    base_type=Annotated[str, PydanticField(min_length=1, max_length=255)],
    description="Name field",
)

DESCRIPTION_TEMPLATE = FieldTemplate(
    base_type=str,
    description="Description field",
    default="",
)

# Using Pydantic v2 HttpUrl for URL validation
URL_TEMPLATE = FieldTemplate(
    base_type=HttpUrl,
    description="URL field",
)

# Phone number with pattern constraint
PHONE_TEMPLATE = FieldTemplate(
    base_type=constr(pattern=r"^\+?[0-9\s\-\(\)]{10,20}$"),
    description="Phone number",
)

# Datetime Templates - Naive (without timezone)
CREATED_AT_TEMPLATE = FieldTemplate(
    base_type=NaiveDatetime,
    description="Creation timestamp (naive)",
    default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
)

UPDATED_AT_TEMPLATE = FieldTemplate(
    base_type=NaiveDatetime,
    description="Last update timestamp (naive)",
    default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
)

DELETED_AT_TEMPLATE = FieldTemplate(
    base_type=NaiveDatetime,
    description="Deletion timestamp (naive)",
    nullable=True,
)

# Datetime Templates - Timezone Aware (recommended)
CREATED_AT_TZ_TEMPLATE = FieldTemplate(
    base_type=AwareDatetime,
    description="Creation timestamp (timezone-aware)",
    default=lambda: datetime.now(timezone.utc),
)

UPDATED_AT_TZ_TEMPLATE = FieldTemplate(
    base_type=AwareDatetime,
    description="Last update timestamp (timezone-aware)",
    default=lambda: datetime.now(timezone.utc),
)

DELETED_AT_TZ_TEMPLATE = FieldTemplate(
    base_type=AwareDatetime,
    description="Deletion timestamp (timezone-aware)",
    nullable=True,
)

# Numeric Templates using Pydantic v2 constraints
POSITIVE_INT_TEMPLATE = FieldTemplate(
    base_type=conint(gt=0),
    description="Positive integer",
)

NONNEGATIVE_INT_TEMPLATE = FieldTemplate(
    base_type=conint(ge=0),
    description="Non-negative integer",
    default=0,
)

POSITIVE_FLOAT_TEMPLATE = FieldTemplate(
    base_type=confloat(gt=0),
    description="Positive float",
)

PERCENTAGE_TEMPLATE = FieldTemplate(
    base_type=confloat(ge=0, le=100),
    description="Percentage value (0-100)",
    default=0.0,
)

# JSON/Dict Templates for JSONB support
JSON_TEMPLATE = FieldTemplate(
    base_type=dict,
    description="JSON data",
    default=dict,
    json_schema_extra={"db_type": "jsonb"},
)

# Common collection templates
TAGS_TEMPLATE = FieldTemplate(
    base_type=list[str],
    description="List of tags",
    default=list,
)

METADATA_TEMPLATE = FieldTemplate(
    base_type=dict[str, Any],
    description="Metadata dictionary",
    default=dict,
    json_schema_extra={"db_type": "jsonb"},
)
