"""The app's bundled Google OAuth *installed-app* client.

Why a client id/secret can live in source here: for the installed-app (loopback) flow, Google's own
documentation treats the client secret as **not confidential** — it cannot be protected inside a
distributed binary, and security comes from the redirect going to 127.0.0.1 on the user's own
machine plus PKCE, not from the secret. This is the same reason every open-source desktop Google
client ships one.

What it buys us: onboarding becomes one click. Without a bundled client, every user would have to
create a Google Cloud project, enable the Gmail API and download credentials — which nobody outside
this repo is going to do.

To enable Gmail in a build:
  1. Google Cloud console -> new project -> enable the Gmail API.
  2. OAuth consent screen: External, add the `gmail.readonly` scope, add a privacy policy URL.
  3. Credentials -> OAuth client ID -> **Desktop app**.
  4. Paste the client id and secret below, or set STATEMENTLENS_GOOGLE_CLIENT_ID /
     STATEMENTLENS_GOOGLE_CLIENT_SECRET at build time.

Distribution reality: `gmail.readonly` is a RESTRICTED scope. Unverified, the app works but shows an
"unverified app" warning and is capped at 100 users. Unlimited users additionally require a CASA
security assessment. Folder/upload import has no such gate, which is why it is the default path.
"""

from __future__ import annotations

import os
from typing import Optional

#: Filled in per build. Left blank in the public repo so no real credential is committed.
CLIENT_ID = ""
CLIENT_SECRET = ""

_AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
_TOKEN_URI = "https://oauth2.googleapis.com/token"


def bundled_client_config() -> Optional[dict]:
    """The installed-app client config, or None when this build has no Gmail client."""
    cid = os.getenv("STATEMENTLENS_GOOGLE_CLIENT_ID") or CLIENT_ID
    secret = os.getenv("STATEMENTLENS_GOOGLE_CLIENT_SECRET") or CLIENT_SECRET
    if not cid:
        return None
    return {
        "installed": {
            "client_id": cid,
            "client_secret": secret,
            "auth_uri": _AUTH_URI,
            "token_uri": _TOKEN_URI,
            "redirect_uris": ["http://localhost"],
        }
    }


def gmail_available() -> bool:
    """True when this build can offer Gmail connect (used to hide the button if it can't)."""
    return bundled_client_config() is not None
