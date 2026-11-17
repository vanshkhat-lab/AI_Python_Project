
import { useEffect, useState } from "react";
import { supabase } from "./supabase";

type CreditBalanceProps = {
  userId: string;
};

export default function CreditBalance({
  userId,
}: CreditBalanceProps) {
  const [balance, setBalance] = useState<number | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    async function loadCredits() {
      setBalance(null);
      setError("");

      const { data, error } = await supabase
        .from("user_credits")
        .select("balance")
        .eq("user_id", userId)
        .single();

      if (!active) return;

      if (error) {
        console.error("Credit loading error:", error);
        setError("Could not load credits");
        return;
      }

      setBalance(data.balance);
    }

    void loadCredits();

    const refreshCredits = () => { void loadCredits(); };
    window.addEventListener("resumeiq:credits-changed", refreshCredits);

    return () => {
      active = false;
      window.removeEventListener("resumeiq:credits-changed", refreshCredits);
    };
  }, [userId]);

  return (
    <div
      style={{
        padding: "12px 20px",
        margin: "12px",
        border: "1px solid #ddd",
        borderRadius: "10px",
      }}
    >
      <strong>ResumeIQ Credits</strong>
      <p>
        {error
          ? error
          : balance === null
          ? "Loading credits..."
          : `${balance} Credits Remaining`}
      </p>
    </div>
  );
}
