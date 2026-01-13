"""Value substitution system for i18n placeholders.

This module handles replacement of placeholder values like [key] in translation strings.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .types import FormatParam

# Precompiled regex pattern for performance
_PLACEHOLDER_PATTERN: re.Pattern[str] = re.compile(r"\[(.*?)]")


class ValueSubstitutor:
    """Handles substitution of placeholder values in translation strings."""

    @staticmethod
    def substitute(template: str, values: FormatParam | None = None) -> str:
        """Replace [key] placeholders in template with actual values.

        Args:
            template: String template with placeholders like [key]
            values: Dictionary with replacement values

        Returns:
            String with placeholders replaced by values

        Examples:
            >>> ValueSubstitutor.substitute("Hello [name]!", {"name": "World"})
            'Hello World!'
            >>> ValueSubstitutor.substitute("Count: [n]", {"n": 42})
            'Count: 42'
        """
        if values is None or not values:
            return template

        def replacer(match: re.Match[str]) -> str:
            """Replace a single placeholder match."""
            key = match.group(1)
            if key in values:
                return str(values[key])
            # Return original placeholder if key not found
            return match.group(0)

        return _PLACEHOLDER_PATTERN.sub(replacer, template)

    @staticmethod
    def extract_placeholders(template: str) -> list[str]:
        """Extract all placeholder keys from a template string.

        Args:
            template: String template with placeholders

        Returns:
            List of placeholder keys found in template

        Examples:
            >>> ValueSubstitutor.extract_placeholders("Hello [name], you have [count] messages")
            ['name', 'count']
        """
        return _PLACEHOLDER_PATTERN.findall(template)

    @staticmethod
    def has_placeholders(template: str) -> bool:
        """Check if a template contains any placeholders.

        Args:
            template: String template to check

        Returns:
            True if template contains at least one placeholder

        Examples:
            >>> ValueSubstitutor.has_placeholders("Hello [name]")
            True
            >>> ValueSubstitutor.has_placeholders("Hello World")
            False
        """
        return _PLACEHOLDER_PATTERN.search(template) is not None
