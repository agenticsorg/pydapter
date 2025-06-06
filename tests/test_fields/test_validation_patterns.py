"""Tests for validation patterns functionality."""

import re

import pytest
from pydantic import ValidationError
from pydapter.fields import (
    FieldTemplate,
    ValidationPatterns,
    create_model,
    create_pattern_template,
    create_range_template,
)


class TestValidationPatterns:
    """Test the ValidationPatterns class."""

    def test_email_pattern(self):
        """Test email validation pattern."""
        pattern = ValidationPatterns.EMAIL

        # Valid emails
        assert pattern.match("user@example.com")
        assert pattern.match("user.name@example.com")
        assert pattern.match("user+tag@example.co.uk")

        # Invalid emails
        assert not pattern.match("invalid")
        assert not pattern.match("@example.com")
        assert not pattern.match("user@")
        assert not pattern.match("user@.com")

    def test_url_patterns(self):
        """Test URL validation patterns."""
        # HTTP/HTTPS URLs
        http_pattern = ValidationPatterns.HTTP_URL
        assert http_pattern.match("http://example.com")
        assert http_pattern.match("https://example.com")
        assert http_pattern.match("https://sub.example.com/path?query=1#anchor")
        assert not http_pattern.match("ftp://example.com")
        assert not http_pattern.match("not a url")

        # HTTPS only
        https_pattern = ValidationPatterns.HTTPS_URL
        assert https_pattern.match("https://example.com")
        assert not https_pattern.match("http://example.com")

    def test_phone_patterns(self):
        """Test phone number validation patterns."""
        # US phone
        us_pattern = ValidationPatterns.US_PHONE
        assert us_pattern.match("1234567890")
        assert us_pattern.match("123-456-7890")
        assert us_pattern.match("(123) 456-7890")
        assert us_pattern.match("+1 (123) 456-7890")
        assert not us_pattern.match("12345")

        # International phone
        intl_pattern = ValidationPatterns.INTERNATIONAL_PHONE
        assert intl_pattern.match("+44 20 7123 4567")
        assert intl_pattern.match("0033 1 42 86 82 82")

    def test_username_patterns(self):
        """Test username validation patterns."""
        # Alphanumeric
        pattern1 = ValidationPatterns.USERNAME_ALPHANUMERIC
        assert pattern1.match("user123")
        assert pattern1.match("test_user")
        assert not pattern1.match("us")  # Too short
        assert not pattern1.match("user-name")  # No dash allowed

        # With dash
        pattern2 = ValidationPatterns.USERNAME_WITH_DASH
        assert pattern2.match("user-name")
        assert pattern2.match("test_user_123")

        # Strict (must start with lowercase)
        pattern3 = ValidationPatterns.USERNAME_STRICT
        assert pattern3.match("user123")
        assert not pattern3.match("User123")  # Must start with lowercase
        assert not pattern3.match("123user")  # Must start with letter

    def test_identifier_patterns(self):
        """Test identifier validation patterns."""
        # Slug
        slug_pattern = ValidationPatterns.SLUG
        assert slug_pattern.match("my-awesome-post")
        assert slug_pattern.match("post123")
        assert not slug_pattern.match("My-Post")  # No uppercase
        assert not slug_pattern.match("post_name")  # No underscore

        # UUID
        uuid_pattern = ValidationPatterns.UUID
        assert uuid_pattern.match("123e4567-e89b-12d3-a456-426614174000")
        assert not uuid_pattern.match("not-a-uuid")

        # Alphanumeric ID
        id_pattern = ValidationPatterns.ALPHANUMERIC_ID
        assert id_pattern.match("ABC123")
        assert id_pattern.match("123456")
        assert not id_pattern.match("abc123")  # Must be uppercase

    def test_code_patterns(self):
        """Test code validation patterns."""
        # Hex color
        hex_pattern = ValidationPatterns.HEX_COLOR
        assert hex_pattern.match("#FF0000")
        assert hex_pattern.match("FF0000")
        assert hex_pattern.match("#F00")
        assert not hex_pattern.match("#GG0000")  # Invalid hex

        # ISO date
        date_pattern = ValidationPatterns.ISO_DATE
        assert date_pattern.match("2024-01-01")
        assert not date_pattern.match("01-01-2024")

        # ISO datetime
        datetime_pattern = ValidationPatterns.ISO_DATETIME
        assert datetime_pattern.match("2024-01-01T12:00:00")
        assert datetime_pattern.match("2024-01-01T12:00:00.123Z")
        assert datetime_pattern.match("2024-01-01T12:00:00+00:00")

    def test_geographic_patterns(self):
        """Test geographic validation patterns."""
        # Latitude
        lat_pattern = ValidationPatterns.LATITUDE
        assert lat_pattern.match("45.123")
        assert lat_pattern.match("-90")
        assert lat_pattern.match("90.0")
        assert not lat_pattern.match("91")  # Out of range

        # Longitude
        lon_pattern = ValidationPatterns.LONGITUDE
        assert lon_pattern.match("123.456")
        assert lon_pattern.match("-180")
        assert lon_pattern.match("180.0")
        assert not lon_pattern.match("181")  # Out of range

        # US ZIP
        zip_us_pattern = ValidationPatterns.ZIP_US
        assert zip_us_pattern.match("12345")
        assert zip_us_pattern.match("12345-6789")
        assert not zip_us_pattern.match("1234")  # Too short

        # Canadian postal code
        zip_ca_pattern = ValidationPatterns.ZIP_CA
        assert zip_ca_pattern.match("K1A 0B1")
        assert zip_ca_pattern.match("K1A0B1")

    def test_financial_patterns(self):
        """Test financial validation patterns."""
        # Credit card
        cc_pattern = ValidationPatterns.CREDIT_CARD
        assert cc_pattern.match("4111111111111111")  # 16 digits
        assert cc_pattern.match("5500000000000004")  # 16 digits
        assert not cc_pattern.match("123")  # Too short

        # IBAN
        iban_pattern = ValidationPatterns.IBAN
        assert iban_pattern.match("GB82WEST12345698765432")
        assert iban_pattern.match("DE89370400440532013000")

        # Bitcoin address
        btc_pattern = ValidationPatterns.BITCOIN_ADDRESS
        assert btc_pattern.match("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa")
        assert btc_pattern.match("bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq")

    def test_social_media_patterns(self):
        """Test social media validation patterns."""
        # Twitter handle
        twitter_pattern = ValidationPatterns.TWITTER_HANDLE
        assert twitter_pattern.match("@username")
        assert twitter_pattern.match("@user_123")
        assert not twitter_pattern.match("username")  # Missing @
        assert not twitter_pattern.match("@toolongusernamehere")  # Too long

        # Instagram handle
        instagram_pattern = ValidationPatterns.INSTAGRAM_HANDLE
        assert instagram_pattern.match("@username")
        assert instagram_pattern.match("@user.name")
        assert instagram_pattern.match("@user_name")

        # Hashtag
        hashtag_pattern = ValidationPatterns.HASHTAG
        assert hashtag_pattern.match("#python")
        assert hashtag_pattern.match("#Python3")
        assert hashtag_pattern.match("#test_tag")
        assert not hashtag_pattern.match("hashtag")  # Missing #

    def test_validator_functions(self):
        """Test validator helper functions."""
        # Pattern validator
        email_validator = ValidationPatterns.validate_pattern(
            ValidationPatterns.EMAIL, "Invalid email format"
        )

        assert email_validator("test@example.com") == "test@example.com"

        with pytest.raises(ValueError, match="Invalid email format"):
            email_validator("not-an-email")

        with pytest.raises(ValueError, match="Expected string"):
            email_validator(123)

        # Whitespace normalizer
        normalizer = ValidationPatterns.normalize_whitespace()
        assert normalizer("  hello   world  ") == "hello world"
        assert normalizer("hello\nworld") == "hello world"

        # Strip whitespace
        stripper = ValidationPatterns.strip_whitespace()
        assert stripper("  hello  ") == "hello"

        # Case converters
        lower = ValidationPatterns.lowercase()
        assert lower("HELLO") == "hello"

        upper = ValidationPatterns.uppercase()
        assert upper("hello") == "HELLO"

        title = ValidationPatterns.titlecase()
        assert title("hello world") == "Hello World"


