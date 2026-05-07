"""OAuth: exchange refresh_token for access_token. Cached on disk for ~50 min."""
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict

CACHE_PATH = Path.home() / ".cache" / "google-ads-plugin" / "access_token.json"
TOKEN_TTL_BUFFER = 600  # refresh 10 min before actual expiry


class AuthError(RuntimeError):
    pass


def _load_cache() -> Dict:
    if not CACHE_PATH.exists():
        return {}
    try:
        return json.loads(CACHE_PATH.read_text())
    except Exception:
        return {}


def _save_cache(data: Dict) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(data))
    try:
        os.chmod(CACHE_PATH, 0o600)
    except OSError:
        pass


def _refresh(client_id: str, client_secret: str, refresh_token: str) -> Dict:
    data = urllib.parse.urlencode(
        {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
    ).encode()
    req = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            err = json.loads(body)
            kind = err.get("error", "unknown")
            desc = err.get("error_description", "")
        except Exception:
            kind, desc = "http_error", body
        raise AuthError(
            f"OAuth refresh failed ({kind}): {desc}\n"
            "Common causes:\n"
            "  - refresh_token was issued for a different client_id\n"
            "  - OAuth client is in 'Testing' mode (tokens expire after 7 days)\n"
            "  - User revoked access at https://myaccount.google.com/permissions\n"
            "Fix: rerun scripts/oauth_setup.py to mint a fresh refresh_token."
        )
    except urllib.error.URLError as e:
        raise AuthError(f"Network error contacting Google OAuth: {e}")


def get_access_token(env: Dict[str, str], force_refresh: bool = False) -> str:
    """Returns a valid access_token, refreshing if needed. Caches per refresh_token."""
    refresh_token = env["GOOGLE_ADS_REFRESH_TOKEN"]
    cache = _load_cache()
    cached = cache.get(refresh_token)
    if (
        not force_refresh
        and cached
        and cached.get("access_token")
        and cached.get("expires_at", 0) - TOKEN_TTL_BUFFER > time.time()
    ):
        return cached["access_token"]

    tok = _refresh(
        env["GOOGLE_ADS_CLIENT_ID"],
        env["GOOGLE_ADS_CLIENT_SECRET"],
        refresh_token,
    )
    expires_in = int(tok.get("expires_in", 3600))
    cache[refresh_token] = {
        "access_token": tok["access_token"],
        "expires_at": int(time.time()) + expires_in,
    }
    _save_cache(cache)
    return tok["access_token"]
