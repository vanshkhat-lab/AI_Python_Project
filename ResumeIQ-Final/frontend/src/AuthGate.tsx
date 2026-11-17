import CreditBalance from "./CreditBalance";
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

      {children}
    </>
  );
}


  return (
    <div style={{ maxWidth: 400, margin: "60px auto", padding: 20 }}>
      <h1>ResumeIQ</h1>
      <h2>{mode === "signup" ? "Create account" : "Log in"}</h2>

      <form onSubmit={handleSubmit}>
        <label>Email</label>
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          style={{ width: "100%", marginBottom: 12 }}
        />

        <label>Password</label>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          minLength={6}
          required
          style={{ width: "100%", marginBottom: 12 }}
        />

        <button type="submit" disabled={busy}>
          {busy ? "Please wait..." :
            mode === "signup" ? "Sign up" : "Log in"}
        </button>
      </form>

      {message && <p>{message}</p>}

      <button
        type="button"
        onClick={() => {
          setMode(mode === "signup" ? "login" : "signup");
          setMessage("");
        }}
        style={{ marginTop: 16 }}
      >
        {mode === "signup"
          ? "Already have an account? Log in"
          : "New user? Create an account"}
      </button>
    </div>
  );
}
