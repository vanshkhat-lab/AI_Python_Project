import { describe, expect, it, vi } from "vitest";
import { recoverCheckoutOrder } from "./paymentRecovery";

describe("recoverCheckoutOrder", () => {
  it("recognizes a webhook-confirmed order without awarding credits client-side", async () => {
    const check = vi.fn().mockResolvedValue({ status: "paid" });
    const pause = vi.fn();
    expect(await recoverCheckoutOrder("order_123", check, pause)).toBe(true);
    expect(check).toHaveBeenCalledExactlyOnceWith("order_123");
    expect(pause).not.toHaveBeenCalled();
  });

  it("recovers a delayed payment when the second status check confirms it", async () => {
    const check = vi.fn()
      .mockResolvedValueOnce({ status: "created" })
      .mockResolvedValueOnce({ status: "paid" });
    const pause = vi.fn().mockResolvedValue(undefined);
    expect(await recoverCheckoutOrder("order_123", check, pause)).toBe(true);
    expect(check).toHaveBeenCalledTimes(2);
    expect(pause).toHaveBeenCalledExactlyOnceWith(1500);
  });

  it("keeps an uncaptured purchase pending instead of falsely confirming it", async () => {
    const check = vi.fn().mockResolvedValue({ status: "created" });
    const pause = vi.fn().mockResolvedValue(undefined);
    expect(await recoverCheckoutOrder("order_123", check, pause)).toBe(false);
    expect(check).toHaveBeenCalledTimes(4);
  });

  it("retries transient network errors without claiming success", async () => {
    const check = vi.fn().mockRejectedValue(new Error("temporarily offline"));
    const pause = vi.fn().mockResolvedValue(undefined);
    expect(await recoverCheckoutOrder("order_123", check, pause)).toBe(false);
    expect(check).toHaveBeenCalledTimes(4);
  });
});
