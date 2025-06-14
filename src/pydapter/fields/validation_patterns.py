"""Validation Patterns - Common validation patterns for field templates.

This module provides pre-built validation patterns and constraint builders
for creating field templates with consistent validation rules.
"""

from __future__ import annotations

import re
from re import Pattern
from typing import Any, Callable

from pydantic import confloat, conint, constr

from pydapter.fields.template import FieldTemplate

__all__ = (
    "ValidationPatterns",
    "create_pattern_template",
    "create_range_template",
)


class ValidationPatterns:
    """Common validation patterns for field templates.

    This class provides regex patterns and validation functions for common
    field types like emails, URLs, phone numbers, etc. These can be used
    with FieldTemplate to create consistently validated fields.
    """

    # Email pattern (simplified, RFC-compliant email validation is complex)
    EMAIL = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

    # URL patterns
    HTTP_URL = re.compile(
        r"^https?://[a-zA-Z0-9.-]+(?:\.[a-zA-Z]{2,})+(?:/[^?#]*)?(?:\?[^#]*)?(?:#.*)?$"
    )
    HTTPS_URL = re.compile(
        r"^https://[a-zA-Z0-9.-]+(?:\.[a-zA-Z]{2,})+(?:/[^?#]*)?(?:\?[^#]*)?(?:#.*)?$"
    )

    # Phone patterns
    US_PHONE = re.compile(
        r"^\+?1?\s*\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})$"
    )
    INTERNATIONAL_PHONE = re.compile(r"^\+?[0-9\s\-\(\)]{10,20}$")

    # Username patterns
    USERNAME_ALPHANUMERIC = re.compile(r"^[a-zA-Z0-9_]{3,32}$")
    USERNAME_WITH_DASH = re.compile(r"^[a-zA-Z0-9_-]{3,32}$")
    USERNAME_STRICT = re.compile(r"^[a-z][a-z0-9_]{2,31}$")  # Must start with lowercase

    # Password patterns (for validation, not storage)
    PASSWORD_STRONG = re.compile(
        r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$"
    )

    # Identifier patterns
    SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    UUID = re.compile(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
        re.IGNORECASE,
    )
    ALPHANUMERIC_ID = re.compile(r"^[A-Z0-9]{6,12}$")

    # Code patterns
    HEX_COLOR = re.compile(r"^#?([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$")
    ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    ISO_DATETIME = re.compile(
        r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?$"
    )

    # Geographic patterns
    LATITUDE = re.compile(r"^[-+]?([1-8]?\d(\.\d+)?|90(\.0+)?)$")
    LONGITUDE = re.compile(r"^[-+]?(180(\.0+)?|((1[0-7]\d)|([1-9]?\d))(\.\d+)?)$")
    ZIP_US = re.compile(r"^\d{5}(-\d{4})?$")
    ZIP_CA = re.compile(r"^[A-Z]\d[A-Z]\s?\d[A-Z]\d$", re.IGNORECASE)

    # Financial patterns
    CREDIT_CARD = re.compile(r"^\d{13,19}$")
    IBAN = re.compile(r"^[A-Z]{2}\d{2}[A-Z0-9]{1,30}$")
    BITCOIN_ADDRESS = re.compile(r"^(bc1|[13])[a-zA-HJ-NP-Z0-9]{25,39}$")

    # Social media patterns
    TWITTER_HANDLE = re.compile(r"^@[A-Za-z0-9_]{1,15}$")
    INSTAGRAM_HANDLE = re.compile(r"^@[A-Za-z0-9_.]{1,30}$")
    HASHTAG = re.compile(r"^#[A-Za-z0-9_]+$")

    @staticmethod
    def validate_pattern(
        pattern: Pattern[str], error_message: str
    ) -> Callable[[str], str]:
        """Create a validator function for a regex pattern.

        Args:
            pattern: Compiled regex pattern
            error_message: Error message to show on validation failure

        Returns:
            A validator function that checks the pattern
        """

        def validator(value: str) -> str:
            if not isinstance(value, str):
                raise ValueError(f"Expected string, got {type(value).__name__}")
            if not pattern.match(value):
                raise ValueError(error_message)
            return value

        return validator

    @staticmethod
    def normalize_whitespace() -> Callable[[str], str]:
        """Create a validator that normalizes whitespace in strings."""

        def validator(value: str) -> str:
            if isinstance(value, str):
                # Strip leading/trailing whitespace and normalize internal spaces
                return " ".join(value.split())
            return value

        return validator

    @staticmethod
    def strip_whitespace() -> Callable[[str], str]:
        """Create a validator that strips leading/trailing whitespace."""

        def validator(value: str) -> str:
            if isinstance(value, str):
                return value.strip()
            return value

        return validator

    @staticmethod
    def lowercase() -> Callable[[str], str]:
        """Create a validator that converts strings to lowercase."""

        def validator(value: str) -> str:
            if isinstance(value, str):
                return value.lower()
            return value

        return validator

    @staticmethod
    def uppercase() -> Callable[[str], str]:
        """Create a validator that converts strings to uppercase."""

        def validator(value: str) -> str:
            if isinstance(value, str):
                return value.upper()
            return value

        return validator

    @staticmethod
    def titlecase() -> Callable[[str], str]:
        """Create a validator that converts strings to title case."""

        def validator(value: str) -> str:
            if isinstance(value, str):
                return value.title()
            return value

        return validator


