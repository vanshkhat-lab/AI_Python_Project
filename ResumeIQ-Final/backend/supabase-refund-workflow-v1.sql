-- ResumeIQ staging refund lifecycle (off by default at application layer).
-- Requires the existing purchase-ledger v2 schema.
BEGIN;
ALTER TABLE public.credit_purchases DROP CONSTRAINT IF EXISTS credit_purchases_status_check;
ALTER TABLE public.credit_purchases ADD CONSTRAINT credit_purchases_status_check CHECK (status IN ('created','paid','refund_pending','refunded'));
CREATE TABLE IF NOT EXISTS public.credit_refunds (
  purchase_id uuid PRIMARY KEY REFERENCES public.credit_purchases(id),
  user_id uuid NOT NULL REFERENCES auth.users(id),
  razorpay_payment_id text NOT NULL UNIQUE,
  razorpay_refund_id text UNIQUE,
  idempotency_key text NOT NULL UNIQUE DEFAULT gen_random_uuid()::text,
  amount_paise integer NOT NULL DEFAULT 9900 CHECK (amount_paise=9900),
  status text NOT NULL DEFAULT 'requested' CHECK (status IN ('requested','pending','processed','failed')),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE public.credit_refunds ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.credit_refunds FROM PUBLIC, anon, authenticated, service_role;
CREATE OR REPLACE FUNCTION public.get_resumeiq_pack_refund_v1(p_user_id uuid, p_order_id text)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
DECLARE
  v_record public.credit_refunds%ROWTYPE;
BEGIN
  SELECT r.* INTO v_record
  FROM public.credit_refunds r
  JOIN public.credit_purchases p ON p.id=r.purchase_id
  WHERE p.razorpay_order_id=p_order_id AND r.user_id=p_user_id;

  IF NOT FOUND THEN
    RETURN jsonb_build_object('status','not_found');
  END IF;
  RETURN jsonb_build_object(
    'status',v_record.status,
    'payment_id',v_record.razorpay_payment_id,
    'refund_id',v_record.razorpay_refund_id
  );
END;
$function$
;

CREATE OR REPLACE FUNCTION public.record_resumeiq_pack_refund_v1(p_payment_id text, p_refund_id text, p_status text, p_amount_paise integer, p_currency text)
 RETURNS text
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
DECLARE
  v_user UUID;
  v_refund public.credit_refunds%ROWTYPE;
  v_pack public.credit_purchases%ROWTYPE;
BEGIN
  IF p_payment_id IS NULL OR p_refund_id NOT LIKE 'rfnd_%'
     OR p_status NOT IN ('pending','processed','failed')
     OR p_amount_paise <> 9900 OR p_currency <> 'INR' THEN
    RAISE EXCEPTION 'Invalid provider refund details';
  END IF;

  SELECT user_id INTO v_user FROM public.credit_refunds
    WHERE razorpay_payment_id=p_payment_id;
  IF v_user IS NULL THEN RETURN 'unknown_payment'; END IF;

  PERFORM 1 FROM public.user_credits WHERE user_id=v_user FOR UPDATE;
  SELECT p.* INTO v_pack
    FROM public.credit_purchases p
    JOIN public.credit_refunds r ON p.id=r.purchase_id
    WHERE r.razorpay_payment_id=p_payment_id
    FOR UPDATE OF p;
  SELECT * INTO v_refund FROM public.credit_refunds
    WHERE razorpay_payment_id=p_payment_id FOR UPDATE;

  IF v_refund.razorpay_refund_id IS NOT NULL
     AND v_refund.razorpay_refund_id <> p_refund_id THEN
    RETURN 'conflicting_refund';
  END IF;

  IF v_refund.status IN ('processed','failed') THEN
    IF v_refund.status = p_status THEN RETURN 'already_'||p_status; END IF;
    RETURN 'terminal_status_conflict';
  END IF;

  IF v_pack.status <> 'refund_pending' THEN RETURN 'purchase_state_conflict'; END IF;

  UPDATE public.credit_refunds
    SET razorpay_refund_id=p_refund_id, status=p_status, updated_at=now()
    WHERE purchase_id=v_refund.purchase_id;

  IF p_status='processed' THEN
    UPDATE public.credit_purchases SET status='refunded'
      WHERE id=v_pack.id;
  ELSIF p_status='failed' THEN
    -- Provider-confirmed failure: restore pack exactly once. Refund cannot
    -- be attempted again automatically; refund ledger entry remains unique.
    UPDATE public.user_credits SET balance=balance+5 WHERE user_id=v_user;
    UPDATE public.credit_purchases
      SET status='paid', credits_available=5
      WHERE id=v_pack.id;
  END IF;
  RETURN p_status;
END;
$function$
;

CREATE OR REPLACE FUNCTION public.request_resumeiq_pack_refund_v1(p_user_id uuid, p_order_id text, p_mode text)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
DECLARE
  v_user UUID;
  v_balance INTEGER;
  v_pack public.credit_purchases%ROWTYPE;
  v_refund public.credit_refunds%ROWTYPE;
BEGIN
  IF p_user_id IS NULL OR p_order_id IS NULL
     OR p_mode NOT IN ('test','live') OR p_mode IS NULL THEN
    RAISE EXCEPTION 'Invalid refund request';
  END IF;

  SELECT user_id INTO v_user FROM public.credit_purchases
    WHERE razorpay_order_id = p_order_id;
  IF v_user IS DISTINCT FROM p_user_id THEN
    RETURN jsonb_build_object('status','ineligible','reason','order_not_found');
  END IF;

  -- Lock order: user's global balance, then pack, then refund record.
  SELECT balance INTO v_balance FROM public.user_credits
    WHERE user_id = p_user_id FOR UPDATE;
  IF v_balance IS NULL THEN
    RETURN jsonb_build_object('status','ineligible','reason','credit_account_missing');
  END IF;

  SELECT * INTO v_pack FROM public.credit_purchases
    WHERE razorpay_order_id = p_order_id AND user_id = p_user_id FOR UPDATE;
  SELECT * INTO v_refund FROM public.credit_refunds
    WHERE purchase_id=v_pack.id FOR UPDATE;
  IF FOUND THEN
    RETURN jsonb_build_object(
      'status',v_refund.status,
      'payment_id',v_refund.razorpay_payment_id,
      'refund_id',v_refund.razorpay_refund_id,
      'idempotency_key',v_refund.idempotency_key
    );
  END IF;

  IF v_pack.payment_mode IS DISTINCT FROM p_mode
     OR v_pack.status <> 'paid'
     OR v_pack.razorpay_payment_id IS NULL
     OR v_pack.amount_paise <> 9900 OR v_pack.currency <> 'INR'
     OR v_pack.credits <> 5 THEN
    RETURN jsonb_build_object('status','ineligible','reason','not_matching_paid_pack');
  END IF;
  IF v_pack.paid_at IS NULL
     OR v_pack.paid_at > now()
     OR v_pack.paid_at + interval '7 days' < now() THEN
    RETURN jsonb_build_object('status','ineligible','reason','outside_seven_days');
  END IF;
  IF v_pack.credits_available <> 5 OR v_balance < 5 THEN
    RETURN jsonb_build_object('status','ineligible','reason','credits_used_or_reserved');
  END IF;

  UPDATE public.user_credits SET balance = balance-5
    WHERE user_id=p_user_id AND balance>=5;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'Balance changed during refund reservation';
  END IF;
  UPDATE public.credit_purchases
    SET status='refund_pending', credits_available=0
    WHERE id=v_pack.id;

  INSERT INTO public.credit_refunds(purchase_id,user_id,razorpay_payment_id)
    VALUES(v_pack.id,p_user_id,v_pack.razorpay_payment_id)
    RETURNING * INTO v_refund;
  RETURN jsonb_build_object(
    'status','requested',
    'payment_id',v_refund.razorpay_payment_id,
    'refund_id',null,
    'idempotency_key',v_refund.idempotency_key
  );
END;
$function$
;

REVOKE ALL ON FUNCTION public.request_resumeiq_pack_refund_v1(uuid,text,text) FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.get_resumeiq_pack_refund_v1(uuid,text) FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.record_resumeiq_pack_refund_v1(text,text,text,integer,text) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.request_resumeiq_pack_refund_v1(uuid,text,text) TO service_role;
GRANT EXECUTE ON FUNCTION public.get_resumeiq_pack_refund_v1(uuid,text) TO service_role;
GRANT EXECUTE ON FUNCTION public.record_resumeiq_pack_refund_v1(text,text,text,integer,text) TO service_role;
COMMIT;
