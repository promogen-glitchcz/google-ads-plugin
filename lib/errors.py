"""Friendly translation of Google Ads API errors with concrete fix suggestions.

Use:
    from lib import errors as err
    print(err.explain(google_ads_error))
"""
from typing import Dict


# Each entry: {"summary": short reason, "fix": what to do}
ERROR_GUIDE: Dict[str, Dict[str, str]] = {
    "DEVELOPER_TOKEN_NOT_APPROVED": {
        "summary": "Your developer token isn't approved for this kind of request.",
        "fix": "Apply for Standard or Basic access in Google Ads UI: Tools -> API Center. Until approved, only test accounts work.",
    },
    "DEVELOPER_TOKEN_NOT_WHITELISTED": {
        "summary": "Developer token only allowed against test accounts.",
        "fix": "Either use a test customer ID, or apply for Basic Access for the token.",
    },
    "USER_PERMISSION_DENIED": {
        "summary": "The Google account behind the refresh token has no permission on this customer.",
        "fix": "Have an admin invite the user to the Google Ads account, then accept invite, then mint a new refresh token.",
    },
    "CUSTOMER_NOT_ENABLED": {
        "summary": "Customer is disabled or canceled.",
        "fix": "Re-enable the customer in the Google Ads UI, or pick a different customer ID.",
    },
    "CUSTOMER_NOT_FOUND": {
        "summary": "The customer_id you used doesn't match any customer the auth user can see.",
        "fix": "Run the account-explorer skill to list accessible customer IDs.",
    },
    "INVALID_CUSTOMER_ID": {
        "summary": "Customer ID isn't a 10-digit number.",
        "fix": "Strip dashes and use the 10-digit form (e.g. 1234567890, not 123-456-7890).",
    },
    "MISSING_LOGIN_CUSTOMER_ID": {
        "summary": "Operating on a sub-account but didn't pass login-customer-id header.",
        "fix": "Set GOOGLE_ADS_LOGIN_CUSTOMER_ID to your manager (MCC) customer ID.",
    },
    "QUOTA_EXCEEDED": {
        "summary": "You hit a daily/monthly request limit on the developer token.",
        "fix": "Apply for higher access tier. In the meantime, batch operations and back off requests.",
    },
    "RESOURCE_EXHAUSTED": {
        "summary": "Per-second rate limit hit.",
        "fix": "Add exponential backoff. Lib client already retries 429 with 2^n backoff.",
    },
    "INVALID_ARGUMENT": {
        "summary": "One of your fields is malformed (often the GAQL query or an update_mask).",
        "fix": "Read the inner errors[] for which field. For mutations, double-check update_mask paths and required fields.",
    },
    "REQUEST_HEADER_NOT_ALLOWED": {
        "summary": "Sent login-customer-id when not allowed (or vice versa).",
        "fix": "If the customer is the manager itself, omit login-customer-id.",
    },
    "INVALID_GRANT": {
        "summary": "Refresh token is no longer valid.",
        "fix": "Run scripts/oauth_setup.py to mint a fresh refresh token.",
    },
    "UNAUTHORIZED_CLIENT": {
        "summary": "Refresh token doesn't match the client_id/secret pair.",
        "fix": "These three credentials must come from the SAME Google Cloud OAuth client. Re-run scripts/oauth_setup.py.",
    },
    "AUTHENTICATION_ERROR": {
        "summary": "Auth failed somewhere (token, dev token, or scope).",
        "fix": "Check (a) developer-token header is present, (b) refresh token is valid, (c) scope is https://www.googleapis.com/auth/adwords.",
    },
    "REQUIRED_FIELD_MISSING": {
        "summary": "A required field on the operation wasn't set.",
        "fix": "See errors[].location.field_path_elements - that lists the missing field name.",
    },
    "DUPLICATE_NAME": {
        "summary": "A campaign/ad group with that name already exists.",
        "fix": "Pick a different name or update the existing entity.",
    },
    "POLICY_VIOLATION": {
        "summary": "Ad / asset violates Google's policy.",
        "fix": "Check errors[].details for the policy topic. May need to revise copy or request review.",
    },
    "INVALID_STATUS_TRANSITION": {
        "summary": "Tried to move a resource from REMOVED back to ENABLED, or similar.",
        "fix": "REMOVED is terminal - create a new resource instead.",
    },
}


def explain(error) -> str:
    """Pretty-print a GoogleAdsError with guidance.
    Accepts either a GoogleAdsError instance or a dict-like body.
    """
    parts = []
    status = getattr(error, "status", None)
    kind = getattr(error, "kind", None)
    message = getattr(error, "message", None)
    errors_list = getattr(error, "errors", []) or []

    if status:
        parts.append(f"HTTP {status} - {kind}: {message}")
    elif message:
        parts.append(message)

    for i, e in enumerate(errors_list, 1):
        ec = e.get("errorCode", {}) or {}
        # errorCode is one-of: e.g. {"authenticationError": "OAUTH_TOKEN_INVALID"}
        if ec:
            label, code = next(iter(ec.items()))
        else:
            label, code = "unknown", "UNKNOWN"
        msg = e.get("message", "")
        guide = ERROR_GUIDE.get(code) or ERROR_GUIDE.get(code.upper(), {})
        parts.append(f"  [{i}] {label} = {code}")
        if msg:
            parts.append(f"      {msg}")
        if guide:
            parts.append(f"      WHY:  {guide['summary']}")
            parts.append(f"      FIX:  {guide['fix']}")
        loc = e.get("location", {})
        if loc:
            fpe = loc.get("fieldPathElements") or loc.get("field_path_elements") or []
            field = ".".join(p.get("fieldName", p.get("field_name", "")) for p in fpe)
            if field:
                parts.append(f"      AT:   {field}")
    return "\n".join(parts) if parts else str(error)
