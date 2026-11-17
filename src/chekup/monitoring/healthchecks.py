"""HTTP(S) endpoint healthchecks (read-only GET requests only).

Endpoints and expected status codes always come from user
configuration.  Chekup never posts, writes or mutates anything.
"""

import subprocess
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


def check_nupur_router_health(url: str = "http://127.0.0.1:8001/health",
                               timeout: float = 2.0) -> Dict[str, Any]:
    """Check Nupur router health endpoint (VPS-style).
    
    Returns dict like: {"url": "...", "ok": True, "status": 200, "error": None}
    or {"url": "...", "ok": False, "status": None, "error": "UNREACHABLE"}
    """
    result: Dict[str, Any] = {
        "url": url, "ok": False, "status": None, "error": None
    }
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "chekup-readonly/1.0"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result["status"] = resp.status
            result["ok"] = resp.status == 200
            if not result["ok"]:
                result["error"] = f"expected HTTP 200, got {resp.status}"
    except Exception as e:
        result["error"] = "UNREACHABLE"
    return result


def check_nginx_listener() -> bool:
    """Check if Nginx is actually listening on :80 or :443 (VPS fallback).
    
    Returns True if sockets found, False otherwise.
    """
    try:
        p = subprocess.run(
            ["ss", "-H", "-lnt"],
            capture_output=True, text=True, timeout=3, errors="replace"
        )
        sockets = p.stdout
        return ":80 " in sockets or ":443 " in sockets
    except Exception:
        return False
