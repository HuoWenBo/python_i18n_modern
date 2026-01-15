# pyright: basic
"""
Comprehensive benchmark comparing i18n_modern with other i18n libraries.

Compares:
- i18n_modern (our library)
- python-i18n
- pyi18n-v2
- i18nice
- toml-i18n
"""

import json
import time
from pathlib import Path
from typing import Callable

import i18n as py_i18n
import pyi18n as pyi18n
from pyi18n.loaders import PyI18nJsonLoader

try:
    import i18n as i18nice_lib
except ImportError:
    i18nice_lib = None  # type: ignore[assignment]

try:
    from toml_i18n import TomlI18n
    from toml_i18n import i18n as toml_i18n_translate
except ImportError:
    TomlI18n = None  # type: ignore[assignment]
    toml_i18n_translate = None  # type: ignore[assignment]

from i18n_modern import I18nModern
from i18n_modern._accel import get_deep_value_fast  # just to check availability


class BenchmarkRunner:
    """Runs performance benchmarks on different i18n libraries."""

    def __init__(self):
        """Initialize the benchmark runner."""
        self.results = {}

    def measure_time(
        self, func: Callable, iterations: int = 10000, suppress_output: bool = False
    ) -> tuple[float, float]:
        """
        Measure execution time of a function.

        Args:
            func: Function to measure
            iterations: Number of iterations
            suppress_output: Whether to suppress stdout during execution

        Returns:
            Tuple of (total_time, time_per_iteration)
        """
        import io
        import sys

        start = time.perf_counter()
        # if suppress_output:
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            for _ in range(iterations):
                func()
        finally:
            # if suppress_output:
            sys.stdout = old_stdout
        end = time.perf_counter()
        total_time = end - start
        return total_time, total_time / iterations

    def setup_i18n_modern(self) -> I18nModern:
        """Setup i18n_modern with test data."""
        locales_path = Path(__file__).parent / "examples" / "locales" / "en.json"
        with open(locales_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        i18n_obj = I18nModern("en", data)
        return i18n_obj

    def setup_python_i18n(self) -> dict:
        """Setup python-i18n with test data."""
        locales_path = Path(__file__).parent / "examples" / "locales" / "en.json"
        py_i18n.set("locale", "en")
        py_i18n.set("filename_format", "{namespace}.{locale}.json")
        py_i18n.set("file_format", "json")
        # py_i18n.set("default_locale", "en")

        # Load from file
        locale_dir = Path(__file__).parent / "examples" / "locales"
        py_i18n.load_path.clear()  # type: ignore[attr-defined]  # pyright: ignore[reportAttributeAccessIssue]
        py_i18n.load_path.append(str(locale_dir))  # type: ignore[attr-defined]  # pyright: ignore[reportAttributeAccessIssue]

        # Load the file
        with open(locales_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return {"i18n": py_i18n, "data": data}

    def setup_pyi18n(self) -> dict:
        """Setup pyi18n-v2 with test data using JSON loader."""
        # pyi18n-v2 requires a locales directory and a loader
        locales_dir = Path(__file__).parent / "examples" / "locales"

        # Create JSON loader pointing to locales directory
        loader = PyI18nJsonLoader(str(locales_dir))

        # Create PyI18n instance with available locales
        pyi18n_obj = pyi18n.PyI18n(available_locales=("en",), loader=loader)

        return {"i18n": pyi18n_obj}

    def setup_i18nice(self) -> dict:  # pyright: ignore[name-defined]
        """Setup i18nice with test data."""
        if i18nice_lib is None:
            raise ImportError("i18nice is not installed")

        # i18nice is a global module, we need to configure it
        # Configure i18nice
        i18nice_lib.set("locale", "en")  # type: ignore[attr-defined]
        i18nice_lib.set("file_format", "json")  # type: ignore[attr-defined]
        i18nice_lib.set("filename_format", "{namespace}.{locale}.{format}")  # type: ignore[attr-defined]
        i18nice_lib.set("enable_memoization", True)  # type: ignore[attr-defined]

        # Load path with translations
        locale_dir = Path(__file__).parent / "examples" / "locales"
        i18nice_lib.load_path.clear()  # pyright: ignore[reportOptionalMemberAccess]
        i18nice_lib.load_path.append(str(locale_dir))  # pyright: ignore[reportOptionalMemberAccess]

        # Attempt to load everything, but continue if method doesn't exist
        try:
            i18nice_lib.load_everything()  # type: ignore[attr-defined]
        except (AttributeError, TypeError):
            # If load_everything is not available, translations will be lazy-loaded on first access
            pass

        return {"i18n": i18nice_lib}

    def setup_toml_i18n(self) -> dict:
        """Setup toml-i18n with test data."""
        if TomlI18n is None or toml_i18n_translate is None:
            raise ImportError("toml-i18n is not installed")

        locales_dir = Path(__file__).parent / "examples" / "locales"

        # Load en.json
        with open(locales_dir / "en.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        # toml-i18n expects TOML files or needs to be initialized with data
        # We need to create TOML files with the proper structure
        # For now, let's initialize it with the directory and create temporary TOML files
        try:
            TomlI18n.initialize(locale="en", fallback_locale="en", directory=str(locales_dir))
        except Exception:
            # If initialization fails, it's likely because TOML files don't exist
            # We'll use a simpler approach - just return the function without initialization
            pass

        return {"i18n": toml_i18n_translate, "data": data}

    def benchmark_i18n_modern(self):
        """Benchmark i18n_modern library."""
        print("\n" + "=" * 70)
        print("BENCHMARKING: i18n_modern")
        print("=" * 70)

        # Acceleration status
        ok, _ = get_deep_value_fast({}, "x.y")
        print(f"Acceleration available: {'YES' if ok else 'NO'}")

        i18n_obj = self.setup_i18n_modern()

        # Test 1: Simple key access
        print("\n1. Simple Key Access (welcome)")
        total, per_iter = self.measure_time(lambda: i18n_obj.get("welcome"), iterations=10000)
        print(f"   Total: {total:.4f}s | Per iteration: {per_iter * 1e6:.2f}µs")
        self.results["i18n_modern_simple"] = {"total": total, "per_iter": per_iter}

        # Test 2: Nested key access
        print("\n2. Nested Key Access (messages.success)")
        total, per_iter = self.measure_time(lambda: i18n_obj.get("messages.success"), iterations=10000)
        print(f"   Total: {total:.4f}s | Per iteration: {per_iter * 1e6:.2f}µs")
        self.results["i18n_modern_nested"] = {"total": total, "per_iter": per_iter}

        # Test 3: With parameter substitution
        print("\n3. Parameter Substitution (greeting)")
        total, per_iter = self.measure_time(
            lambda: i18n_obj.get("greeting", values={"name": "Alice"}),
            iterations=10000,
        )
        print(f"   Total: {total:.4f}s | Per iteration: {per_iter * 1e6:.2f}µs")
        self.results["i18n_modern_params"] = {"total": total, "per_iter": per_iter}

        # Test 4: With conditional logic
        print("\n4. Conditional Logic (age_group with adult)")
        total, per_iter = self.measure_time(
            lambda: i18n_obj.get("age_group", values={"age": 25}),
            iterations=5000,
        )
        print(f"   Total: {total:.4f}s | Per iteration: {per_iter * 1e6:.2f}µs")
        self.results["i18n_modern_conditional"] = {"total": total, "per_iter": per_iter}

        # Test 5: Cache effectiveness (repeated calls)
        print("\n5. Cache Effectiveness (100 repeated calls)")

        def cache_test():
            return i18n_obj.get("greeting", values={"name": "Alice"})

        total, per_iter = self.measure_time(cache_test, iterations=10000)
        print(f"   Total: {total:.4f}s | Per iteration: {per_iter * 1e6:.2f}µs")
        self.results["i18n_modern_cache"] = {"total": total, "per_iter": per_iter}

        # Test 6: Parallel loading (load_many) using the same file n times
        print("\n6. Parallel Load (load_many) of 4 files (same JSON)")
        locales_path = Path(__file__).parent / "examples" / "locales" / "en.json"
        files = [(str(locales_path), f"en{i}") for i in range(4)]

        def do_load() -> None:
            I18nModern("en").load_many(files)

        total, per_iter = self.measure_time(do_load, iterations=1)
        print(f"   Total: {total:.4f}s")
        self.results["i18n_modern_parallel_load"] = {"total": total, "per_iter": per_iter}

    def benchmark_python_i18n(self):
        """Benchmark python-i18n library."""
        print("\n" + "=" * 70)
        print("BENCHMARKING: python-i18n")
        print("=" * 70)

        try:
            setup = self.setup_python_i18n()
            i18n_lib = setup["i18n"]

            # Test 1: Simple key access
            print("\n1. Simple Key Access (welcome)")
            try:
                total, per_iter = self.measure_time(lambda: i18n_lib.t("welcome"), iterations=10000)
                print(f"   Total: {total:.4f}s | Per iteration: {per_iter * 1e6:.2f}µs")
                self.results["python_i18n_simple"] = {
                    "total": total,
                    "per_iter": per_iter,
                }
            except Exception as e:
                print(f"   Error: {e}")
                self.results["python_i18n_simple"] = {"error": str(e)}

            # Test 2: Nested key access
            print("\n2. Nested Key Access (messages.success)")
            try:
                total, per_iter = self.measure_time(lambda: i18n_lib.t("messages.success"), iterations=10000)
                print(f"   Total: {total:.4f}s | Per iteration: {per_iter * 1e6:.2f}µs")
                self.results["python_i18n_nested"] = {
                    "total": total,
                    "per_iter": per_iter,
                }
            except Exception as e:
                print(f"   Error: {e}")
                self.results["python_i18n_nested"] = {"error": str(e)}

            # Test 3: With parameter substitution
            print("\n3. Parameter Substitution (greeting)")
            try:
                total, per_iter = self.measure_time(lambda: i18n_lib.t("greeting", name="Alice"), iterations=10000)
                print(f"   Total: {total:.4f}s | Per iteration: {per_iter * 1e6:.2f}µs")
                self.results["python_i18n_params"] = {
                    "total": total,
                    "per_iter": per_iter,
                }
            except Exception as e:
                print(f"   Error: {e}")
                self.results["python_i18n_params"] = {"error": str(e)}

        except Exception as e:
            print(f"\nError setting up python-i18n: {e}")

    def benchmark_pyi18n(self):
        """Benchmark pyi18n-v2 library."""
        print("\n" + "=" * 70)
        print("BENCHMARKING: pyi18n-v2")
        print("=" * 70)

        try:
            setup = self.setup_pyi18n()
            pyi18n_obj = setup["i18n"]

            # Test 1: Simple key access
            print("\n1. Simple Key Access (welcome)")
            try:
                total, per_iter = self.measure_time(
                    lambda: pyi18n_obj.gettext("en", "welcome"),
                    iterations=10000,
                )
                print(f"   Total: {total:.4f}s | Per iteration: {per_iter * 1e6:.2f}µs")
                self.results["pyi18n_simple"] = {"total": total, "per_iter": per_iter}
            except Exception as e:
                print(f"   Error: {e}")
                self.results["pyi18n_simple"] = {"error": str(e)}

            # Test 2: Nested key access
            print("\n2. Nested Key Access (messages.success)")
            try:
                total, per_iter = self.measure_time(
                    lambda: pyi18n_obj.gettext("en", "messages.success"),
                    iterations=10000,
                )
                print(f"   Total: {total:.4f}s | Per iteration: {per_iter * 1e6:.2f}µs")
                self.results["pyi18n_nested"] = {"total": total, "per_iter": per_iter}
            except Exception as e:
                print(f"   Error: {e}")
                self.results["pyi18n_nested"] = {"error": str(e)}

            # Test 3: With parameter substitution
            print("\n3. Parameter Substitution (greeting)")
            try:
                total, per_iter = self.measure_time(
                    lambda: pyi18n_obj.gettext("en", "greeting", name="Alice"),
                    iterations=10000,
                )
                print(f"   Total: {total:.4f}s | Per iteration: {per_iter * 1e6:.2f}µs")
                self.results["pyi18n_params"] = {"total": total, "per_iter": per_iter}
            except Exception as e:
                print(f"   Error: {e}")
                self.results["pyi18n_params"] = {"error": str(e)}

        except Exception as e:
            print(f"\nError setting up pyi18n-v2: {e}")

    def benchmark_i18nice(self):
        """Benchmark i18nice library."""
        print("\n" + "=" * 70)
        print("BENCHMARKING: i18nice")
        print("=" * 70)

        try:
            setup = self.setup_i18nice()
            i18n_obj = setup["i18n"]

            # Test 1: Simple key access
            print("\n1. Simple Key Access (translations.welcome)")
            try:
                total, per_iter = self.measure_time(lambda: i18n_obj.t("translations.welcome"), iterations=10000)
                print(f"   Total: {total:.4f}s | Per iteration: {per_iter * 1e6:.2f}µs")
                self.results["i18nice_simple"] = {"total": total, "per_iter": per_iter}
            except Exception as e:
                print(f"   Error: {e}")
                self.results["i18nice_simple"] = {"error": str(e)}

            # Test 2: Nested key access
            print("\n2. Nested Key Access (translations.messages.success)")
            try:
                total, per_iter = self.measure_time(
                    lambda: i18n_obj.t("translations.messages.success"), iterations=10000
                )
                print(f"   Total: {total:.4f}s | Per iteration: {per_iter * 1e6:.2f}µs")
                self.results["i18nice_nested"] = {"total": total, "per_iter": per_iter}
            except Exception as e:
                print(f"   Error: {e}")
                self.results["i18nice_nested"] = {"error": str(e)}

            # Test 3: With parameter substitution
            print("\n3. Parameter Substitution (translations.greeting)")
            try:
                total, per_iter = self.measure_time(
                    lambda: i18n_obj.t("translations.greeting", name="Alice"),
                    iterations=10000,
                )
                print(f"   Total: {total:.4f}s | Per iteration: {per_iter * 1e6:.2f}µs")
                self.results["i18nice_params"] = {"total": total, "per_iter": per_iter}
            except Exception as e:
                print(f"   Error: {e}")
                self.results["i18nice_params"] = {"error": str(e)}

        except Exception as e:
            print(f"\nError setting up i18nice: {e}")

    def benchmark_toml_i18n(self):
        """Benchmark toml-i18n library."""
        print("\n" + "=" * 70)
        print("BENCHMARKING: toml-i18n")
        print("=" * 70)

        try:
            setup = self.setup_toml_i18n()
            i18n_translate = setup["i18n"]

            # Test 1: Simple key access
            print("\n1. Simple Key Access (general.welcome)")
            try:
                total, per_iter = self.measure_time(
                    lambda: i18n_translate("general.welcome"),
                    iterations=10000,
                    suppress_output=True,
                )
                print(f"   Total: {total:.4f}s | Per iteration: {per_iter * 1e6:.2f}µs")
                self.results["toml_i18n_simple"] = {"total": total, "per_iter": per_iter}
            except Exception as e:
                print(f"   Error: {e}")
                self.results["toml_i18n_simple"] = {"error": str(e)}

            # Test 2: Nested key access
            print("\n2. Nested Key Access (general.messages.success)")
            try:
                total, per_iter = self.measure_time(
                    lambda: i18n_translate("general.messages.success"),
                    iterations=10000,
                    suppress_output=True,
                )
                print(f"   Total: {total:.4f}s | Per iteration: {per_iter * 1e6:.2f}µs")
                self.results["toml_i18n_nested"] = {"total": total, "per_iter": per_iter}
            except Exception as e:
                print(f"   Error: {e}")
                self.results["toml_i18n_nested"] = {"error": str(e)}

            # Test 3: With parameter substitution
            print("\n3. Parameter Substitution (general.greeting)")
            try:
                # Note: toml-i18n does not support parameter substitution in the same way
                # It just returns the template string as-is
                total, per_iter = self.measure_time(
                    lambda: i18n_translate("general.greeting"),
                    iterations=10000,
                    suppress_output=True,
                )
                print(f"   Total: {total:.4f}s | Per iteration: {per_iter * 1e6:.2f}µs")
                print("   Note: toml-i18n returns template without substitution")
                self.results["toml_i18n_params"] = {"total": total, "per_iter": per_iter}
            except Exception as e:
                print(f"   Error: {e}")
                self.results["toml_i18n_params"] = {"error": str(e)}

        except Exception as e:
            print(f"\nError setting up toml-i18n: {e}")

    def print_comparison_summary(self):
        """Print a summary comparison of all libraries."""
        print("\n" + "=" * 70)
        print("COMPARISON SUMMARY")
        print("=" * 70)

        # Extract times for each test
        tests = {
            "Simple Access": (
                "i18n_modern_simple",
                "python_i18n_simple",
                "pyi18n_simple",
                "i18nice_simple",
                "toml_i18n_simple",
            ),
            "Nested Access": (
                "i18n_modern_nested",
                "python_i18n_nested",
                "pyi18n_nested",
                "i18nice_nested",
                "toml_i18n_nested",
            ),
            "Parameter Substitution": (
                "i18n_modern_params",
                "python_i18n_params",
                "pyi18n_params",
                "i18nice_params",
                "toml_i18n_params",
            ),
        }

        def _print_rows(times: dict[str, float], fastest_time: float) -> None:
            for key, time_us in times.items():
                library = key.split("_")[0]
                if time_us == float("inf"):
                    print(f"  {library:15} - Error")
                else:
                    ratio = time_us / fastest_time if fastest_time > 0 else 1.0
                    bar = "█" * int(ratio * 20)
                    print(f"  {library:15} - {time_us:8.2f}µs {bar} ({ratio:.1f}x)")

        for test_name, keys in tests.items():
            print(f"\n{test_name}:")
            print("-" * 70)

            times: dict[str, float] = {}
            for key in keys:
                result = self.results.get(key)
                if not result:
                    continue
                times[key] = result.get("per_iter", float("inf")) * 1e6 if "error" not in result else float("inf")

            if not times:
                continue

            # Compute fastest without lambda capture
            fastest_time = float("inf")
            for k, v in times.items():
                if v < fastest_time:
                    fastest_time = v

            _print_rows(times, fastest_time)

    def run_all_benchmarks(self):
        """Run all benchmarks."""
        print("\n" + "█" * 70)
        print("█ I18N LIBRARIES PERFORMANCE BENCHMARK".ljust(70) + "█")
        print("█" * 70)

        self.benchmark_i18n_modern()
        self.benchmark_python_i18n()
        self.benchmark_pyi18n()
        self.benchmark_i18nice()
        self.benchmark_toml_i18n()
        self.print_comparison_summary()

        print("\n" + "█" * 70)
        print("█ BENCHMARK COMPLETE".ljust(69) + "█")
        print("█" * 70 + "\n")


if __name__ == "__main__":
    runner = BenchmarkRunner()
    runner.run_all_benchmarks()
