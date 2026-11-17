"""HTTP(S) endpoint healthchecks (read-only GET requests only).

Endpoints and expected status codes always come from user
configuration.  Chekup never posts, writes or mutates anything.
"""

import urllib.request
from typing import Any, Dict, List

__all__ = ["check_url", "get_healthchecks_status"]


def check_url(url: str, timeout: float = 3.0,
              expect_status: int = 200) -> Dict[str, Any]:
    """Perform a single GET and return {url, ok, status, error}."""
    result: Dict[str, Any] = {"url": url, "ok": False, "status": None, "error": None}
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "chekup-readonly/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result["status"] = resp.status
            result["ok"] = resp.status == expect_status
            if not result["ok"]:
                result["error"] = f"expected HTTP {expect_status}, got {resp.status}"
    except urllib.error.HTTPError as e:  # noqa: E722
        result["status"] = e.code
        result["error"] = f"HTTP {e.code}"
    except Exception as e:
        result["error"] = f"{type(e).__name__}: {e}"
    return result


def get_healthchecks_status(
    healthchecks: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Check every configured endpoint and return result dicts."""
    results: List[Dict[str, Any]] = []
    for hc in healthchecks:
        url = hc.get("url", "")
        if not url:
            continue
        timeout = float(hc.get("timeout", 3.0))
        expect = int(hc.get("expect_status", 200))
        results.append(check_url(url, timeout=timeout, expect_status=expect))
    return results
