# ResumeIQ Refund Workflow — staging only

## Scope and status
This branch implements a **feature-gated** refund request and reconciliation path for an entirely unused, paid, five-credit pack within seven calendar days. It does **not** activate a real-money payment gateway or enable refunds on Render or Netlify.

Migration: `backend/supabase-refund-workflow-v1.sql` was applied to **ResumeIQ-Staging only**. The production Supabase database and original Netlify website have not been changed.

## Safety model
- Backend verifies Supabase user token; database RPC checks that the requested order belongs to that user.
- Database locks the credit balance and original pack before holding five credits. The pack cannot be spent while refund is pending.
- One refund row per original purchase, unique Razorpay payment/refund IDs and a stable idempotency key.
- Razorpay `POST /v1/payments/{payment_id}/refund` uses `X-Refund-Idempotency` and the identical amount payload for retries.
- For unknown network results, credits remain held until the provider state is reconciled. Never issue a new refund with another key.
- `refund.created`, `refund.processed`, and `refund.failed` webhooks require the existing HMAC verification, then independently fetch the refund from Razorpay before database reconciliation.
- Refund failure restores all five credits only once; successful refunds permanently consume them. A failed refund remains recorded and requires manual support if another attempt is necessary.
- `credit_refunds` is not exposed to browser roles; privileged RPCs are backend-only. RLS is enabled and deliberately has no browser policies.
- Existing legacy/test purchase records cannot be claimed as real-money refunds.
- Only server-selected `RAZORPAY_MODE` is accepted.

## Before enabling anything
1. Deploy this branch to a **separate staging Render service** connected only to **ResumeIQ-Staging**, never to the original site's Supabase keys.
2. Keep `RAZORPAY_LIVE_ENABLED=false` and `RESUMEIQ_REFUNDS_ENABLED=false` during setup.
3. Configure test-key `RAZORPAY_MODE=test`, `RESUMEIQ_LEDGER_V2_ENABLED=true` and the staging webhook for `payment.captured`, `refund.created`, `refund.processed`, `refund.failed`.
4. Run `python -m pytest backend/tests/test_refund_workflow_v1.py -q` from `ResumeIQ-Final`.
5. Only when deliberate **test-mode** refund checks are authorized, temporarily set `RESUMEIQ_REFUNDS_ENABLED=true` on the staging backend. Turning this flag off blocks **new** refund requests; existing refunds can still be reconciled by GET or webhook.
6. Confirm a test-mode captured payment is eligible, unused; verify credit hold, a single provider refund, repeated requests with the same idempotency key, asynchronous status and failure recovery.
7. Audit legal refund terms, merchant approval, real support processes, test/live separation, webhook reliability, exception logging, monitoring, and production reconciliation before considering any live enablement.

## Backend routes
- `POST /api/payments/refunds/{order_id}`: request refund of the signed-in user's pack (disabled unless flag enabled).
- `GET /api/payments/refunds/{order_id}`: reconcile the existing request; never creates a new refund.
- Existing `POST /api/payments/webhook` additionally processes supported signed refund webhooks.

## Safety caveats
- Customer-initiated requests issue refunds **automatically** if enabled and eligible. The feature flag should remain off until the merchant explicitly approves this business process and operations are staffed.
- Webhook delivery and reconciliation should be monitored; a network failure can leave the pack in `refund_pending` until reviewed.
- A provider-reported refund `failed` restores credits, but automatically starting a second refund is deliberately forbidden.
- These staging SQL checks used synthetic users and rollback; they are **not** a substitute for real Razorpay test-mode or concurrency tests.