class TestCreatePatternTemplate:
    """Test the create_pattern_template function."""

    def test_basic_pattern_template(self):
        """Test creating a basic pattern template."""
        template = create_pattern_template(
            r"^\d{3}-\d{3}-\d{4}$", description="Phone number"
        )

        field = template.create_field("phone")
        Model = create_model("Model", fields={"phone": field})

        # Valid
        instance = Model(phone="123-456-7890")
        assert instance.phone == "123-456-7890"

        # Invalid
        with pytest.raises(ValidationError):
            Model(phone="1234567890")

    def test_pattern_with_compiled_regex(self):
        """Test using a compiled regex pattern."""
        pattern = re.compile(r"^[A-Z]{2}\d{4}$")
        template = create_pattern_template(
            pattern,
            description="Product code",
            error_message="Product code must be 2 uppercase letters followed by 4 digits",
        )

        field = template.create_field("code")
        Model = create_model("Product", fields={"code": field})

        # Valid
        product = Model(code="AB1234")
        assert product.code == "AB1234"

        # Invalid
        with pytest.raises(ValidationError):
            Model(code="ab1234")  # Lowercase

    def test_pattern_with_custom_error(self):
        """Test custom error message."""
        template = create_pattern_template(
            ValidationPatterns.EMAIL, error_message="Please enter a valid email address"
        )

        field = template.create_field("email")
        Model = create_model("User", fields={"email": field})

        with pytest.raises(ValidationError) as exc_info:
            Model(email="invalid")

        # Check that our custom error is in the validation errors
        errors = exc_info.value.errors()
        assert any("string_pattern_mismatch" in str(error) for error in errors)

    def test_pattern_with_kwargs(self):
        """Test passing additional kwargs to FieldTemplate."""
        template = create_pattern_template(
            r"^[a-z]+$", description="Lowercase word", default="hello", title="Word"
        )

        assert template.default == "hello"
        assert template.title == "Word"


