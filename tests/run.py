"""Run every test with nothing but the standard library: `python3 tests/run.py`.

pytest collects the same plain functions in CI; this exists so the suite (including the real-store
consistency checks, which only run where a store exists) is one command on a machine without pytest.
Exit code is the number of failures, so it gates a build.
"""
import importlib
import os
import sys
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def main() -> int:
    here = os.path.dirname(__file__)
    mods = sorted(f[:-3] for f in os.listdir(here) if f.startswith("test_") and f.endswith(".py"))
    total = failed = 0
    for name in mods:
        mod = importlib.import_module(f"tests.{name}")
        for fn_name in sorted(n for n in dir(mod) if n.startswith("test_")):
            fn = getattr(mod, fn_name)
            if not callable(fn):
                continue
            total += 1
            try:
                fn()
            except Exception:
                failed += 1
                print(f"FAIL {name}.{fn_name}")
                traceback.print_exc()
    print(f"{total - failed}/{total} passed")
    return failed


if __name__ == "__main__":
    sys.exit(main())
