#!/usr/bin/env python3
import importlib.util
import sys
import traceback
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(path):
    spec = importlib.util.spec_from_file_location(path.stem, str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    failures = 0
    tests = 0
    for path in sorted((ROOT / "tests").glob("test_*.py")):
        module = load_module(path)
        for name in sorted(dir(module)):
            if not name.startswith("test_"):
                continue
            fn = getattr(module, name)
            if not callable(fn):
                continue
            tests += 1
            try:
                fn()
                print("PASS", path.name + "::" + name)
            except Exception:
                failures += 1
                print("FAIL", path.name + "::" + name)
                traceback.print_exc()
    print("%s tests, %s failures" % (tests, failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