class TestCreateRangeTemplate:
    """Test the create_range_template function."""

    def test_integer_range(self):
        """Test integer range constraints."""
        # Age field (0-150)
        age_template = create_range_template(
            int, ge=0, le=150, description="Person's age"
        )

        field = age_template.create_field("age")
        Model = create_model("Person", fields={"age": field})

        # Valid
        person = Model(age=25)
        assert person.age == 25

        # Invalid - too low
        with pytest.raises(ValidationError):
            Model(age=-1)

        # Invalid - too high
        with pytest.raises(ValidationError):
            Model(age=151)

    def test_float_range(self):
        """Test float range constraints."""
        # Percentage (0-100)
        percentage_template = create_range_template(
            float, ge=0, le=100, description="Percentage", default=0.0
        )

        field = percentage_template.create_field("percentage")
        Model = create_model("Progress", fields={"percentage": field})

        # Valid
        progress = Model(percentage=50.5)
        assert progress.percentage == 50.5

        # Default
        progress2 = Model()
        assert progress2.percentage == 0.0

        # Invalid
        with pytest.raises(ValidationError):
            Model(percentage=101.0)

    def test_exclusive_bounds(self):
        """Test exclusive bounds (gt/lt)."""
        # Temperature above absolute zero
        temp_template = create_range_template(
            float, gt=-273.15, description="Temperature in Celsius"
        )

        field = temp_template.create_field("temperature")
        Model = create_model("Measurement", fields={"temperature": field})

        # Valid
        m1 = Model(temperature=20.0)
        assert m1.temperature == 20.0

        # Invalid - exactly at absolute zero
        with pytest.raises(ValidationError):
            Model(temperature=-273.15)

    def test_invalid_base_type(self):
        """Test error handling for invalid base type."""
        with pytest.raises(ValueError, match="base_type must be int or float"):
            create_range_template(str, ge=0)

    def test_mixed_constraints(self):
        """Test mixing different constraint types."""
        # Score between 0 (exclusive) and 100 (inclusive)
        score_template = create_range_template(float, gt=0, le=100, description="Score")

        field = score_template.create_field("score")
        Model = create_model("Result", fields={"score": field})

        # Valid
        result = Model(score=50.0)
        assert result.score == 50.0

        # Valid - at upper bound
        result2 = Model(score=100.0)
        assert result2.score == 100.0

        # Invalid - at lower bound
        with pytest.raises(ValidationError):
            Model(score=0.0)

    def test_range_with_kwargs(self):
        """Test passing additional kwargs."""
        template = create_range_template(
            int, ge=1, le=10, description="Rating", default=5, title="Star Rating"
        )

        assert template.default == 5
        assert template.title == "Star Rating"


class TestValidationTemplates:
    """Test pre-built validation templates."""

    def test_prebuilt_templates(self):
        """Test that pre-built templates exist and work."""
        from pydapter.fields.validation_patterns import VALIDATION_TEMPLATES

        # Check that expected templates exist
        expected = [
            "email",
            "url",
            "https_url",
            "us_phone",
            "username",
            "slug",
            "hex_color",
            "zip_us",
        ]

        for name in expected:
            assert name in VALIDATION_TEMPLATES
            assert isinstance(VALIDATION_TEMPLATES[name], FieldTemplate)

    def test_using_prebuilt_template(self):
        """Test using a pre-built template in a model."""
        from pydapter.fields.validation_patterns import VALIDATION_TEMPLATES

        # Create a model using pre-built templates
        email_field = VALIDATION_TEMPLATES["email"].create_field("email")
        slug_field = VALIDATION_TEMPLATES["slug"].create_field("slug")

        Model = create_model(
            "Article", fields={"email": email_field, "slug": slug_field}
        )

        # Valid
        article = Model(email="author@example.com", slug="my-awesome-article")
        assert article.email == "author@example.com"
        assert article.slug == "my-awesome-article"

        # Invalid email
        with pytest.raises(ValidationError):
            Model(email="not-an-email", slug="valid-slug")
