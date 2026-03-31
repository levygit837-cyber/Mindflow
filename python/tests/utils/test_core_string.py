"""Test cases for core string utilities."""

from mindflow_backend.utils.core import (
    camel_case,
    count_words,
    estimate_token_count,
    generate_random_string,
    is_blank,
    is_empty,
    levenshtein_distance,
    mask_string,
    slugify,
    snake_case,
    truncate,
)


class TestStringUtilities:
    """Test core string utility functions."""

    def test_slugify(self):
        """Test slugification."""
        assert slugify("Hello World!") == "hello-world"
        assert slugify("  Test   String  ") == "test-string"
        assert slugify("Café & Restaurant") == "cafe-restaurant"

    def test_truncate(self):
        """Test string truncation."""
        text = "This is a long string"
        result = truncate(text, 10)
        assert result == "This is..."
        assert len(result) <= 10

    def test_snake_case(self):
        """Test snake case conversion."""
        assert snake_case("HelloWorld") == "hello_world"
        assert snake_case("helloWorld") == "hello_world"
        assert snake_case("Hello-World") == "hello_world"

    def test_camel_case(self):
        """Test camel case conversion."""
        assert camel_case("hello_world") == "HelloWorld"
        assert camel_case("hello-world") == "HelloWorld"

    def test_is_empty(self):
        """Test empty string check."""
        assert is_empty("") is True
        assert is_empty("   ") is False
        assert is_empty("hello") is False

    def test_is_blank(self):
        """Test blank string check."""
        assert is_blank("") is True
        assert is_blank("   ") is True
        assert is_blank("\t\n") is True
        assert is_blank("hello") is False

    def test_count_words(self):
        """Test word counting."""
        assert count_words("Hello world") == 2
        assert count_words("  Multiple   spaces  ") == 2
        assert count_words("") == 0

    def test_mask_string(self):
        """Test string masking."""
        assert mask_string("1234567890", 4) == "1234******"
        assert mask_string("hello@world.com", 2) == "he************"

    def test_generate_random_string(self):
        """Test random string generation."""
        result = generate_random_string(10)
        assert len(result) == 10
        assert result.isalnum()

    def test_levenshtein_distance(self):
        """Test Levenshtein distance calculation."""
        assert levenshtein_distance("kitten", "sitting") == 3
        assert levenshtein_distance("hello", "hello") == 0
        assert levenshtein_distance("", "test") == 4

    def test_estimate_token_count(self):
        """Test token count estimation."""
        # ~4 chars per token
        assert estimate_token_count("") == 0
        assert estimate_token_count("hello") == 2  # 5 chars -> 2 tokens
        assert estimate_token_count("a" * 16) == 4  # 16 chars -> 4 tokens

    def test_slugify_unicode(self):
        """Test slugification with unicode characters."""
        assert slugify("naïve café") == "naive-cafe"
        assert slugify("测试") == "测试"

    def test_truncate_no_ellipsis(self):
        """Test truncation without ellipsis."""
        text = "Short"
        result = truncate(text, 10, ellipsis=False)
        assert result == "Short"

    def test_mask_string_short(self):
        """Test masking of short strings."""
        result = mask_string("hi", 2)
        assert result == "hi"  # No masking if string is too short
