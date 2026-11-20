# ResumeIQ ₹99 / 5-credit Razorpay TEST checkout

**Do not enable live payments or merge to production until the steps below have passed.**
The checkout only accepts Razorpay keys beginning with `rzp_test_`.
The frontend has a visible TEST MODE label.

## 1. Database
Supabase Dashboard → SQL Editor → New Query:
1. Run `backend/supabase-credit-functions.sql` if not already installed.
2. Run `backend/supabase-payment-functions.sql` **once** on your existing ResumeIQ Supabase project.
3. Confirm that `public.credit_purchases` exists and Row Level Security is enabled.

The order table records each Razorpay order, its authenticated Supabase user, 9,900 paise, INR, and 5 credits. Browser users can only SELECT their own purchases. Backend-only Postgres functions add credits in the same transaction as changing order status from `created` to `paid`. Duplicate callbacks for the same payment do not grant credits again.

## 2. Backend / Render staging environment
Keep these variables:
- `SUPABASE_URL`
- `SUPABASE_PUBLISHABLE_KEY`
- `SUPABASE_SECRET_KEY` (backend only)
- `FRONTEND_ORIGIN` includes `https://airesumeiq4u.netlify.app`

Add these variables to the **staging backend only**:
- `RAZORPAY_KEY_ID` — Razorpay **test** Key ID `rzp_test_...`
- `RAZORPAY_KEY_SECRET` — Razorpay **test** Key Secret
- `RAZORPAY_WEBHOOK_SECRET` — choose a **new random secret**, separate from your API Key Secret. Use the same value in the Razorpay Test Mode webhook configuration.

Never put these secrets into GitHub, Netlify, or the React bundle.

## 3. Razorpay Test Mode webhook
In Razorpay Test Mode, create a webhook with:
- URL: `https://resumeiq-backend-staging-hcld.onrender.com/api/payments/webhook`
- Event: `payment.captured`
- Secret: the same private value as `RAZORPAY_WEBHOOK_SECRET` on Render

The server verifies `X-Razorpay-Signature` against the raw request body before honoring the event. It independently retrieves the captured payment from Razorpay and checks the saved order amount, currency and ownership. Events for unrelated orders cannot grant credits.

Webhook registration can be done after an initial checkout test, but **configure it before any public/live release**. If a checkout callback is missed, the `Check purchase status` button also reconciles captured payments with Razorpay.

## 4. Frontend
Netlify imports GitHub branch `feature/credit-enforcement`.
Its `VITE_API_BASE_URL` should point to:
`https://resumeiq-backend-staging-hcld.onrender.com`

Netlify frontend needs only Supabase publishable URL/key and API base URL. Razorpay Key ID is returned by FastAPI for each order; no Razorpay secret is ever sent to the browser.

## 5. Test plan
1. Open `https://airesumeiq4u.netlify.app/` in a private browser, sign in.
2. Verify that the "Buy 5 Credits — ₹99 (Test)" button appears.
3. Choose test payment methods/test instruments permitted by Razorpay's Test Mode documentation. Never use real payments for this stage.
4. Upon successful captured payment, confirm credits increase by exactly **5** in Supabase `user_credits`.
5. Press "Check purchase status" after a successful or interrupted payment. It must never add 5 credits twice.
6. Failed / dismissed checkout must not grant credits.
7. Attempt to use another user's order ID while signed in—status and verification must be denied.
8. Verify `public.credit_purchases` has one `paid` row with the Razorpay payment ID.
9. Check the Razorpay Test webhook delivery log (after enabling the webhook).
10. Check payment API errors and bank/transaction state in the Test Dashboard.

**Before live payments:** move to production-grade hosting, add legal/policy pages, secure user-owned report history, tune abuse limits, handle refunds/chargebacks and pending-order reconciliation, complete merchant verification and switch keys in an explicitly separate live rollout.
