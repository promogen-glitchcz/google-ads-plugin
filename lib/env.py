"""Load credentials from .secrets/.env.

Resolution order:
1. Environment variables (process env wins)
2. .secrets/.env in plugin root
3. ~/.config/google-ads-plugin/.env (per-user fallback)
"""
import os
from pathlib import Path
from typing import Dict, Optional

REQUIRED_KEYS = [
    "GOOGLE_ADS_CLIENT_ID",
    "GOOGLE_ADS_CLIENT_SECRET",
    "GOOGLE_ADS_DEVELOPER_TOKEN",
    "GOOGLE_ADS_REFRESH_TOKEN",
]

OPTIONAL_KEYS = [
    "GOOGLE_ADS_LOGIN_CUSTOMER_ID",
    "GOOGLE_ADS_API_VERSION",
    "GOOGLE_ADS_DEFAULT_CUSTOMER_ID",
]


def _parse_env_file(path: Path) -> Dict[str, str]:
    out = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        v = v.strip()
        if v.startswith('"') and v.endswith('"'):
            v = v[1:-1]
        elif v.startswith("'") and v.endswith("'"):
            v = v[1:-1]
        out[k.strip()] = v
    return out


def _candidate_paths() -> list:
    here = Path(__file__).resolve()
    plugin_root = here.parent.parent
    return [
        plugin_root / ".secrets" / ".env",
        Path.home() / ".config" / "google-ads-plugin" / ".env",
    ]


def load_env() -> Dict[str, str]:
    """Returns a merged dict. Process env overrides files. Files: first found wins."""
    merged: Dict[str, str] = {}
    for p in _candidate_paths():
        for k, v in _parse_env_file(p).items():
            merged.setdefault(k, v)
    for k in REQUIRED_KEYS + OPTIONAL_KEYS:
        if k in os.environ and os.environ[k]:
            merged[k] = os.environ[k]
    merged.setdefault("GOOGLE_ADS_API_VERSION", "v20")
    return merged


def get_required(env: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """Returns env or raises with a clear message naming missing keys."""
    env = env or load_env()
    missing = [k for k in REQUIRED_KEYS if not env.get(k)]
    if missing:
        raise RuntimeError(
            "Missing required credentials: "
            + ", ".join(missing)
            + ". Set them in .secrets/.env or run scripts/oauth_setup.py"
        )
    return env
