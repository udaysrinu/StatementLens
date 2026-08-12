#!/usr/bin/env bash
# Publish a release. Run this, and every no-warning install channel starts working.
#
#   ./packaging/release.sh --check     # build + validate, publish nothing (default)
#   ./packaging/release.sh --testpypi  # dry run against TestPyPI
#   ./packaging/release.sh --publish   # real PyPI upload
#
# Why PyPI is the whole game for distribution: Gatekeeper and SmartScreen warn based on the
# `com.apple.quarantine` xattr that BROWSERS attach to downloads, not on whether a binary is signed.
# Package managers never set it. So `brew install` / `pipx install` / `winget install` launch with NO
# warning and NO code-signing certificate — and all three install from PyPI. Publishing there is
# therefore the free alternative to a $99/yr Apple account, and only the raw .zip download still
# needs signing.
#
# Auth: create a scoped token at https://pypi.org/manage/account/token/ and export
#   TWINE_USERNAME=__token__
#   TWINE_PASSWORD=pypi-...
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODE="${1:---check}"
cd "$ROOT"

VERSION="$(python3 -c "
import re,pathlib
print(re.search(r'^version = \"([^\"]+)\"', pathlib.Path('pyproject.toml').read_text(), re.M).group(1))
")"
echo "==> statementlens $VERSION"

echo "==> tests must pass before anything is published"
PYTHONPATH=src python3 - <<'PY'
import importlib, os, sys, traceback
mods = [f[:-3] for f in sorted(os.listdir("tests"))
        if f.startswith("test_") and f.endswith(".py")]
tot = bad = 0
for mn in mods:
    m = importlib.import_module("tests." + mn)
    for n in sorted(d for d in dir(m) if d.startswith("test_")):
        fn = getattr(m, n)
        if not callable(fn):
            continue
        tot += 1
        try:
            fn()
        except Exception:
            bad += 1
            print("FAIL", mn, n)
            traceback.print_exc()
print(f"{tot - bad}/{tot} passed")
sys.exit(1 if bad else 0)
PY

echo "==> build"
python3 -m pip install --quiet --upgrade build twine
rm -rf dist build ./*.egg-info
python3 -m build --outdir dist >/dev/null

echo "==> validate the artifacts (catches the metadata errors that break pip install)"
python3 -m twine check dist/*

echo "==> install the wheel into a clean venv and run it"
TMP="$(mktemp -d)"
python3 -m venv "$TMP/venv" >/dev/null
"$TMP/venv/bin/pip" install --quiet "$(ls dist/*.whl)"
"$TMP/venv/bin/statementlens" --db "$TMP/t.db" stats >/dev/null
echo "    wheel installs and runs"

SDIST="$(ls dist/*.tar.gz)"
echo "==> sdist sha256 (paste into packaging/Formula/statementlens.rb):"
shasum -a 256 "$SDIST" | awk '{print "    " $1}'
rm -rf "$TMP"

case "$MODE" in
  --publish)
    : "${TWINE_USERNAME:?export TWINE_USERNAME=__token__}"
    : "${TWINE_PASSWORD:?export TWINE_PASSWORD=pypi-...}"
    python3 -m twine upload dist/*
    echo "==> published. Users can now install with NO security warning:"
    echo "      pipx install statementlens          # any platform"
    echo "      brew install statementlens          # after tapping the formula"
    ;;
  --testpypi)
    : "${TWINE_PASSWORD:?export TWINE_PASSWORD=pypi-... (a TestPyPI token)}"
    python3 -m twine upload --repository testpypi dist/*
    ;;
  *)
    echo "==> check only — nothing published. Re-run with --publish when ready."
    ;;
esac
