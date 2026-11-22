# ResumeIQ — Razorpay Live Mode rollout (NOT YET ACTIVATED)

The app now supports a **server-selected** Razorpay payment mode. This branch prepares a
live configuration but does **not** activate real payments, change Netlify, or alter Render.
Never put live key secrets in GitHub or a Vite environment variable.

## Important distinction

A Razorpay Payment Link being activated does not necessarily mean your own
website's Standard Checkout integration and live API credentials are approved.
Confirm website checkout access and live API keys in the Razorpay Dashboard.

## Configuration on the actual production Render backend

Use the existing FastAPI service only after testing its production deployment.
Set these via Render's **secret environment variable** controls:

- `RAZORPAY_MODE=live`
- `RAZORPAY_LIVE_ENABLED=true` **only after all checks below pass**
- `RAZORPAY_KEY_ID` — live ID beginning with `rzp_live_`
- `RAZORPAY_KEY_SECRET` — matching live API key secret
- `RAZORPAY_WEBHOOK_SECRET` — newly generated production webhook secret
- `SUPABASE_URL`, `SUPABASE_SECRET_KEY`, `SUPABASE_PUBLISHABLE_KEY` — verified
  production Supabase configuration; never mix test purchases with live funds.
- `FRONTEND_ORIGIN` — include only your actual approved production Netlify origin

The default code mode is `test` and requires matching `rzp_test_` credentials.
When `RAZORPAY_MODE=live`, requests fail closed unless both live credentials and
`RAZORPAY_LIVE_ENABLED=true` are provided. When switching modes, deploy a matching
frontend; its checkout now reads `GET /api/payments/config` and displays a real-payment
warning for live checkout. The order response includes the mode and is checked against
the UI's current mode before opening Razorpay.

## Mandatory readiness tasks before enabling live purchases

1. Razorpay confirms **live Payment Gateway API/website checkout** enabled, not only
   Payment Links. Obtain live keys directly from the dashboard.
2. Configure a production HTTPS webhook URL:
   `https://<PRODUCTION-RENDER-HOST>/api/payments/webhook`
   and subscribe to `payment.captured`. Use a different secret from Test Mode.
3. Verify callback HMAC, webhook HMAC, server-to-Razorpay payment capture status,
   order ownership, and amount/currency match.
4. Use a **production credit database with audited migration and recovery strategy**.
   The existing `credit_purchases` records do not distinguish test and live funds,
   so do not reuse an unreviewed test-payment database as a live purchase ledger.
5. Implement and test **per-purchase credit consumption tracking**. Current deductions
   draw from a shared balance, so eligibility for a wholly unused 5-credit pack cannot
   currently be reliably determined.
6. Implement refund processing/reconciliation, including credit reversal, unique
   refund records, partial/duplicate/chargeback reconciliation, and refund idempotency.
   Verify how to process legal refund requests before the first real charge.
7. Confirm legal-operator details, accurate Contact/Privacy/Terms/Refund/Delivery pages
   and purchase disclosures. Remove all **pre-launch draft** disclaimers only once
   policies accurately reflect the operating service.
8. Confirm payment failure, callback failure, webhook retry, pending status, double
   callback, unauthorized access, and cancellation behaviors.
9. Test in a controlled production environment with a deliberately authorized,
   small-value real transaction and verify funds, credits and reconciliation.
10. Monitor errors, securely maintain a support/refund workflow and decide when
   `RAZORPAY_LIVE_ENABLED=true` may be enabled.

## What this code does NOT do

- It does not create or upload your live API credentials.
- It does not configure Razorpay merchant activation, Render, Supabase, or Netlify.
- It does not yet implement purchase-level refund accounting or refund API calls.
- It does not make the existing staging service live.

References:
- https://razorpay.com/docs/payments/payment-gateway/web-integration/standard/
- https://razorpay.com/docs/payments/payment-gateway/test-and-live-mode/
- https://razorpay.com/docs/webhooks/
