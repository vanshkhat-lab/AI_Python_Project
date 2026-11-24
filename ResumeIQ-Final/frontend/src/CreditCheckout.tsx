import { useEffect, useState } from "react";
import {
  createCreditOrder,
  verifyCreditPayment,
  checkCreditPayment,
  getPaymentConfiguration,
} from "./api";
import type { PaymentConfiguration } from "./api";

type CheckoutResult = {
  razorpay_order_id: string;
  razorpay_payment_id: string;
  razorpay_signature: string;
};

type RazorpayOptions = {
  key: string;
  amount: number;
  currency: string;
  name: string;
  description: string;
  order_id: string;
  handler: (response: CheckoutResult) => void;
  modal: { ondismiss: () => void };
  theme: { color: string };
};

declare global {
  interface Window {
    Razorpay?: new (options: RazorpayOptions) => {
      open: () => void;
      on: (name: string, handler: (error: unknown) => void) => void;
    };
  }
}

function loadRazorpayCheckout(): Promise<void> {
  return new Promise((resolve, reject) => {
    if (window.Razorpay) {
      resolve();
      return;
    }
    const existing = document.querySelector<HTMLScriptElement>(
      'script[src="https://checkout.razorpay.com/v1/checkout.js"]',
    );
    if (existing) {
      existing.addEventListener("load", () => resolve(), { once: true });
      existing.addEventListener("error", () => reject(new Error("Could not load Razorpay.")), { once: true });
      return;
    }

    const script = document.createElement("script");
    script.src = "https://checkout.razorpay.com/v1/checkout.js";
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Could not load payment checkout."));
    document.head.appendChild(script);
  });
}

export default function CreditCheckout() {
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [pendingOrderId, setPendingOrderId] = useState("");
  const [configuration, setConfiguration] = useState<PaymentConfiguration | null>(null);

  useEffect(() => {
    let cancelled = false;
    getPaymentConfiguration().then((value) => {
      if (!cancelled) setConfiguration(value);
    }).catch(() => {
      if (!cancelled) setNotice("Payment checkout is unavailable. Try again later.");
    });
    return () => { cancelled = true; };
  }, []);

  async function startCheckout() {
    if (!configuration?.enabled) {
      setNotice("Payment checkout is not enabled.");
      return;
    }
    setBusy(true);
    setNotice("");
    try {
      await loadRazorpayCheckout();
      const order = await createCreditOrder();
      if (order.mode !== configuration.mode) throw new Error("Payment mode mismatch. Please refresh.");
      setPendingOrderId(order.order_id);
      if (!window.Razorpay) {
        throw new Error("Razorpay Checkout could not start.");
      }
      const checkout = new window.Razorpay({
        key: order.key_id,
        order_id: order.order_id,
        amount: order.amount,
        currency: order.currency,
        name: "ResumeIQ",
        description: order.mode === "live" ? "5 resume analysis credits" : "5 resume analysis credits — TEST MODE",
        theme: { color: "#1d7a4f" },
        modal: {
          ondismiss: () => {
            setBusy(false);
            setNotice("Checkout closed. No credits have been added unless payment was captured.");
          },
        },
        handler: (payment) => {
          void (async () => {
            try {
              setBusy(true);
              const result = await verifyCreditPayment(payment);
              setNotice(`Payment verified. ${result.credits_added} credits added to your account.`);
              setPendingOrderId("");
            } catch (error) {
              setNotice(error instanceof Error ? error.message : "Payment verification pending. Try Check purchase status.");
            } finally {
              setBusy(false);
            }
          })();
        },
      });
      checkout.on("payment.failed", () => {
        setNotice("Payment failed. No credits added.");
        setBusy(false);
      });
      checkout.open();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Unable to start checkout.");
      setBusy(false);
    }
  }

  async function checkStatus() {
    if (!pendingOrderId) return;
    setBusy(true);
    try {
      const status = await checkCreditPayment(pendingOrderId);
      if (status.status === "paid") {
        setNotice("Purchase confirmed. Your credit balance has been refreshed.");
        setPendingOrderId("");
      } else {
        setNotice("Purchase is still pending. If you completed payment, check again after confirmation.");
      }
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Could not check payment status.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section style={{
      margin: "12px",
      padding: "16px 20px",
      border: "1px solid #dfe8e2",
      borderRadius: 12,
      background: "#fff",
    }}>
      <h3 style={{ marginTop: 0 }}>ResumeIQ Credit Pack</h3>
      <p>Get 5 more resume analyses for ₹99 — one-time purchase.</p>
      {configuration?.mode === "test" && (
        <p style={{ color: "#965014", fontWeight: 600 }}>
          TEST MODE: This checkout does not collect real payments.
        </p>
      )}
      {!configuration?.enabled && (
        <p style={{ color: "#965014" }}>
          Checkout is unavailable until the payment service is configured.
        </p>
      )}
      <button type="button" disabled={busy || !configuration?.enabled} onClick={() => void startCheckout()}>
        {busy ? "Processing..." : configuration?.mode === "live" ? "Buy 5 Credits — ₹99" : "Buy 5 Credits — ₹99 (Test)"}
      </button>
      {pendingOrderId && (
        <button type="button" disabled={busy} onClick={() => void checkStatus()}
          style={{ marginLeft: 12 }}>
          Check purchase status
        </button>
      )}
      {notice && <p role="status" style={{ marginBottom: 0 }}>{notice}</p>}
    </section>
  );
}
