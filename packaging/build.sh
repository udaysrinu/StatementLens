#!/usr/bin/env bash
# Build a double-clickable StatementLens for people who do not have Python.
#
#   ./packaging/build.sh            # unsigned build (works, shows an OS warning on first launch)
#   ./packaging/build.sh --sign     # signed + notarized (needs the credentials below)
#
# The unsigned build is fully functional — Gatekeeper/SmartScreen just require the user to click
# through a warning once. Signing removes that warning; it cannot be automated here because it needs
# an Apple Developer account (macOS) or an EV/OV code-signing certificate (Windows), which only the
# project owner can hold.
#
# To sign on macOS, export these first:
#   APPLE_SIGNING_IDENTITY  e.g. "Developer ID Application: Your Name (TEAMID)"
#   APPLE_ID                your Apple ID email
#   APPLE_TEAM_ID           the 10-character team id
#   APPLE_APP_PASSWORD      an app-specific password from appleid.apple.com
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST="$ROOT/dist"
APP_NAME="StatementLens"
SIGN=false
[[ "${1:-}" == "--sign" ]] && SIGN=true

cd "$ROOT"
python3 -m pip install --quiet --upgrade build pyinstaller

echo "==> wheel + sdist"
rm -rf "$DIST" build ./*.egg-info
python3 -m build --outdir "$DIST" >/dev/null
ls -1 "$DIST"

echo "==> self-contained binary"
# --onedir rather than --onefile: a onefile binary unpacks to a temp dir on every launch, which is
# slower and trips some endpoint-security tools. Hidden imports are the lazily-imported adapters that
# PyInstaller's static analysis cannot see.
# --paths src is required: --collect-submodules alone finds nothing when the package is not installed
# in the build environment, and the binary then dies with ModuleNotFoundError at launch.
python3 -m PyInstaller \
  --noconfirm --clean --onedir --name "$APP_NAME" \
  --paths "$ROOT/src" \
  --collect-submodules statementlens \
  --hidden-import pikepdf --hidden-import pdfplumber \
  --hidden-import googleapiclient.discovery --hidden-import google_auth_oauthlib.flow \
  --distpath "$DIST/app" --workpath "$ROOT/build" --specpath "$ROOT/build" \
  "$ROOT/packaging/launcher.py" >/dev/null

BUNDLE="$DIST/app/$APP_NAME"
echo "    -> $BUNDLE"

if [[ "$(uname)" == "Darwin" && "$SIGN" == true ]]; then
  : "${APPLE_SIGNING_IDENTITY:?set APPLE_SIGNING_IDENTITY}"
  : "${APPLE_ID:?set APPLE_ID}" ; : "${APPLE_TEAM_ID:?set APPLE_TEAM_ID}"
  : "${APPLE_APP_PASSWORD:?set APPLE_APP_PASSWORD}"

  echo "==> signing"
  # --options runtime enables the hardened runtime, which notarization requires.
  codesign --force --deep --timestamp --options runtime \
           --sign "$APPLE_SIGNING_IDENTITY" "$BUNDLE"
  codesign --verify --strict --verbose=2 "$BUNDLE"

  echo "==> notarizing (a few minutes; Apple scans the upload)"
  ZIP="$DIST/$APP_NAME.zip"
  ditto -c -k --keepParent "$BUNDLE" "$ZIP"
  xcrun notarytool submit "$ZIP" --apple-id "$APPLE_ID" --team-id "$APPLE_TEAM_ID" \
        --password "$APPLE_APP_PASSWORD" --wait
  # Stapling attaches the ticket so the app also launches offline.
  xcrun stapler staple "$BUNDLE"
  spctl --assess --type execute --verbose "$BUNDLE"
  echo "==> signed, notarized, stapled"
else
  echo "==> UNSIGNED build."
  if [[ "$(uname)" == "Darwin" ]]; then
    echo "    First launch: right-click -> Open, then Open again. Or:"
    echo "      xattr -dr com.apple.quarantine '$BUNDLE'"
  else
    echo "    First launch: SmartScreen -> More info -> Run anyway."
  fi
  echo "    Re-run with --sign once signing credentials are available."
fi
