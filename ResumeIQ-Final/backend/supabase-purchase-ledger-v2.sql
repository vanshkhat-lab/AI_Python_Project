-- ResumeIQ: purchase-aware credit ledger (staging migration; NOT YET APPLIED).
-- Additive migration: leaves legacy balances and test purchases untouched.
-- Apply in a supervised Supabase SQL Editor session after backup and tests.
-- Deployment requires matching backend release. Existing v1 RPCs are retained for rollback.
--
-- Existing, untraceable credits are treated as legacy/free credits.
-- A legacy purchase is never assumed to be a refundable live purchase.

BEGIN;

ALTER TABLE public.credit_purchases
  ADD COLUMN IF NOT EXISTS payment_mode TEXT NOT NULL DEFAULT 'legacy';

ALTER TABLE public.credit_purchases
  ADD COLUMN IF NOT EXISTS credits_available INTEGER NOT NULL DEFAULT 0;

ALTER TABLE public.analysis_credit_transactions
  ADD COLUMN IF NOT EXISTS purchase_id UUID REFERENCES public.credit_purchases(id);

DO $do$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid = 'public.credit_purchases'::regclass
      AND conname = 'credit_purchases_mode_valid'
  ) THEN
    ALTER TABLE public.credit_purchases
      ADD CONSTRAINT credit_purchases_mode_valid
      CHECK (payment_mode IN ('legacy','test','live'));
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid = 'public.credit_purchases'::regclass
      AND conname = 'credit_purchases_available_valid'
  ) THEN
    ALTER TABLE public.credit_purchases
      ADD CONSTRAINT credit_purchases_available_valid
      CHECK (credits_available BETWEEN 0 AND credits);
  END IF;
END
$do$;

CREATE INDEX IF NOT EXISTS credit_purchases_usable_idx
  ON public.credit_purchases (user_id, paid_at, id)
  WHERE status = 'paid' AND credits_available > 0;

CREATE INDEX IF NOT EXISTS analysis_credit_transactions_purchase_idx
  ON public.analysis_credit_transactions (purchase_id)
  WHERE purchase_id IS NOT NULL;

-- No browser role is allowed to invoke privileged ledger RPCs.
-- The backend provides the mode from RAZORPAY_MODE (not the checkout client).
CREATE OR REPLACE FUNCTION public.register_resumeiq_credit_order_v2(
    p_user_id UUID,
    p_order_id TEXT,
    p_amount_paise INTEGER,
    p_currency TEXT,
    p_credits INTEGER,
    p_payment_mode TEXT
)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
BEGIN
    IF p_amount_paise <> 9900 OR p_currency <> 'INR' OR p_credits <> 5
       OR p_order_id IS NULL OR p_order_id NOT LIKE 'order_%'
       OR p_payment_mode NOT IN ('test', 'live') OR p_payment_mode IS NULL
    THEN
        RAISE EXCEPTION 'Invalid ResumeIQ credit package';
    END IF;

    INSERT INTO public.credit_purchases
        (user_id, razorpay_order_id, amount_paise, currency, credits, payment_mode)
    VALUES
        (p_user_id, p_order_id, p_amount_paise, p_currency, p_credits, p_payment_mode);

    RETURN TRUE;
END;
$$;

-- Lock order: user_credits first, then credit_purchases. This matches analysis
-- reservation order and prevents purchase/deduction deadlocks on one account.
CREATE OR REPLACE FUNCTION public.apply_resumeiq_credit_payment_v2(
    p_order_id TEXT,
    p_payment_id TEXT,
    p_payment_mode TEXT
)
RETURNS TEXT
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
    v_user_id UUID;
    v_purchase public.credit_purchases%ROWTYPE;
