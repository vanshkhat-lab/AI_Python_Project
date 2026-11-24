"""Razorpay credit purchases with explicit test/live environment isolation.

Fixed price and credits are defined on the backend, never accepted from React.
All Razorpay and Supabase privileged keys remain server-side.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen
from uuid import uuid4

from fastapi import HTTPException

logger = logging.getLogger(__name__)

PACK_AMOUNT_PAISE = 9900
PACK_CREDITS = 5
PACK_CURRENCY = "INR"


def payment_mode() -> str:
    """The server, never the browser, selects Razorpay's environment."""
    mode = os.getenv("RAZORPAY_MODE", "test").strip().lower()
    if mode not in ("test", "live"):
        raise HTTPException(status_code=503, detail="Invalid Razorpay mode configuration.")
    return mode


def ledger_v2_enabled() -> bool:
    return os.getenv("RESUMEIQ_LEDGER_V2_ENABLED", "").strip().lower() == "true"


def _env() -> tuple[str, str, str, str, str]:
    mode = payment_mode()
    key_id = os.getenv("RAZORPAY_KEY_ID", "").strip()
    key_secret = os.getenv("RAZORPAY_KEY_SECRET", "")
    supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
    supabase_secret = os.getenv("SUPABASE_SECRET_KEY", "")
    webhook_secret = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")
    expected_prefix = "rzp_live_" if mode == "live" else "rzp_test_"
    if mode == "live" and os.getenv("RAZORPAY_LIVE_ENABLED", "").lower() != "true":
        raise HTTPException(status_code=503, detail="Live checkout is not enabled for this service.")
    if mode == "live" and not ledger_v2_enabled():
        raise HTTPException(status_code=503, detail="Purchase-level credit accounting is required for live checkout.")
    if not (
        key_id.startswith(expected_prefix)
        and key_secret
        and supabase_url.startswith("https://")
        and supabase_secret
        and (mode != "live" or webhook_secret)
    ):
        raise HTTPException(status_code=503, detail="Payment gateway configuration is incomplete.")
    return key_id, key_secret, supabase_url, supabase_secret, webhook_secret


def checkout_config() -> dict:
    """Public, non-secret status for accurate payment labels in the frontend."""
    mode = payment_mode()
    try:
        _env()
    except HTTPException:
        return {"mode": mode, "enabled": False}
    return {"mode": mode, "enabled": True}


def _http_json(
    url: str,
    headers: dict[str, str],
    payload: dict | None = None,
) -> object:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8") if payload is not None else None,
        headers=headers,
        method="POST" if payload is not None else "GET",
    )
    with urlopen(request, timeout=15) as result:
        return json.load(result)


def _razorpay(path: str, payload: dict | None = None) -> dict:
    key_id, key_secret, *_ = _env()
    basic = base64.b64encode(f"{key_id}:{key_secret}".encode("utf-8")).decode("ascii")
    try:
        result = _http_json(
            f"https://api.razorpay.com/v1/{path.lstrip('/')}",
            {"Authorization": f"Basic {basic}", "Content-Type": "application/json"},
            payload,
        )
    except HTTPError as exc:
        logger.warning("Razorpay API returned HTTP %s", exc.code)
        raise HTTPException(status_code=502, detail="Payment gateway request failed.") from exc
    except (URLError, TimeoutError, ValueError) as exc:
        logger.warning("Razorpay API request failed: %s", type(exc).__name__)
        raise HTTPException(status_code=502, detail="Payment gateway is temporarily unavailable.") from exc
    if not isinstance(result, dict):
        raise HTTPException(status_code=502, detail="Unexpected payment gateway response.")
    return result


def _supabase_rpc(name: str, payload: dict) -> object:
    _id, _secret, url, supabase_secret, _webhook = _env()
    try:
        return _http_json(
            f"{url}/rest/v1/rpc/{name}",
            {"apikey": supabase_secret, "Content-Type": "application/json"},
            payload,
        )
    except HTTPError as exc:
        logger.error("Supabase payment RPC %s returned HTTP %s", name, exc.code)
        raise HTTPException(status_code=502, detail="Purchase database operation failed.") from exc
    except (URLError, TimeoutError, ValueError) as exc:
        logger.error("Supabase payment RPC %s failed: %s", name, type(exc).__name__)
        raise HTTPException(status_code=502, detail="Purchase database unavailable.") from exc


def _purchase(order_id: str) -> dict | None:
    _id, _secret, url, supabase_secret, _webhook = _env()
    safe_id = quote(order_id, safe="")
    try:
        result = _http_json(
            f"{url}/rest/v1/credit_purchases?razorpay_order_id=eq.{safe_id}&select=user_id,razorpay_order_id,razorpay_payment_id,amount_paise,currency,credits,status",
            {"apikey": supabase_secret},
        )
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        logger.warning("Purchase lookup failed: %s", type(exc).__name__)
        raise HTTPException(status_code=502, detail="Could not look up payment order.") from exc
    return result[0] if isinstance(result, list) and result else None


