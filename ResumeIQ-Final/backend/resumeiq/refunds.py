"""Refund requests for unused five-credit packs.

Feature-gated, server-side only. Never issue real refunds without validated
merchant approval, policy review and the matching database migration.
"""
from __future__ import annotations

import base64
import json
import logging
import os
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from fastapi import HTTPException

from backend.resumeiq import payments

logger = logging.getLogger(__name__)
AMOUNT = 9900
CURRENCY = "INR"


def _enabled() -> bool:
    return os.getenv("RESUMEIQ_REFUNDS_ENABLED", "false").lower() == "true"


def _guard() -> None:
    if not _enabled() or not payments.ledger_v2_enabled():
        raise HTTPException(503, "Refund processing is not enabled.")
    # Never mix real-money refunds into the staging/test environment.
    if payments.payment_mode() not in ("test", "live"):
        raise HTTPException(503, "Invalid payment mode.")
    payments._env()


def _provider(path: str, body: dict | None = None, key: str | None = None) -> dict:
    key_id, secret, *_ = payments._env()
    encoded = base64.b64encode(f"{key_id}:{secret}".encode()).decode()
    headers = {"Authorization": f"Basic {encoded}", "Content-Type": "application/json"}
    if key is not None:
        headers["X-Refund-Idempotency"] = key
    req = Request(
        "https://api.razorpay.com/v1/" + path.lstrip("/"),
        data=json.dumps(body, separators=(",", ":"), sort_keys=True).encode() if body is not None else None,
        headers=headers,
        method="POST" if body is not None else "GET",
    )
    try:
        with urlopen(req, timeout=15) as response:
            result = json.load(response)
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        logger.warning("Razorpay refund status unknown or unavailable: %s", type(exc).__name__)
        raise HTTPException(502, "Refund state needs reconciliation. Do not create another request.") from exc
    if not isinstance(result, dict):
        raise HTTPException(502, "Unexpected refund gateway response.")
    return result


def _validate_refund(refund: dict, payment_id: str) -> str:
    refund_id = refund.get("id")
    state = refund.get("status")
    if (not isinstance(refund_id, str) or not refund_id.startswith("rfnd_")
        or refund.get("payment_id") != payment_id
        or refund.get("amount") != AMOUNT
        or refund.get("currency") != CURRENCY
        or state not in ("pending", "processed", "failed")):
        raise HTTPException(502, "Unexpected refund response. Manual reconciliation required.")
    return state


def _record_refund(refund: dict, payment_id: str) -> str:
    state = _validate_refund(refund, payment_id)
    result = payments._supabase_rpc("record_resumeiq_pack_refund_v1", {
        "p_payment_id": payment_id,
        "p_refund_id": refund["id"],
        "p_status": state,
        "p_amount_paise": AMOUNT,
        "p_currency": CURRENCY,
    })
    if result not in (state, "already_" + state):
        raise HTTPException(409, "Refund ledger conflict; manual review required.")
    return state


def request_pack_refund(user_id: str, order_id: str) -> dict:
    _guard()
    if not order_id.startswith("order_") or len(order_id) > 100:
        raise HTTPException(400, "Invalid order ID.")

    # Atomic reservation removes unused credits before any provider request.
    reservation = payments._supabase_rpc("request_resumeiq_pack_refund_v1", {
        "p_user_id": user_id, "p_order_id": order_id,
        "p_mode": payments.payment_mode(),
    })
    if not isinstance(reservation, dict):
        raise HTTPException(502, "Invalid refund reservation response.")
    if reservation.get("status") == "ineligible":
        return {"status": "ineligible", "reason": reservation.get("reason")}
    if reservation.get("status") in ("processed", "failed"):
        return {"status": reservation["status"], "refund_id": reservation.get("refund_id")}
    if reservation.get("status") == "pending" and reservation.get("refund_id"):
        return reconcile_pack_refund(user_id, order_id)

    payment_id = reservation.get("payment_id")
    stable_key = reservation.get("idempotency_key")
    if (not isinstance(payment_id, str) or not payment_id.startswith("pay_")
        or not isinstance(stable_key, str) or len(stable_key) < 10):
        raise HTTPException(502, "Invalid refund reference.")

    # Same stable key and identical body on every retry; prevents double refunds.
    result = _provider(
        f"payments/{quote(payment_id, safe='')}/refund",
        {"amount": AMOUNT},
        stable_key,
    )
    state = _record_refund(result, payment_id)
    return {"status": state, "refund_id": result["id"]}


def reconcile_pack_refund(user_id: str, order_id: str) -> dict:
    _guard()
    if not order_id.startswith("order_") or len(order_id) > 100:
        raise HTTPException(400, "Invalid order ID.")
    current = payments._supabase_rpc("get_resumeiq_pack_refund_v1", {
        "p_user_id": user_id, "p_order_id": order_id,
    })
    if not isinstance(current, dict) or current.get("status") == "not_found":
        return {"status": "not_found"}
    refund_id, payment_id = current.get("refund_id"), current.get("payment_id")
    if current.get("status") in ("processed", "failed"):
        return {"status": current["status"], "refund_id": refund_id}
    if not refund_id:
        return {"status": "awaiting_provider_confirmation"}
    if not isinstance(refund_id, str) or not refund_id.startswith("rfnd_"):
        raise HTTPException(502, "Invalid refund reference.")
    refund = _provider(f"refunds/{quote(refund_id, safe='')}")
    state = _record_refund(refund, payment_id)
    return {"status": state, "refund_id": refund_id}