BEGIN
    IF p_order_id IS NULL OR p_order_id NOT LIKE 'order_%'
       OR p_payment_id IS NULL OR p_payment_id NOT LIKE 'pay_%'
       OR p_payment_mode NOT IN ('test','live') OR p_payment_mode IS NULL
    THEN
        RAISE EXCEPTION 'Invalid payment identifiers or mode';
    END IF;

    SELECT user_id INTO v_user_id
      FROM public.credit_purchases
     WHERE razorpay_order_id = p_order_id;

    IF v_user_id IS NULL THEN
        RETURN 'unknown_or_conflicting_order';
    END IF;

    PERFORM 1 FROM public.user_credits WHERE user_id = v_user_id FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'User credit account is missing';
    END IF;

    SELECT * INTO v_purchase
      FROM public.credit_purchases
     WHERE razorpay_order_id = p_order_id
     FOR UPDATE;

    IF v_purchase.payment_mode <> p_payment_mode
       OR v_purchase.amount_paise <> 9900
       OR v_purchase.currency <> 'INR'
       OR v_purchase.credits <> 5
    THEN
        RETURN 'unknown_or_conflicting_order';
    END IF;

    IF v_purchase.status = 'paid'
       AND v_purchase.razorpay_payment_id = p_payment_id
    THEN
        RETURN 'already_credited';
    END IF;

    IF v_purchase.status <> 'created' THEN
        RETURN 'unknown_or_conflicting_order';
    END IF;

    UPDATE public.credit_purchases
       SET status = 'paid',
           razorpay_payment_id = p_payment_id,
           paid_at = NOW(),
           credits_available = 5
     WHERE id = v_purchase.id;

    UPDATE public.user_credits
       SET balance = balance + 5
     WHERE user_id = v_user_id;

    RETURN 'credited';
END;
$$;

-- Preserve free/legacy credits first. On a purchased-credit reservation,
-- atomically record the source pack and decrement its available count.
CREATE OR REPLACE FUNCTION public.reserve_analysis_credit_v2(
    p_user_id UUID,
    p_request_id UUID
)
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
    v_balance INTEGER;
    v_paid_available BIGINT;
    v_purchase_id UUID;
BEGIN
    SELECT balance INTO v_balance
      FROM public.user_credits
     WHERE user_id = p_user_id
     FOR UPDATE;

    IF v_balance IS NULL OR v_balance <= 0 THEN
        RETURN -1;
    END IF;

    SELECT COALESCE(SUM(credits_available), 0) INTO v_paid_available
      FROM public.credit_purchases
     WHERE user_id = p_user_id
       AND status = 'paid'
       AND payment_mode IN ('test','live');

    IF v_paid_available > v_balance THEN
        RAISE EXCEPTION 'Credit ledger mismatch; reconciliation required';
    END IF;

    IF v_paid_available = v_balance THEN
        SELECT id INTO v_purchase_id
          FROM public.credit_purchases
         WHERE user_id = p_user_id
           AND status = 'paid'
           AND payment_mode IN ('test','live')
           AND credits_available > 0
         ORDER BY paid_at ASC, id ASC
         LIMIT 1
         FOR UPDATE;

        IF v_purchase_id IS NULL THEN
            RAISE EXCEPTION 'Purchase credit source is missing';
        END IF;

        UPDATE public.credit_purchases
           SET credits_available = credits_available - 1
         WHERE id = v_purchase_id
           AND credits_available > 0;

        IF NOT FOUND THEN
            RAISE EXCEPTION 'Credit reservation conflict';
        END IF;
    END IF;

    UPDATE public.user_credits
       SET balance = balance - 1
     WHERE user_id = p_user_id
       AND balance > 0
     RETURNING balance INTO v_balance;

    IF v_balance IS NULL THEN
        RAISE EXCEPTION 'Credit reservation balance conflict';
    END IF;

    INSERT INTO public.analysis_credit_transactions
       (id, user_id, status, purchase_id)
    VALUES
       (p_request_id, p_user_id, 'reserved', v_purchase_id);

    RETURN v_balance;
END;
$$;

-- Roll back a failed analysis to the same purchased pack (if applicable).
-- Existing complete_analysis_credit remains compatible and finalizes consumption.
CREATE OR REPLACE FUNCTION public.refund_analysis_credit_v2(
    p_user_id UUID,
    p_request_id UUID
)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
    v_purchase_id UUID;
