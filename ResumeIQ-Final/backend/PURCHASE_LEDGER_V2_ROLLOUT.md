# ResumeIQ: Purchase-credit ledger v2 — MIGRATION REQUIRED, NOT DEPLOYED

## Status

This branch adds opt-in purchase attribution for **new** five-credit packs.
It does not switch Render production settings, enable real payments, or create
Razorpay refunds. The live checkout gate stays closed unless all required
server flags and live credentials are present.

## Migration safety

1. Back up Supabase `user_credits`, `credit_purchases` and
   `analysis_credit_transactions`. Inspect existing rows and review any
   currently reserved credits / unfinished payment orders.
2. In **staging**, execute `backend/supabase-purchase-ledger-v2.sql` once
   with a privileged SQL Editor session. The migration adds:
   - `credit_purchases.payment_mode` (existing rows default to `legacy`);
   - `credit_purchases.credits_available` (existing rows default to zero);
   - `analysis_credit_transactions.purchase_id` (null for legacy deductions);
   - dedicated v2 purchase/credit RPCs and an internal eligibility check.
3. Do **not** backfill unknown purchases with `live`; they may be Test Mode
   payments. Existing free and untracked balances remain legacy, and the v2
   reserve operation spends these before new traceable packs.
4. Deploy matching backend to staging with
   `RESUMEIQ_LEDGER_V2_ENABLED=true`, `RAZORPAY_MODE=test`, and test keys.
   Test two free analyses, new purchases, multiple packs, parallel requests,
   successful analyses, failed analyses, webhook duplicates and status retries.
5. After verifying staging, prepare a **separate reconciled production migration**.
   Review historic credits; switch the v2 flag and backend in a controlled window.
   Until this is complete, keep `RAZORPAY_LIVE_ENABLED=false`.
6. Do not switch payment mode mid-checkout with outstanding orders. Freeze payment
   creation first, complete pending captures/reconciliation, then switch.
7. Keep the webhook secret private and never commit API keys, access tokens,
   personally identifiable data, or Supabase service keys.

## Important ledger semantics

- The existing global `user_credits.balance` remains authoritative for how
  many analyses are available.
- New successfully captured v2 orders increment both the global balance and the
  purchase's `credits_available` count **in one transaction**.
- v2 reservations lock the user's balance row to serialize credit operations.
  Once legacy/free balance is exhausted, the reservation selects the oldest
  available pack and records its ID against the analysis transaction.
- If an analysis fails before completion, its original pack credit is restored.
- Exactly-once captured-payment logic is preserved, scoped to a server-chosen
  `payment_mode`; repeated webhook/callbacks should never grant credits twice.
- The eligibility RPC **only reports eligibility for review**: a live purchase
  within seven calendar days, with all five purchased credits unused. It does
  not perform or authorize a Razorpay refund.

## Before the very first real ₹99 payment

**Still required (not implemented by this branch):**

- Implement a refund request and reconciliation procedure that atomically
  locks purchase+credit rows, reverses an approved unused pack only once,
  records Razorpay refund identifiers, and reconciles async success/failure.
- Add `refunded` / `refund_pending` states, dispute and chargeback handling,
  account support processes, audit trails and monitoring.
- Prevent credit consumption while the corresponding pack is being refunded;
  the existing unused-pack eligibility check alone is not sufficient.
- Separate or rigorously reconcile test and production database transactions.
- Review production privacy/terms/refund pages (current site has draft notices).
- Validate webhook delivery, Razorpay capture, order ownership, payment amount,
  duplicate detection, error recovery and storage policy.
- Run a controlled real-money end-to-end payment only after the above passes.

## Local unit tests (RPC mocked, not a substitute for database concurrency tests)

```shell
cd ResumeIQ-Final
python -m pytest backend/tests/test_purchase_ledger_v2.py -q
```

The unit tests verify server-side payment-mode gates and call routing, not live
Razorpay transactions or real Supabase transaction isolation.

## Enabling or disabling the new ledger

`RESUMEIQ_LEDGER_V2_ENABLED` defaults to false (existing behavior).
Set true only after the matching SQL migration is applied and tested. The Live
payment API refuses to open checkout when this flag is false.

**Do not set `RAZORPAY_LIVE_ENABLED=true` as a shortcut: that would allow
real charges before refund processing and production reconciliation exist.**
