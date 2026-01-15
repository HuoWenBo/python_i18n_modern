"""Conditional key evaluator for i18n translation selection.

This module evaluates conditional keys against provided values to determine
which translation variant should be used.
"""

from __future__ import annotations

import functools
import logging
import re
from typing import TYPE_CHECKING

from .ast_evaluator import ASTExpressionEvaluator
from .value_substitution import ValueSubstitutor

if TYPE_CHECKING:
    from .types import FormatParam

# Pattern to validate safe conditional expressions
_SAFE_EXPRESSION_PATTERN: re.Pattern[str] = re.compile(
    r"^(?:\[?(\d+|\w+)\]?)(?:(?:(?:\s?)(?:[\>\=\!\<\|\&]|and|or){1,3}(?:\s?)(?:\[?(\d+|\w+)\]?))*)?$"
)


class ConditionalKeyEvaluator:
    """Evaluator for conditional translation keys."""

    __slots__ = ()

    # Python reserved words that should not appear in expressions
    _RESERVED_WORDS: frozenset[str] = frozenset(
        [
            "break",
            "case",
            "catch",
            "class",
            "const",
            "continue",
            "debugger",
            "delete",
            "do",
            "enum",
            "export",
            "extends",
            "false",
            "finally",
            "for",
            "function",
            "if",
            "import",
            "isinstance",
            "interface",
            "let",
            "new",
            "null",
            "package",
            "private",
            "protected",
            "public",
            "return",
            "static",
            "super",
            "switch",
            "this",
            "throw",
            "true",
            "try",
            "typeof",
            "var",
            "void",
            "while",
            "with",
            "alert",
            "console",
            "script",
            "eval",
            "exec",
            "__import__",
            "open",
            "compile",
        ]
    )

    @classmethod
    def evaluate(cls, key: str, values: FormatParam | None = None) -> bool:
        """Evaluate a conditional key against provided values.

        Args:
            key: Conditional key expression to evaluate
            values: Values to substitute and check against

        Returns:
            Boolean result of evaluation

        Examples:
            >>> ConditionalKeyEvaluator.evaluate("[count] > 1", {"count": 5})
            True
            >>> ConditionalKeyEvaluator.evaluate("[name] == 'John'", {"name": "Jane"})
            False
        """
        if not cls.is_safe_expression(key):
            logging.warning("Unsafe or invalid conditional key: '%s'", key)
            return False

        # Normalize logical operators
        normalized_key = cls._normalize_operators(key)

        # Check if expression contains logical/comparison operators
        has_logic = cls._has_logical_operators(normalized_key)

        # Substitute placeholder values
        substituted = ValueSubstitutor.substitute(normalized_key, values)

        if has_logic:
            # Evaluate as boolean expression using AST
            return ASTExpressionEvaluator.evaluate(substituted)

        # Simple value check (key exists in values)
        if not values:
            return False

        search_value = substituted.strip()
        return search_value in values or search_value in {str(v) for v in values.values()}

    @classmethod
    @functools.lru_cache(maxsize=512)
    def is_safe_expression(cls, expression: str) -> bool:
        """Validate that expression is safe to evaluate.

        Args:
            expression: Expression to validate

        Returns:
            True if expression is safe
        """
        # Normalize for validation
        normalized = expression.replace("&&", "and").replace("||", "or")

        # Check pattern match
        if not _SAFE_EXPRESSION_PATTERN.match(normalized):
            return False

        # Ensure no reserved words present
        return all(word not in normalized for word in cls._RESERVED_WORDS)

    @staticmethod
    def _normalize_operators(expression: str) -> str:
        """Normalize logical operators to Python syntax.

        Args:
            expression: Expression with potentially non-Python operators

        Returns:
            Expression with normalized operators
        """
        return expression.replace("&&", " and ").replace("||", " or ")

    @staticmethod
    def _has_logical_operators(expression: str) -> bool:
        """Check if expression contains logical or comparison operators.

        Args:
            expression: Expression to check

        Returns:
            True if expression contains operators
        """
        logical_tokens = ("==", "!=", ">=", "<=", ">", "<", " and ", " or ")
        return any(token in expression for token in logical_tokens)
