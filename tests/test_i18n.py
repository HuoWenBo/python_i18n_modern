"""Tests for i18n_modern library."""

import pytest

from i18n_modern import I18nModern
from i18n_modern.types import LocaleDict


@pytest.fixture
def basic_locales():
    """Basic locale data for testing."""
    return {"welcome": "Welcome!", "greeting": "Hello, [name]!"}


@pytest.fixture
def nested_locales():
    """Nested locale data for testing."""
    return {"messages": {"success": "Success!", "error": "Error!"}}


@pytest.fixture
def conditional_locales():
    """Conditional locale data for testing."""
    return {"items": {"0": "No items", "1": "One item", "default": "[count] items"}}


@pytest.fixture
def comparison_locales():
    """Comparison condition locale data for testing."""
    return {"age_group": {"[age] < 18": "Minor", "[age] >= 18": "Adult", "default": "Unknown"}}


@pytest.fixture
def memoization_locales():
    """Locale data for memoization testing."""
    return {"greeting": "Hello, [name]!"}


class TestI18nModern:
    """Test class for I18nModern functionality."""

    def test_basic_translation(self, basic_locales: LocaleDict) -> None:
        """Test basic translation."""
        i18n = I18nModern("en", basic_locales)
        assert i18n.get("welcome") == "Welcome!"
        assert i18n.get("greeting", values={"name": "World"}) == "Hello, World!"

    def test_nested_keys(self, nested_locales: LocaleDict) -> None:
        """Test nested translation keys."""
        i18n = I18nModern("en", nested_locales)
        assert i18n.get("messages.success") == "Success!"
        assert i18n.get("messages.error") == "Error!"

    def test_conditional_translations(self, conditional_locales: LocaleDict) -> None:
        """Test conditional translations."""
        i18n = I18nModern("en", conditional_locales)
        assert i18n.get("items", values={"count": 0}) == "No items"
        assert i18n.get("items", values={"count": 1}) == "One item"
        assert i18n.get("items", values={"count": 5}) == "5 items"

    def test_comparison_conditions(self, comparison_locales: LocaleDict) -> None:
        """Test comparison conditions."""
        i18n = I18nModern("en", comparison_locales)
        assert i18n.get("age_group", values={"age": 15}) == "Minor"
        assert i18n.get("age_group", values={"age": 25}) == "Adult"

    def test_memoization(self, memoization_locales: LocaleDict) -> None:
        """Test that memoization works."""
        i18n = I18nModern("en", memoization_locales)

        # First call
        result1 = i18n.get("greeting", values={"name": "World"})
        # Second call should be cached
        result2 = i18n.get("greeting", values={"name": "World"})

        assert result1 == result2 == "Hello, World!"

    def test_load_from_value(self) -> None:
        """Test loading from value."""
        i18n = I18nModern("en")
        i18n.load_from_value({"welcome": "Welcome!"}, "en")

        assert i18n.get("welcome") == "Welcome!"

    def test_default_locale(self) -> None:
        """Test default locale property."""
        i18n = I18nModern("en")
        assert i18n.default_locale == "en"

        i18n.default_locale = "es"
        assert i18n.default_locale == "es"

    def test_missing_key_returns_key(self, basic_locales: LocaleDict) -> None:
        """Test that missing keys return the key itself."""
        i18n = I18nModern("en", basic_locales)
        assert i18n.get("missing.key") == "missing.key"

    def test_empty_values_dict(self, basic_locales: LocaleDict) -> None:
        """Test translation with empty values dict."""
        i18n = I18nModern("en", basic_locales)
        assert i18n.get("greeting", values={}) == "Hello, [name]!"

    @pytest.mark.parametrize(
        "count,expected",
        [
            (0, "No items"),
            (1, "One item"),
            (2, "2 items"),
            (10, "10 items"),
            (100, "100 items"),
        ],
    )
    def test_conditional_translations_parametrized(
        self, conditional_locales: LocaleDict, count: int, expected: str
    ) -> None:
        """Test conditional translations with multiple values."""
        i18n = I18nModern("en", conditional_locales)
        assert i18n.get("items", values={"count": count}) == expected

    @pytest.mark.parametrize(
        "age,expected",
        [
            (5, "Minor"),
            (17, "Minor"),
            (18, "Adult"),
            (25, "Adult"),
            (65, "Adult"),
        ],
    )
    def test_comparison_conditions_parametrized(self, comparison_locales: LocaleDict, age: int, expected: str) -> None:
        """Test comparison conditions with multiple values."""
        i18n = I18nModern("en", comparison_locales)
        assert i18n.get("age_group", values={"age": age}) == expected


# Additional functional tests outside the class for variety
def test_initialization_without_locales() -> None:
    """Test that I18nModern can be initialized without locales."""
    i18n = I18nModern("en")
    assert i18n.default_locale == "en"


def test_initialization_with_empty_dict() -> None:
    """Test that I18nModern can be initialized with empty dict."""
    i18n = I18nModern("en", {})
    assert i18n.default_locale == "en"


def test_get_nonexistent_key_with_values() -> None:
    """Test getting a nonexistent key with values."""
    i18n = I18nModern("en", {})
    result = i18n.get("nonexistent", values={"name": "test"})
    assert result == "nonexistent"


def test_multiple_locale_setting() -> None:
    """Test that default_locale can be changed multiple times."""
    i18n = I18nModern("en")

    # Change locale multiple times
    i18n.default_locale = "es"
    assert i18n.default_locale == "es"

    i18n.default_locale = "fr"
    assert i18n.default_locale == "fr"

    i18n.default_locale = "de"
    assert i18n.default_locale == "de"


def test_multiple_loads_merge_locale() -> None:
    """
    Testing that reloading won't let the default translation text
    override translations that have already been loaded
    """
    i18n = I18nModern("en", {
        "title": "Test",
        "message": "Hello World!"
    })

    assert i18n.get("title") == "Test"
    assert i18n.get("message") == "Hello World!"

    i18n.load_from_value({
        "message": "你好, 世界"
    }, "zh")

    assert i18n.get("title", "zh") == "Test"
    assert i18n.get("message", "zh") == "你好, 世界"

    i18n.load_from_value({
        "title": "测试",
    }, "zh")

    assert i18n.get("title", "zh") == "测试"
    assert i18n.get("message", "zh") == "你好, 世界"