BEGIN
    PERFORM 1 FROM public.user_credits
     WHERE user_id = p_user_id
     FOR UPDATE;

    IF NOT FOUND THEN
        RETURN FALSE;
    END IF;

    SELECT purchase_id INTO v_purchase_id
      FROM public.analysis_credit_transactions
     WHERE id = p_request_id
       AND user_id = p_user_id
       AND status = 'reserved'
     FOR UPDATE;

    IF NOT FOUND THEN
        RETURN FALSE;
    END IF;

    IF v_purchase_id IS NOT NULL THEN
        UPDATE public.credit_purchases
           SET credits_available = credits_available + 1
         WHERE id = v_purchase_id
           AND user_id = p_user_id
           AND status = 'paid'
           AND credits_available < credits;
        IF NOT FOUND THEN
            RAISE EXCEPTION 'Could not restore the original purchase credit';
        END IF;
    END IF;

    UPDATE public.analysis_credit_transactions
       SET status = 'refunded',
           updated_at = NOW()
     WHERE id = p_request_id
       AND user_id = p_user_id
       AND status = 'reserved';

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Credit transaction changed during rollback';
    END IF;

    UPDATE public.user_credits
       SET balance = balance + 1
     WHERE user_id = p_user_id;

    RETURN TRUE;
END;
$$;

-- For a private/manual refund review only; does not issue or authorize refunds.
-- Legacy and test-mode purchases are NEVER considered live-money eligible.
CREATE OR REPLACE FUNCTION public.resumeiq_unused_pack_eligibility_v2(
    p_order_id TEXT
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
    v_purchase public.credit_purchases%ROWTYPE;
BEGIN
    SELECT * INTO v_purchase
      FROM public.credit_purchases
     WHERE razorpay_order_id = p_order_id;

    IF NOT FOUND THEN
        RETURN jsonb_build_object('eligible', false, 'reason', 'unknown_order');
    ELSIF v_purchase.payment_mode <> 'live' THEN
        RETURN jsonb_build_object('eligible', false, 'reason', 'not_a_live_purchase');
    ELSIF v_purchase.status <> 'paid' THEN
        RETURN jsonb_build_object('eligible', false, 'reason', 'not_paid');
    ELSIF v_purchase.paid_at IS NULL OR
          v_purchase.paid_at + INTERVAL '7 days' < NOW() THEN
        RETURN jsonb_build_object('eligible', false, 'reason', 'outside_seven_days');
    ELSIF v_purchase.credits_available <> v_purchase.credits THEN
        RETURN jsonb_build_object('eligible', false, 'reason', 'pack_not_wholly_unused');
    END IF;

    RETURN jsonb_build_object('eligible', true, 'reason', 'wholly_unused_within_seven_days');
END;
$$;

REVOKE ALL ON FUNCTION public.register_resumeiq_credit_order_v2(UUID,TEXT,INTEGER,TEXT,INTEGER,TEXT) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.apply_resumeiq_credit_payment_v2(TEXT,TEXT,TEXT) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.reserve_analysis_credit_v2(UUID,UUID) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.refund_analysis_credit_v2(UUID,UUID) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.resumeiq_unused_pack_eligibility_v2(TEXT) FROM PUBLIC, anon, authenticated;

GRANT EXECUTE ON FUNCTION public.register_resumeiq_credit_order_v2(UUID,TEXT,INTEGER,TEXT,INTEGER,TEXT) TO service_role;
GRANT EXECUTE ON FUNCTION public.apply_resumeiq_credit_payment_v2(TEXT,TEXT,TEXT) TO service_role;
GRANT EXECUTE ON FUNCTION public.reserve_analysis_credit_v2(UUID,UUID) TO service_role;
GRANT EXECUTE ON FUNCTION public.refund_analysis_credit_v2(UUID,UUID) TO service_role;
GRANT EXECUTE ON FUNCTION public.resumeiq_unused_pack_eligibility_v2(TEXT) TO service_role;

COMMIT;
