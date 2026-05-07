"""Google Ads plugin shared library.

Modules:
- env: loads .secrets/.env into a dict
- auth: OAuth refresh-token -> access-token flow
- client: GoogleAdsClient with .search() and .mutate() helpers
- format: pretty-print results as markdown / CSV
- errors: friendly translations of GoogleAdsFailure errors
"""
from .env import load_env, get_required
from .auth import get_access_token
from .client import GoogleAdsClient, GoogleAdsError
from . import format as fmt
from . import errors

__all__ = [
    "load_env",
    "get_required",
    "get_access_token",
    "GoogleAdsClient",
    "GoogleAdsError",
    "fmt",
    "errors",
]
