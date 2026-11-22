# ResumeIQ: credit-enforcement development setup

> Development branch only. Do not merge/deploy to production before testing.

## 1. Initialize Supabase SQL
- Open Supabase Dashboard > SQL Editor > New query.
- Copy the contents of `backend/supabase-credit-functions.sql` into the query and run it.
- This creates an RLS-protected credit transaction ledger and three server-only RPC functions.
- The existing `public.user_credits` table and signup trigger are prerequisites.

## 2. Add **Render backend** environment variables
- `SUPABASE_URL`: your project's HTTPS URL (e.g. https://YOUR-PROJECT.supabase.co)
- `SUPABASE_PUBLISHABLE_KEY`: your `sb_publishable_...` key
- `SUPABASE_SECRET_KEY`: your **server-only** `sb_secret_...` key
- Keep `FRONTEND_ORIGIN` configured with the exact local and deployed origins.

Never add `SUPABASE_SECRET_KEY` to Vercel, `.env.local` under frontend, or GitHub source control. Only the backend may use it.

## 3. What the backend enforces
- Both `POST /api/analyze` and `POST /api/analyze/text` require a Supabase login token in `Authorization: Bearer ...`.
- A credit is reserved atomically before analysis and completed after success.
- If report generation fails, a refund is attempted (a failed network request can leave a pending reservation needing reconciliation).
- If the account balance is 0, the API returns HTTP 402.
- The legacy shared database history API endpoints and `save_analysis=true` are disabled until they support per-user ownership.
- React refreshes the credit counter after successful analysis.

## 4. Test before releasing
1. Deploy backend and frontend to a staging environment using this branch; don't change production's `main` deployment.
2. Sign up/log in with a dedicated test account that shows two credits.
3. Analyze a valid resume once: credits should show 1.
4. Analyze again: credits should show 0.
5. Third analysis should return 402 without producing a report.
6. Missing/expired token should return 401.
7. An invalid analysis should not permanently consume a credit.
8. Run parallel analysis calls to check the balance cannot go below zero.
9. Confirm that legacy saved-report endpoints do not expose stored reports.
10. Inspect `public.analysis_credit_transactions` for reservations left pending after test failures.

## 5. Important before accepting payments
- Add tests, controlled retry/idempotency, and automated reconciliation for reservations stuck in `reserved` if network connections are lost.
- Introduce a persistent user-owned analysis history schema with row-level access controls.
- Add rate limits, email verification policy, anti-abuse checks, privacy and retention controls, and payment webhook idempotency.
