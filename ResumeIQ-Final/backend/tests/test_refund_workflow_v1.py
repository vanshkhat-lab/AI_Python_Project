"""Refund API unit checks: all external calls are mocked; no real money.

Run: python -m pytest backend/tests/test_refund_workflow_v1.py -q
"""
import pytest
from fastapi import HTTPException
from backend.resumeiq import refunds, payments


@pytest.fixture(autouse=True)
def fake_env(monkeypatch):
    monkeypatch.setenv("RESUMEIQ_LEDGER_V2_ENABLED", "true")
    monkeypatch.setenv("RAZORPAY_MODE", "test")
    monkeypatch.setenv("RESUMEIQ_REFUNDS_ENABLED", "true")
    monkeypatch.setattr(payments, "_env", lambda: ("rzp_test_fake", "secret", "https://example.supabase.co", "secret", "webhook"))


def test_default_disabled(monkeypatch):
    monkeypatch.delenv("RESUMEIQ_REFUNDS_ENABLED", raising=False)
    with pytest.raises(HTTPException) as e:
        refunds.request_pack_refund("user-123", "order_123")
    assert e.value.status_code == 503


def test_no_gateway_call_when_ineligible(monkeypatch):
    monkeypatch.setattr(payments, "_supabase_rpc", lambda name, payload: {"status": "ineligible", "reason": "credits_used_or_reserved"})
    monkeypatch.setattr(refunds, "_provider", lambda *args, **kwargs: pytest.fail("provider must not be called"))
    assert refunds.request_pack_refund("user-123", "order_123")["status"] == "ineligible"


def test_refund_request_uses_fixed_amount_and_stable_key(monkeypatch):
    calls = []
    def rpc(name, payload):
        calls.append((name, payload))
        if name == "request_resumeiq_pack_refund_v1":
            return {"status": "requested", "payment_id": "pay_123",
                    "idempotency_key": "12345678-1234-1234-1234-123456789abc"}
        return "pending"
    def provider(path, body=None, key=None):
        calls.append(("provider", path, body, key))
        return {"id": "rfnd_123", "payment_id": "pay_123",
                "amount": 9900, "currency": "INR", "status": "pending"}
    monkeypatch.setattr(payments, "_supabase_rpc", rpc)
    monkeypatch.setattr(refunds, "_provider", provider)
    result = refunds.request_pack_refund("user-123", "order_123")
    assert result == {"status": "pending", "refund_id": "rfnd_123"}
    assert ("provider", "payments/pay_123/refund", {"amount": 9900},
            "12345678-1234-1234-1234-123456789abc") in calls
    assert calls[-1][0] == "record_resumeiq_pack_refund_v1"


def test_different_payment_provider_response_rejected(monkeypatch):
    monkeypatch.setattr(payments, "_supabase_rpc", lambda n, p: {
        "status": "requested", "payment_id": "pay_123",
        "idempotency_key": "12345678-1234-1234-1234-123456789abc"})
    monkeypatch.setattr(refunds, "_provider", lambda *a: {
        "id": "rfnd_123", "payment_id": "pay_attacker",
        "amount": 9900, "currency": "INR", "status": "processed"})
    with pytest.raises(HTTPException) as e:
        refunds.request_pack_refund("user-123", "order_123")
    assert e.value.status_code == 502


def test_pending_refund_status_reconciles(monkeypatch):
    calls = []
    def rpc(name, payload):
        calls.append(name)
        if name == "get_resumeiq_pack_refund_v1":
            return {"status": "pending", "payment_id": "pay_123",
                    "refund_id": "rfnd_123"}
        return "processed"
    monkeypatch.setattr(payments, "_supabase_rpc", rpc)
    monkeypatch.setattr(refunds, "_provider", lambda path: {
        "id": "rfnd_123", "payment_id": "pay_123",
        "amount": 9900, "currency": "INR", "status": "processed"})
    assert refunds.reconcile_pack_refund("user-123", "order_123") == {
        "status": "processed", "refund_id": "rfnd_123"}
    assert calls == ["get_resumeiq_pack_refund_v1", "record_resumeiq_pack_refund_v1"]


def test_unknown_gateway_result_stays_pending(monkeypatch):
    monkeypatch.setattr(payments, "_supabase_rpc", lambda n, p: {
        "status": "requested", "payment_id": "pay_123",
        "idempotency_key": "12345678-1234-1234-1234-123456789abc"})
    monkeypatch.setattr(refunds, "_provider", lambda *a: (_ for _ in ()).throw(HTTPException(502, "unknown")))
    with pytest.raises(HTTPException) as e:
        refunds.request_pack_refund("user-123", "order_123")
    assert e.value.status_code == 502