def create_pattern_template(
    pattern: str | Pattern[str],
    base_type: type = str,
    description: str = "Pattern-validated field",
    error_message: str | None = None,
    **kwargs: Any,
) -> FieldTemplate:
    """Create a FieldTemplate with pattern validation.

    Args:
        pattern: Regex pattern (string or compiled Pattern)
        base_type: Base type for the field (default: str)
        description: Field description
        error_message: Custom error message for validation failures
        **kwargs: Additional arguments for FieldTemplate

    Returns:
        A FieldTemplate with pattern validation

    Examples:
        ```python
        # Create a field for US phone numbers
        us_phone = create_pattern_template(
            ValidationPatterns.US_PHONE,
            description="US phone number",
            error_message="Invalid US phone number format"
        )

        # Create a field for slugs
        slug_field = create_pattern_template(
            r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
            description="URL-friendly slug",
            error_message="Slug must contain only lowercase letters, numbers, and hyphens"
        )
        ```
    """
    if isinstance(pattern, str):
        pattern = re.compile(pattern)

    if error_message is None:
        error_message = f"Value does not match pattern: {pattern.pattern}"

    # Use constr for pattern validation
    annotated_type = constr(pattern=pattern.pattern)

    # Create template with description and all kwargs
    template_kwargs = {"description": description}
    template_kwargs.update(kwargs)

    return FieldTemplate(base_type=annotated_type, **template_kwargs)


def create_range_template(
    base_type: type[int] | type[float],
    *,
    gt: int | float | None = None,
    ge: int | float | None = None,
    lt: int | float | None = None,
    le: int | float | None = None,
    description: str = "Range-constrained numeric field",
    **kwargs: Any,
) -> FieldTemplate:
    """Create a FieldTemplate with numeric range constraints.

    Args:
        base_type: Either int or float
        gt: Greater than constraint
        ge: Greater than or equal constraint
        lt: Less than constraint
        le: Less than or equal constraint
        description: Field description
        **kwargs: Additional arguments for FieldTemplate

    Returns:
        A FieldTemplate with range constraints

    Examples:
        ```python
        # Create a percentage field (0-100)
        percentage = create_range_template(
            float,
            ge=0,
            le=100,
            description="Percentage value"
        )

        # Create an age field (0-150)
        age = create_range_template(
            int,
            ge=0,
            le=150,
            description="Person's age"
        )

        # Create a temperature field (-273.15 to infinity)
        temperature_celsius = create_range_template(
            float,
            gt=-273.15,
            description="Temperature in Celsius"
        )
        ```
    """
    if base_type is int:
        # Use conint for integer constraints
        annotated_type = conint(gt=gt, ge=ge, lt=lt, le=le)
    elif base_type is float:
        # Use confloat for float constraints
        annotated_type = confloat(gt=gt, ge=ge, lt=lt, le=le)
    else:
        raise ValueError("base_type must be int or float")

    # Create template with description and all kwargs
    template_kwargs = {"description": description}
    template_kwargs.update(kwargs)

    return FieldTemplate(base_type=annotated_type, **template_kwargs)


# Pre-built validation templates are created dynamically
# to ensure proper handling of the error_message parameter
VALIDATION_TEMPLATES = {
    "email": create_pattern_template(
        ValidationPatterns.EMAIL,
        description="Email address",
        error_message="Invalid email address format",
    ),
    "url": create_pattern_template(
        ValidationPatterns.HTTP_URL,
        description="HTTP/HTTPS URL",
        error_message="Invalid URL format",
    ),
    "https_url": create_pattern_template(
        ValidationPatterns.HTTPS_URL,
        description="HTTPS URL",
        error_message="Invalid HTTPS URL format",
    ),
    "us_phone": create_pattern_template(
        ValidationPatterns.US_PHONE,
        description="US phone number",
        error_message="Invalid US phone number format",
    ),
    "username": create_pattern_template(
        ValidationPatterns.USERNAME_WITH_DASH,
        description="Username",
        error_message="Username must be 3-32 characters, alphanumeric with underscores and dashes",
    ),
    "slug": create_pattern_template(
        ValidationPatterns.SLUG,
        description="URL slug",
        error_message="Slug must contain only lowercase letters, numbers, and hyphens",
    ),
    "hex_color": create_pattern_template(
        ValidationPatterns.HEX_COLOR,
        description="Hex color code",
        error_message="Invalid hex color format (e.g., #FF0000 or FF0000)",
    ),
    "zip_us": create_pattern_template(
        ValidationPatterns.ZIP_US,
        description="US ZIP code",
        error_message="Invalid US ZIP code format (e.g., 12345 or 12345-6789)",
    ),
}
