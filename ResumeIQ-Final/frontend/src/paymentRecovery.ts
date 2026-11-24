/**
 * Checkout callbacks are not proof of payment. Recover through the authenticated
 * backend order-status endpoint, which checks ownership and the captured payment.
 * Never grant credits in the browser.
 */
export async function recoverCheckoutOrder(
  orderId: string,
  checkStatus: (id: string) => Promise<{ status: string }>,
  pause: (milliseconds: number) => Promise<void> = (milliseconds) =>
    new Promise<void>((resolve) => { setTimeout(resolve, milliseconds); }),
): Promise<boolean> {
  // The Razorpay webhook can arrive before or shortly after the Checkout callback.
  for (let attempt = 0; attempt < 4; attempt += 1) {
    try {
      const result = await checkStatus(orderId);
      if (result.status === "paid") return true;
    } catch {
      // Network or propagation delay: retry, but never assume the payment succeeded.
    }
    if (attempt < 3) await pause(1500);
  }
  return false;
}
