"""Unit tests for opting in to the purchase-attributed credit ledger.

Run from ResumeIQ-Final with: python -m pytest backend/tests/test_purchase_ledger_v2.py
These tests mock RPCs and do not exercise the actual Supabase migration.
"""
import pytest
from fastapi import HTTPException

from backend.resumeiq import credits, payments


def _base_payment_settings(monkeypatch):
    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_live_example")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", "not-a-real-secret")
    monkeypatch.setenv("RAZORPAY_WEBHOOK_SECRET", "not-a-real-webhook-secret")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "not-a-real-supabase-secret")


def test_live_checkout_requires_v2_even_if_live_flag_enabled(monkeypatch):
    _base_payment_settings(monkeypatch)
    monkeypatch.setenv("RAZORPAY_MODE", "live")
    monkeypatch.setenv("RAZORPAY_LIVE_ENABLED", "true")
    monkeypatch.delenv("RESUMEIQ_LEDGER_V2_ENABLED", raising=False)
    assert payments.checkout_config() == {"mode": "live", "enabled": False}
    with pytest.raises(HTTPException) as exc:
        payments._env()
    assert exc.value.status_code == 503


def test_live_checkout_ready_only_when_ledger_and_credentials_present(monkeypatch):
    _base_payment_settings(monkeypatch)
    monkeypatch.setenv("RAZORPAY_MODE", "live")
    monkeypatch.setenv("RAZORPAY_LIVE_ENABLED", "true")
    monkeypatch.setenv("RESUMEIQ_LEDGER_V2_ENABLED", "true")
    assert payments.checkout_config() == {"mode": "live", "enabled": True}


def test_test_mode_remains_available_with_old_ledger(monkeypatch):
    _base_payment_settings(monkeypatch)
    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_test_example")
    monkeypatch.setenv("RAZORPAY_MODE", "test")
    monkeypatch.setenv("RAZORPAY_LIVE_ENABLED", "false")
    monkeypatch.delenv("RESUMEIQ_LEDGER_V2_ENABLED", raising=False)
    assert payments.checkout_config() == {"mode": "test", "enabled": True}


def test_credit_reservation_routes_to_v2_when_enabled(monkeypatch):
    requests = []

    def fake_rpc(name, user_id, request_id):
        requests.append((name, user_id, request_id))
        return 2

    monkeypatch.setattr(credits, "_rpc", fake_rpc)
    monkeypatch.setenv("RESUMEIQ_LEDGER_V2_ENABLED", "true")
    credits.reserve_credit("user-123")
    assert requests[0][0] == "reserve_analysis_credit_v2"

    monkeypatch.setenv("RESUMEIQ_LEDGER_V2_ENABLED", "false")
    credits.reserve_credit("user-123")
    assert requests[1][0] == "reserve_analysis_credit"


def test_credit_failed_analysis_restores_correct_rpc(monkeypatch):
    requests = []

    def fake_rpc(name, user_id, request_id):
        requests.append(name)
        return True

    monkeypatch.setattr(credits, "_rpc", fake_rpc)
    monkeypatch.setenv("RESUMEIQ_LEDGER_V2_ENABLED", "true")
    credits.refund_credit("user-123", "request-123")
    assert requests == ["refund_analysis_credit_v2"]


def test_v2_order_records_server_mode(monkeypatch):
    monkeypatch.setenv("RESUMEIQ_LEDGER_V2_ENABLED", "true")
    monkeypatch.setenv("RAZORPAY_MODE", "live")
    monkeypatch.setattr(payments, "_env", lambda: ("rzp_live_fake", "secret", "https://example.supabase.co", "secret", "webhook"))
    monkeypatch.setattr(payments, "_razorpay", lambda *args: {
        "id": "order_123", "amount": 9900, "currency": "INR"
    })
    calls = []
    def fake_rpc(name, payload):
        calls.append((name, payload))
        return True
    monkeypatch.setattr(payments, "_supabase_rpc", fake_rpc)
    result = payments.create_order("user-123")
    assert result["mode"] == "live"
    assert calls[0][0] == "register_resumeiq_credit_order_v2"
    assert calls[0][1]["p_payment_mode"] == "live"


def test_v2_payment_crediting_is_server_mode_bound(monkeypatch):
    monkeypatch.setenv("RESUMEIQ_LEDGER_V2_ENABLED", "true")
    monkeypatch.setenv("RAZORPAY_MODE", "live")
    monkeypatch.setattr(payments, "_purchase", lambda order_id: {
        "user_id": "user-123", "amount_paise": 9900, "currency": "INR", "credits": 5,
    })
    monkeypatch.setattr(payments, "_verified_capture", lambda order, payment: None)
    calls = []
    def fake_rpc(name, payload):
        calls.append((name, payload))
        return "credited"
    monkeypatch.setattr(payments, "_supabase_rpc", fake_rpc)
    result = payments._grant_captured("order_123", "pay_123", "user-123")
    assert result["credits_added"] == 5
    assert calls == [("apply_resumeiq_credit_payment_v2", {
        "p_order_id": "order_123", "p_payment_id": "pay_123", "p_payment_mode": "live"
    })]
