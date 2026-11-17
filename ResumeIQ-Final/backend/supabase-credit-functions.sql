-- ResumeIQ credit accounting.
-- Run once in Supabase > SQL Editor before deploying the backend changes.
-- Only the server-side service_role is allowed to invoke these functions.

CREATE TABLE IF NOT EXISTS public.analysis_credit_transactions (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  status TEXT NOT NULL CHECK (status IN ('reserved', 'completed', 'refunded')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS analysis_credit_transactions_user_id_idx
  ON public.analysis_credit_transactions (user_id, created_at DESC);

ALTER TABLE public.analysis_credit_transactions ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.analysis_credit_transactions FROM PUBLIC, anon, authenticated;
GRANT SELECT ON TABLE public.analysis_credit_transactions TO authenticated;

DROP POLICY IF EXISTS "Users may view own credit transactions"
  ON public.analysis_credit_transactions;

CREATE POLICY "Users may view own credit transactions"
  ON public.analysis_credit_transactions
  FOR SELECT TO authenticated
  USING ((SELECT auth.uid()) = user_id);

CREATE OR REPLACE FUNCTION public.reserve_analysis_credit(
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
BEGIN
  UPDATE public.user_credits
  SET balance = balance - 1
  WHERE user_id = p_user_id AND balance > 0
  RETURNING balance INTO v_balance;

  IF v_balance IS NULL THEN
    RETURN -1;
  END IF;

  INSERT INTO public.analysis_credit_transactions(id, user_id, status)
  VALUES (p_request_id, p_user_id, 'reserved');

  RETURN v_balance;
END;
$$;

CREATE OR REPLACE FUNCTION public.complete_analysis_credit(
  p_user_id UUID,
  p_request_id UUID
)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
BEGIN
  UPDATE public.analysis_credit_transactions
  SET status = 'completed', updated_at = NOW()
  WHERE id = p_request_id AND user_id = p_user_id AND status = 'reserved';

  RETURN FOUND;
END;
$$;

CREATE OR REPLACE FUNCTION public.refund_analysis_credit(
  p_user_id UUID,
  p_request_id UUID
)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
BEGIN
  UPDATE public.analysis_credit_transactions
  SET status = 'refunded', updated_at = NOW()
  WHERE id = p_request_id AND user_id = p_user_id AND status = 'reserved';

  IF NOT FOUND THEN
    RETURN FALSE;
  END IF;

  UPDATE public.user_credits
  SET balance = balance + 1
  WHERE user_id = p_user_id;

  RETURN TRUE;
END;
$$;

REVOKE ALL ON FUNCTION public.reserve_analysis_credit(UUID, UUID) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.complete_analysis_credit(UUID, UUID) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.refund_analysis_credit(UUID, UUID) FROM PUBLIC, anon, authenticated;

GRANT EXECUTE ON FUNCTION public.reserve_analysis_credit(UUID, UUID) TO service_role;
GRANT EXECUTE ON FUNCTION public.complete_analysis_credit(UUID, UUID) TO service_role;
GRANT EXECUTE ON FUNCTION public.refund_analysis_credit(UUID, UUID) TO service_role;
