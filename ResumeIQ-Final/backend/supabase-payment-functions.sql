-- ResumeIQ Razorpay test-checkout database migration.
-- Run in Supabase SQL Editor before deploying payment endpoints.
-- Requires public.user_credits already created.
-- All credit grants must originate from the trusted FastAPI backend, never the browser.

CREATE TABLE IF NOT EXISTS public.credit_purchases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    razorpay_order_id TEXT NOT NULL UNIQUE,
    razorpay_payment_id TEXT UNIQUE,
    amount_paise INTEGER NOT NULL CHECK (amount_paise = 9900),
    currency TEXT NOT NULL CHECK (currency = 'INR'),
    credits INTEGER NOT NULL CHECK (credits = 5),
    status TEXT NOT NULL DEFAULT 'created' CHECK (status IN ('created', 'paid')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    paid_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS credit_purchases_user_time_idx
ON public.credit_purchases(user_id, created_at DESC);

ALTER TABLE public.credit_purchases ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.credit_purchases FROM PUBLIC, anon, authenticated;
GRANT SELECT ON TABLE public.credit_purchases TO authenticated;

DROP POLICY IF EXISTS "Users view own purchases" ON public.credit_purchases;

CREATE POLICY "Users view own purchases"
    ON public.credit_purchases
    FOR SELECT TO authenticated
    USING ((SELECT auth.uid()) = user_id);

-- Called only by the backend, after Razorpay creates the order.
CREATE OR REPLACE FUNCTION public.register_resumeiq_credit_order(
    p_user_id UUID,
    p_order_id TEXT,
    p_amount_paise INTEGER,
    p_currency TEXT,
    p_credits INTEGER
)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
BEGIN
    IF p_amount_paise <> 9900 OR p_currency <> 'INR' OR p_credits <> 5
       OR p_order_id IS NULL OR p_order_id NOT LIKE 'order_%'
    THEN
        RAISE EXCEPTION 'Invalid ResumeIQ credit package';
    END IF;

    INSERT INTO public.credit_purchases
        (user_id, razorpay_order_id, amount_paise, currency, credits)
    VALUES (p_user_id, p_order_id, p_amount_paise, p_currency, p_credits);

    RETURN TRUE;
END;
$$;

-- Exactly-once granting: mark the order paid and add credits in one transaction.
-- A second callback/webhook for the same payment returns already_credited.
CREATE OR REPLACE FUNCTION public.apply_resumeiq_credit_payment(
    p_order_id TEXT,
    p_payment_id TEXT
)
RETURNS TEXT
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
    v_user_id UUID;
    v_status TEXT;
    v_payment_id TEXT;
BEGIN
    IF p_payment_id IS NULL OR p_payment_id NOT LIKE 'pay_%'
       OR p_order_id IS NULL OR p_order_id NOT LIKE 'order_%'
    THEN
        RAISE EXCEPTION 'Invalid payment identifier';
    END IF;

    UPDATE public.credit_purchases
       SET status = 'paid',
           razorpay_payment_id = p_payment_id,
           paid_at = now()
     WHERE razorpay_order_id = p_order_id AND status = 'created'
     RETURNING user_id INTO v_user_id;

    IF v_user_id IS NOT NULL THEN
        UPDATE public.user_credits
           SET balance = balance + 5
         WHERE user_id = v_user_id;

        IF NOT FOUND THEN
            RAISE EXCEPTION 'User credit account is missing';
        END IF;

        RETURN 'credited';
    END IF;

    SELECT status, razorpay_payment_id
      INTO v_status, v_payment_id
      FROM public.credit_purchases
     WHERE razorpay_order_id = p_order_id;

    IF v_status = 'paid' AND v_payment_id = p_payment_id THEN
        RETURN 'already_credited';
    END IF;

    RETURN 'unknown_or_conflicting_order';
END;
$$;

REVOKE ALL ON FUNCTION public.register_resumeiq_credit_order(UUID, TEXT, INTEGER, TEXT, INTEGER)
  FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.apply_resumeiq_credit_payment(TEXT, TEXT)
  FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.register_resumeiq_credit_order(UUID, TEXT, INTEGER, TEXT, INTEGER)
  TO service_role;
GRANT EXECUTE ON FUNCTION public.apply_resumeiq_credit_payment(TEXT, TEXT)
  TO service_role;
