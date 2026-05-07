"""GoogleAdsClient: thin REST wrapper around the Google Ads API.

Two main methods:
  - search(customer_id, query, page_size=10000) -> generator of row dicts
  - mutate(customer_id, resource, operations, validate_only=False, partial_failure=False)

Plus account discovery:
  - list_accessible_customers()
  - list_customer_clients(login_customer_id)  - the MCC tree
"""
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Iterator, List, Optional

from .auth import AuthError, get_access_token
from .env import get_required, load_env

DEFAULT_PAGE_SIZE = 10000


class GoogleAdsError(RuntimeError):
    """Wraps a non-2xx response from the Google Ads API.

    Attributes:
      status: HTTP status code
      kind: top-level google.rpc Code (e.g. INVALID_ARGUMENT)
      message: human message
      errors: list of GoogleAdsError items from the failure detail
      raw: full parsed response body
    """

    def __init__(
        self,
        status: int,
        kind: str,
        message: str,
        errors: List[Dict],
        raw: Dict,
    ):
        super().__init__(f"[{status} {kind}] {message}")
        self.status = status
        self.kind = kind
        self.message = message
        self.errors = errors
        self.raw = raw


def _parse_error(status: int, body: bytes) -> GoogleAdsError:
    try:
        data = json.loads(body)
    except Exception:
        return GoogleAdsError(status, "UNKNOWN", body.decode(errors="replace"), [], {})
    err = data.get("error", {}) if isinstance(data, dict) else {}
    if not err and isinstance(data, list) and data:
        err = data[0].get("error", {})
    kind = err.get("status", "UNKNOWN")
    message = err.get("message", "")
    details = err.get("details", []) or []
    errors_list: List[Dict] = []
    for d in details:
        if d.get("@type", "").endswith("GoogleAdsFailure"):
            errors_list.extend(d.get("errors", []) or [])
    return GoogleAdsError(status, kind, message, errors_list, data)