def create_order(user_id: str) -> dict:
    # Razorpay order is created first. Only server-approved purchases are recorded.
    order = _razorpay(
        "orders",
        {
            "amount": PACK_AMOUNT_PAISE,
            "currency": PACK_CURRENCY,
            "receipt": f"riq_{uuid4().hex[:20]}",
            "notes": {"product": "resumeiq_5_credits"},
        },
    )
    order_id = order.get("id")
    if (
        not isinstance(order_id, str)
        or not order_id.startswith("order_")
        or order.get("amount") != PACK_AMOUNT_PAISE
        or order.get("currency") != PACK_CURRENCY
    ):
        raise HTTPException(status_code=502, detail="Unexpected Razorpay order response.")

    order_details = {
        "p_user_id": user_id,
        "p_order_id": order_id,
        "p_amount_paise": PACK_AMOUNT_PAISE,
        "p_currency": PACK_CURRENCY,
        "p_credits": PACK_CREDITS,
    }
    if ledger_v2_enabled():
        order_details["p_payment_mode"] = payment_mode()
    recorded = _supabase_rpc(
        "register_resumeiq_credit_order_v2" if ledger_v2_enabled()
        else "register_resumeiq_credit_order",
        order_details,
    )
    if recorded is not True:
        raise HTTPException(status_code=502, detail="Could not register payment order.")
    key_id, *_ = _env()
    return {
        "key_id": key_id,
        "order_id": order_id,
        "amount": PACK_AMOUNT_PAISE,
        "currency": PACK_CURRENCY,
        "credits": PACK_CREDITS,
        "mode": payment_mode(),
    }


def _verified_capture(order_id: str, payment_id: str) -> None:
    payment = _razorpay(f"payments/{quote(payment_id, safe='')}")
    if (
        payment.get("id") != payment_id
        or payment.get("order_id") != order_id
        or payment.get("status") != "captured"
        or payment.get("amount") != PACK_AMOUNT_PAISE
        or payment.get("currency") != PACK_CURRENCY
    ):
        raise HTTPException(
            status_code=409,
            detail="Payment has not been captured for this ResumeIQ order.",
        )


def _grant_captured(order_id: str, payment_id: str, user_id: str | None = None) -> dict:
    order = _purchase(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Unknown ResumeIQ order.")
    if user_id is not None and order["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="This order belongs to another user.")
    if (
        order["amount_paise"] != PACK_AMOUNT_PAISE
        or order["currency"] != PACK_CURRENCY
        or order["credits"] != PACK_CREDITS
    ):
        raise HTTPException(status_code=409, detail="Invalid order package.")
    _verified_capture(order_id, payment_id)
    payment_details = {"p_order_id": order_id, "p_payment_id": payment_id}
    if ledger_v2_enabled():
        payment_details["p_payment_mode"] = payment_mode()
    state = _supabase_rpc(
        "apply_resumeiq_credit_payment_v2" if ledger_v2_enabled()
        else "apply_resumeiq_credit_payment",
        payment_details,
    )
    if state not in ("credited", "already_credited"):
        raise HTTPException(status_code=409, detail="Order and payment do not match.")
    return {"status": "paid", "credits_added": PACK_CREDITS, "already_processed": state == "already_credited"}


def confirm_checkout(user_id: str, order_id: str, payment_id: str, signature: str) -> dict:
    _key_id, key_secret, *_ = _env()
    order = _purchase(order_id)
    if order is None or order["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Payment order not found.")
    expected = hmac.new(
        key_secret.encode("utf-8"),
        f"{order_id}|{payment_id}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=400, detail="Payment signature verification failed.")
    return _grant_captured(order_id, payment_id, user_id)


def confirm_webhook(raw: bytes, signature: str) -> dict:
    _key_id, _key_secret, _url, _supabase_secret, webhook_secret = _env()
    if not webhook_secret:
        raise HTTPException(status_code=503, detail="Payment webhook is not configured.")
    expected = hmac.new(webhook_secret.encode("utf-8"), raw, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=400, detail="Invalid Razorpay webhook signature.")
    try:
        data = json.loads(raw)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid webhook payload.") from exc
    if data.get("event") in ("refund.created", "refund.processed", "refund.failed"):
        refund_entity = data.get("payload", {}).get("refund", {}).get("entity", {})
        refund_id = refund_entity.get("id") if isinstance(refund_entity, dict) else None
        if not isinstance(refund_id, str) or not refund_id.startswith("rfnd_"):
            raise HTTPException(status_code=400, detail="Webhook refund identifier missing.")
        # Lazy import avoids a circular import with the refund module.
        from backend.resumeiq.refunds import reconcile_provider_refund
        return reconcile_provider_refund(refund_id)
    if data.get("event") != "payment.captured":
        return {"status": "ignored"}
    payment = data.get("payload", {}).get("payment", {}).get("entity", {})
    order_id, payment_id = payment.get("order_id"), payment.get("id")
    if not (
        isinstance(order_id, str) and order_id.startswith("order_")
        and isinstance(payment_id, str) and payment_id.startswith("pay_")
    ):
        raise HTTPException(status_code=400, detail="Webhook payment identifiers are missing.")
    return _grant_captured(order_id, payment_id)


def purchase_status(user_id: str, order_id: str) -> dict:
    row = _purchase(order_id)
    if row is None or row["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Payment order not found.")

    # Recover if the checkout callback was lost and the webhook is delayed.
    if row["status"] == "created":
        payments = _razorpay(f"orders/{quote(order_id, safe='')}/payments")
        items = payments.get("items", [])
        if not isinstance(items, list):
            raise HTTPException(status_code=502, detail="Invalid Razorpay payment response.")
        for item in items:
            if (
                isinstance(item, dict)
                and item.get("status") == "captured"
                and item.get("order_id") == order_id
                and isinstance(item.get("id"), str)
            ):
                _grant_captured(order_id, item["id"], user_id)
                row = _purchase(order_id)
                break

    return {"status": row["status"], "credits": row["credits"] if row["status"] == "paid" else 0}
