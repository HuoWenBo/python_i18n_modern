"""
Module to get translation from locales.

Author: Uriel Curiel <urielcurrel@outlook.com>
"""
import json
import logging
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import cast

from i18n_modern.helpers import eval_key, format_value, get_deep_value, merge_deep
from i18n_modern.types import FormatParam, LocaleDict, Locales, LocaleValue, CacheDict

try:
    import yaml
except ImportError:
    yaml = None

try:
    import tomli
except ImportError:
    tomli = None


class I18nModern:
    """
    Gets the translation from a locales variable.

    Args:
        default_locale: The default locale
        locales: The locales variable (dict) or path to locale file
    """

    __slots__ = (
        "_locales",
        "_default_locale",
        "_previous_translations",
        "_cache_max_size",
    )

    def __init__(
            self,
            default_locale: str,
            locales: LocaleDict | str | Path | None = None,
            *,
            cache_max_size: int = 2048
    ):
        self._locales: Locales = {}
        self._default_locale: str = default_locale
        # Increased cache size for better performance (was unbounded)
        self._previous_translations: CacheDict = {}
        self._cache_max_size: int = cache_max_size  # Limit cache size to prevent unbounded growth

        if cache_max_size <= 0:
            raise ValueError("cache_max_size must be a positive integer")

        if isinstance(locales, str | Path):
            self.load_from_file(Path(locales), default_locale)
        elif isinstance(locales, dict):
            self.load_from_value(locales, default_locale)

    @property
    def default_locale(self) -> str:
        """Get the default locale."""
        return self._default_locale

    @default_locale.setter
    def default_locale(self, value: str):
        """Set the default locale."""
        self._default_locale = value

    def load_from_file(self, file_path: str | Path, locale_identify: str):
        """
        Load locales from a file (JSON, YAML, or TOML).

        Args:
            file_path: Path to the locale file
            locale_identify: Locale identifier
        """
        path: Path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"Locale file not found: {file_path}")

        suffix: str = path.suffix.lower()

        if suffix == ".json":
            # Try memory-mapped style reading for very large files
            try:
                import mmap

                with open(path, "rb") as f:
                    with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                        data = cast(LocaleDict, json.loads(mm.read().decode("utf-8")))
            except Exception:
                with open(path, "r", encoding="utf-8") as f:
                    data = cast(LocaleDict, json.load(f))
        elif suffix in [".yaml", ".yml"]:
            if yaml is None:
                raise ImportError("PyYAML is required for YAML support. Install with: pip install pyyaml")
            with open(path, "r", encoding="utf-8") as f:
                data = cast(LocaleDict, yaml.safe_load(f))  # type: ignore
        elif suffix == ".toml":
            if tomli is None:
                raise ImportError("tomli is required for TOML support. Install with: pip install tomli")
            with open(path, "rb") as f:
                data = cast(LocaleDict, tomli.load(f))  # type: ignore
        else:
            raise ValueError(f"Unsupported file format: {suffix}. Supported formats: .json, .yaml, .yml, .toml")

        self._update_locales(locale_identify, data)

    def _update_locales(self, locale_identify: str, data: LocaleDict):
        self._locales[locale_identify] = merge_deep(
            self._locales.get(
                locale_identify,
                self._locales.get(self._default_locale)
            ),
            data
        )
        # Clear the corresponding translation cache to apply the new translated text
        for key, locale, values_tuple in list(self._previous_translations.keys()):
            if locale == locale_identify:
                del self._previous_translations[(key, locale, values_tuple)]

    def _load_path(self, path: Path) -> LocaleDict:
        """Load a single locale file from a path with mmap optimization for JSON."""
        suffix = path.suffix.lower()
        if suffix == ".json":
            try:
                import mmap

                with open(path, "rb") as f:
                    with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                        return cast(LocaleDict, json.loads(mm.read().decode("utf-8")))
            except Exception:
                with open(path, "r", encoding="utf-8") as f:
                    return cast(LocaleDict, json.load(f))
        if suffix in [".yaml", ".yml"]:
            if yaml is None:
                raise ImportError("PyYAML is required for YAML support. Install with: pip install pyyaml")
            with open(path, "r", encoding="utf-8") as f:
                return cast(LocaleDict, yaml.safe_load(f))  # type: ignore
        if suffix == ".toml":
            if tomli is None:
                raise ImportError("tomli is required for TOML support. Install with: pip install tomli")
            with open(path, "rb") as f:
                return cast(LocaleDict, tomli.load(f))  # type: ignore
        raise ValueError(f"Unsupported file format: {suffix}. Supported formats: .json, .yaml, .yml, .toml")

    def _task_load_locale(self, file_path: str | Path, locale: str) -> tuple[str, LocaleDict]:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Locale file not found: {file_path}")
        return locale, self._load_path(path)

    def load_many(self, files: Iterable[tuple[str, str]], max_workers: int | None = None) -> None:
        """Load multiple locale files concurrently.

        Args:
            files: Iterable of tuples (file_path, locale_identify)
            max_workers: Optional maximum number of worker threads
        """

        # Load in parallel and merge safely once complete
        results: list[tuple[str, LocaleDict]] = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(self._task_load_locale, fp, loc) for fp, loc in files]
            for fut in as_completed(futures):
                results.append(fut.result())

        # Merge results into _locales
        for locale, data in results:
            self._update_locales(locale, data)
            # self._locales[locale] = merge_deep(self._locales.get(self._default_locale), data)

    def load_from_value(self, locales: LocaleDict, locale_identify: str):
        """
        Load locales from a dictionary value.

        Args:
            locales: The locales dictionary
            locale_identify: Locale identifier
        """
        # self._locales[locale_identify] = merge_deep(self._locales.get(self._default_locale), locales)

        self._update_locales(locale_identify, locales)

    def get(self, key: str, locale: str | None = None, values: FormatParam | None = None) -> str:
        """
        Get a translation with memoization from a key and format params.

        Args:
            key: Translation key (supports dot notation)
            locale: Optional locale override
            values: Optional values for placeholder replacement

        Returns:
            Translated string
        """
        try:
            locale = locale or self._default_locale
            # values_tuple = tuple(sorted(values.items())) if values else None
            # values_tuple = frozenset(values.items()) if values else None
            values_tuple = tuple(values.items()) if values else None
            cache_key = (key, locale, values_tuple)

            if cache_key in self._previous_translations:
                return self._previous_translations[cache_key]

            if locale not in self._locales:
                raise KeyError(f"Locale '{locale}' not found in locales")

            translation: LocaleValue | None = get_deep_value(self._locales[locale], key)

            if translation is None:
                raise KeyError(f"Translation key '{key}' not found in locale '{locale}'")

            result = self._get_translation(translation, values)

            # Bounded cache - prevent unbounded growth
            if len(self._previous_translations) >= self._cache_max_size:
                # Simple FIFO eviction: remove the oldest items (first half)
                limit = self._cache_max_size // 4 if self._cache_max_size > 4 else 1
                keys_to_remove = list(self._previous_translations.keys())[: limit]
                for k in keys_to_remove:
                    del self._previous_translations[k]

            self._previous_translations[cache_key] = result
            return result

        except Exception as error:
            logging.warning("Error: the key '%s' is not defined in locales - %s", key, error)
            return key

    def _get_translation(
            self, translation: LocaleValue, values: FormatParam | None = None, default_translation: str | None = None
    ) -> str:
        """
        Get a translation from object and format it.

        Args:
            translation: Translation value (string or dict)
            values: Optional values for placeholder replacement
            default_translation: Optional default translation

        Returns:
            Formatted translation string
        """
        if isinstance(translation, dict) and "default" in translation:
            default_translation = str(translation["default"])

        if not isinstance(translation, str):
            # Find matching key based on condition
            for key in translation.keys():  # type: ignore
                if eval_key(key, values):  # type: ignore
                    return self._get_translation(
                        translation[key],
                        values,
                        default_translation,  # type: ignore
                    )

            # Return default if no key matches
            if default_translation:
                # return self._get_translation(default_translation, values, default_translation)  # type: ignore
                return format_value(default_translation, values)  # type: ignore
            return ""

        return format_value(translation, values)


class _LazyLoader:
    def __init__(
            self,
            i18n: I18nModern,
            key: str,
            default_locale: str | None = None,
    ):
        self.i18n = i18n
        self.key = key
        self.default_locale = default_locale

    def __get__(self, instance, owner) -> str:
        return self.i18n.get(self.key, self.default_locale)


class LazyLoader:
    def __init__(self, i18n: I18nModern):
        self.i18n = i18n

    def __call__(self, key: str, locale: str) -> _LazyLoader:
        return _LazyLoader(self.i18n, key, locale)