class GoogleAdsClient:
    def __init__(
        self,
        env: Optional[Dict[str, str]] = None,
        login_customer_id: Optional[str] = None,
    ):
        self.env = get_required(env or load_env())
        self.api_version = self.env.get("GOOGLE_ADS_API_VERSION", "v20")
        self.base = f"https://googleads.googleapis.com/{self.api_version}"
        self.login_customer_id = (
            login_customer_id
            or self.env.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID")
            or None
        )
        if self.login_customer_id:
            self.login_customer_id = str(self.login_customer_id).replace("-", "")

    # ---------- HTTP plumbing ----------

    def _headers(self) -> Dict[str, str]:
        token = get_access_token(self.env)
        h = {
            "Authorization": f"Bearer {token}",
            "developer-token": self.env["GOOGLE_ADS_DEVELOPER_TOKEN"],
            "Content-Type": "application/json",
        }
        if self.login_customer_id:
            h["login-customer-id"] = self.login_customer_id
        return h

    def _request(
        self,
        method: str,
        url: str,
        body: Optional[Dict] = None,
        retries: int = 3,
    ) -> Dict:
        data = json.dumps(body).encode() if body is not None else None
        for attempt in range(retries + 1):
            req = urllib.request.Request(
                url, data=data, headers=self._headers(), method=method
            )
            try:
                with urllib.request.urlopen(req, timeout=120) as resp:
                    body_bytes = resp.read()
                    if not body_bytes:
                        return {}
                    return json.loads(body_bytes)
            except urllib.error.HTTPError as e:
                body_bytes = e.read()
                if e.code == 401 and attempt < retries:
                    # token expired mid-flight: force refresh and retry
                    get_access_token(self.env, force_refresh=True)
                    continue
                if e.code in (429, 500, 502, 503, 504) and attempt < retries:
                    time.sleep(2 ** attempt)
                    continue
                raise _parse_error(e.code, body_bytes) from None
            except urllib.error.URLError as e:
                if attempt < retries:
                    time.sleep(2 ** attempt)
                    continue
                raise GoogleAdsError(0, "NETWORK", str(e), [], {})
        raise GoogleAdsError(0, "UNKNOWN", "request retries exhausted", [], {})

    # ---------- Account discovery ----------

    def list_accessible_customers(self) -> List[str]:
        """Returns customer IDs (no dashes) the authenticated user can access."""
        url = f"{self.base}/customers:listAccessibleCustomers"
        out = self._request("GET", url)
        return [r.split("/")[-1] for r in out.get("resourceNames", [])]

    def list_customer_clients(self, manager_customer_id: str) -> List[Dict]:
        """Returns the full MCC tree visible from a manager account.
        Each row has: client_customer (resource name), id, descriptive_name,
        currency_code, time_zone, manager (bool), test_account (bool), level, status.
        """
        manager_customer_id = str(manager_customer_id).replace("-", "")
        query = """
            SELECT
              customer_client.client_customer,
              customer_client.id,
              customer_client.descriptive_name,
              customer_client.currency_code,
              customer_client.time_zone,
              customer_client.manager,
              customer_client.test_account,
              customer_client.level,
              customer_client.status
            FROM customer_client
            WHERE customer_client.status != 'CLOSED'
        """
        prev_login = self.login_customer_id
        self.login_customer_id = manager_customer_id
        try:
            return list(self.search(manager_customer_id, query))
        finally:
            self.login_customer_id = prev_login

    # ---------- GAQL search ----------

    def search(
        self,
        customer_id: str,
        query: str,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> Iterator[Dict]:
        """Streams rows from googleAds:searchStream. Yields each row as a dict."""
        customer_id = str(customer_id).replace("-", "")
        url = f"{self.base}/customers/{customer_id}/googleAds:searchStream"
        body = {"query": query.strip()}
        # searchStream returns a JSON array of stream messages, each with a "results" list
        out = self._request("POST", url, body)
        if isinstance(out, list):
            chunks = out
        elif isinstance(out, dict) and "results" in out:
            chunks = [out]
        else:
            chunks = out.get("streamingChunks", []) if isinstance(out, dict) else []
        for chunk in chunks:
            for row in chunk.get("results", []) or []:
                yield row

    def search_paginated(
        self,
        customer_id: str,
        query: str,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> Iterator[Dict]:
        """Uses non-streaming /googleAds:search with pagination. For very large pages."""
        customer_id = str(customer_id).replace("-", "")
        url = f"{self.base}/customers/{customer_id}/googleAds:search"
        body = {"query": query.strip(), "pageSize": page_size}
        next_token = None
        while True:
            req = dict(body)
            if next_token:
                req["pageToken"] = next_token
            out = self._request("POST", url, req)
            for row in out.get("results", []) or []:
                yield row
            next_token = out.get("nextPageToken")
            if not next_token:
                break

    # ---------- Mutations ----------

    def mutate_resource(
        self,
        customer_id: str,
        resource_plural: str,
        operations: List[Dict],
        validate_only: bool = False,
        partial_failure: bool = False,
        response_content_type: str = "RESOURCE_NAME_ONLY",
    ) -> Dict:
        """Single-resource mutate: customers/{id}/{resource_plural}:mutate.

        resource_plural examples: campaigns, adGroups, adGroupAds, adGroupCriteria,
        campaignBudgets, campaignCriteria, conversionActions, customerLabels.
        operations: list of {create|update|remove[, updateMask]}.
        """
        customer_id = str(customer_id).replace("-", "")
        url = f"{self.base}/customers/{customer_id}/{resource_plural}:mutate"
        body = {
            "operations": operations,
            "validateOnly": validate_only,
            "partialFailure": partial_failure,
            "responseContentType": response_content_type,
        }
        return self._request("POST", url, body)

    def mutate_batch(
        self,
        customer_id: str,
        mutate_operations: List[Dict],
        validate_only: bool = False,
        partial_failure: bool = False,
        response_content_type: str = "RESOURCE_NAME_ONLY",
    ) -> Dict:
        """Cross-resource batch via customers/{id}/googleAds:mutate.

        Each mutate_operation is a dict with exactly one of:
          campaignOperation, adGroupOperation, adGroupAdOperation,
          adGroupCriterionOperation, campaignBudgetOperation, campaignCriterionOperation,
          assetOperation, assetGroupOperation, assetGroupAssetOperation,
          conversionActionOperation, customerLabelOperation, etc.
        """
        customer_id = str(customer_id).replace("-", "")
        url = f"{self.base}/customers/{customer_id}/googleAds:mutate"
        body = {
            "mutateOperations": mutate_operations,
            "validateOnly": validate_only,
            "partialFailure": partial_failure,
            "responseContentType": response_content_type,
        }
        return self._request("POST", url, body)

    # ---------- Helpers ----------

    @staticmethod
    def micros(amount: float) -> int:
        """Convert a currency amount (e.g. 12.50 USD) to micros."""
        return int(round(amount * 1_000_000))

    @staticmethod
    def from_micros(micros_value: int) -> float:
        """Convert micros back to currency units."""
        return (int(micros_value) if micros_value else 0) / 1_000_000.0

    @staticmethod
    def resource_name(customer_id: str, resource_plural: str, resource_id: Any) -> str:
        return f"customers/{str(customer_id).replace('-', '')}/{resource_plural}/{resource_id}"
