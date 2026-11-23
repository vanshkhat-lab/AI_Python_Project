"""Server-side Supabase authentication and atomic analysis credits.

Required Render environment variables:
  SUPABASE_URL
  SUPABASE_PUBLISHABLE_KEY
  SUPABASE_SECRET_KEY
Never expose SUPABASE_SECRET_KEY to Vite or commit it to Git.
"""
from __future__ import annotations

import json
import logging
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

from fastapi import Header, HTTPException

logger = logging.getLogger(__name__)


def _settings() -> tuple[str, str, str]:
    url = os.getenv("SUPABASE_URL", "").rstrip("/")
    publishable = os.getenv("SUPABASE_PUBLISHABLE_KEY", "")
    secret = os.getenv("SUPABASE_SECRET_KEY", "")
    if not url.startswith("https://") or not publishable or not secret:
        raise HTTPException(
            status_code=503,
            detail="Credit system is not configured on the backend.",
        )
    return url, publishable, secret


def _get_json(url: str, headers: dict[str, str]) -> dict:
    request = Request(url, headers=headers, method="GET")
    with urlopen(request, timeout=10) as response:
        return json.load(response)


def _post_json(url: str, headers: dict[str, str], payload: dict) -> object:
    data = json.dumps(payload).encode("utf-8")
    request = Request(url, headers=headers, data=data, method="POST")
    with urlopen(request, timeout=10) as response:
        return json.load(response)


def verify_user_token(token: str) -> str:
    url, publishable, _secret = _settings()
    try:
        user = _get_json(
            f"{url}/auth/v1/user",
            {
                "apikey": publishable,
                "Authorization": f"Bearer {token}",
            },
        )
    except HTTPError as exc:
        if exc.code in (401, 403):
            raise HTTPException(status_code=401, detail="Invalid or expired login session.") from exc
        logger.warning("Supabase authentication HTTP failure: %s", exc.code)
        raise HTTPException(status_code=502, detail="Login verification is temporarily unavailable.") from exc
    except (URLError, TimeoutError, ValueError) as exc:
        logger.warning("Supabase authentication unavailable (%s)", type(exc).__name__)
        raise HTTPException(status_code=502, detail="Login verification is temporarily unavailable.") from exc

    user_id = user.get("id") if isinstance(user, dict) else None
    if not isinstance(user_id, str) or not user_id:
        raise HTTPException(status_code=401, detail="Invalid login session.")
    return user_id


def current_user_id(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Please log in to analyze your resume.")
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Please log in to analyze your resume.")
    return verify_user_token(token)


def _rpc(function: str, user_id: str, request_id: str) -> object:
    url, _publishable, secret = _settings()
    try:
        # Modern Supabase sb_secret_* keys belong in 'apikey', never a Bearer header.
        return _post_json(
            f"{url}/rest/v1/rpc/{function}",
            {
                "apikey": secret,
                "Content-Type": "application/json",
            },
            {"p_user_id": user_id, "p_request_id": request_id},
        )
    except HTTPError as exc:
        logger.error("Supabase credit RPC %s returned HTTP %s", function, exc.code)
        raise HTTPException(
            status_code=502, detail="Credit system is temporarily unavailable."
        ) from exc
    except (URLError, TimeoutError, ValueError) as exc:
        logger.error("Supabase credit RPC %s failed (%s)", function, type(exc).__name__)
        raise HTTPException(
            status_code=502, detail="Credit system is temporarily unavailable."
        ) from exc


def _ledger_v2() -> bool:
    return os.getenv("RESUMEIQ_LEDGER_V2_ENABLED", "").strip().lower() == "true"


def reserve_credit(user_id: str) -> str:
    request_id = str(uuid4())
    remaining = _rpc("reserve_analysis_credit_v2" if _ledger_v2() else "reserve_analysis_credit", user_id, request_id)
    if remaining == -1:
        raise HTTPException(status_code=402, detail="No credits remaining. Please upgrade.")
    if not isinstance(remaining, int) or remaining < 0:
        raise HTTPException(status_code=502, detail="Unexpected credit system response.")
    return request_id


def complete_credit(user_id: str, request_id: str) -> None:
    if _rpc("complete_analysis_credit", user_id, request_id) is not True:
        raise HTTPException(status_code=502, detail="Could not finalize analysis credit.")


def refund_credit(user_id: str, request_id: str) -> None:
    refunded = _rpc("refund_analysis_credit_v2" if _ledger_v2() else "refund_analysis_credit", user_id, request_id)
    if refunded is not True:
        logger.warning("Credit transaction %s was not refunded (already finalized or missing)", request_id)
