import CreditBalance from "./CreditBalance";
import CreditCheckout from "./CreditCheckout";
import LandingPage from "./LandingPage";
import LegalPage, { getLegalRoute, LegalLinks } from "./LegalPages";
import { useEffect, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import type { Session } from "@supabase/supabase-js";
import { supabase } from "./supabase";

export default function AuthGate({
  children,
}: {
  children: ReactNode;
}) {
  const [session, setSession] = useState<Session | null>(null);
  const [checking, setChecking] = useState(true);
  const [mode, setMode] = useState<"login" | "signup">("signup");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session);
      setChecking(false);
    }).catch(() => setChecking(false));

    const { data: { subscription } } =
      supabase.auth.onAuthStateChange((_event, nextSession) => {
        setSession(nextSession);
        setChecking(false);
      });

    return () => subscription.unsubscribe();
  }, []);

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setMessage("");

    try {
      if (mode === "signup") {
        const { data, error } = await supabase.auth.signUp({
          email,
          password,
          options: {
            emailRedirectTo: window.location.origin,
          },
        });

        if (error) throw error;

        if (!data.session) {
          setMessage("Check your email to confirm your account.");
        }
      } else {
        const { error } =
          await supabase.auth.signInWithPassword({
            email,
            password,
          });

        if (error) throw error;
      }
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : "Authentication failed"
      );
    } finally {
      setBusy(false);
    }
  }

  const legalRoute = getLegalRoute(window.location.pathname);
  if (legalRoute) {
    return <LegalPage kind={legalRoute} />;
  }

  if (checking) {
    return <p>Checking your account...</p>;
  }

  
if (session) {
  return (
    <>
      <div style={{ padding: 12, textAlign: "right" }}>
        <span>{session.user.email} </span>
        <button onClick={() => void supabase.auth.signOut()}>
          Log out
        </button>
      </div>

      <CreditBalance userId={session.user.id} />
      <CreditCheckout />

      {children}
      <footer style={{
        maxWidth: 1200, margin: "20px auto", padding: "20px",
        display: "flex", gap: "16px", flexWrap: "wrap", justifyContent: "space-between",
        alignItems: "center", borderTop: "1px solid #dfe8e2",
      }}>
        <span style={{ fontSize: 12, color: "#5d726b" }}>© {new Date().getFullYear()} ResumeIQ</span>
        <LegalLinks className="ri-legal-links" />
      </footer>
    </>
  );
}


  return (
    <LandingPage
      mode={mode}
      email={email}
      password={password}
      busy={busy}
      message={message}
      onModeChange={(nextMode) => {
        setMode(nextMode);
        setMessage("");
      }}
      onEmailChange={setEmail}
      onPasswordChange={setPassword}
      onSubmit={handleSubmit}
    />
  );
}
