#!/usr/bin/env bash
# Double-click this ONCE if macOS says StatementLens "cannot be opened because it is from an
# unidentified developer".
#
# It removes the com.apple.quarantine attribute your BROWSER attached to the download. That flag —
# not the absence of a signature — is what Gatekeeper acts on, which is why `brew install` binaries
# open silently. Nothing else is changed, and no permissions are requested.
#
# Prefer `brew install statementlens` or `pipx install statementlens`; neither needs this.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP="$HERE/StatementLens"
[[ -d "$APP" ]] || APP="$HERE"
echo "Removing the download quarantine flag from:"
echo "  $APP"
xattr -dr com.apple.quarantine "$APP" 2>/dev/null || true
echo
echo "Done. StatementLens will now open normally."
echo "Press Enter to close."
read -r _ || true
