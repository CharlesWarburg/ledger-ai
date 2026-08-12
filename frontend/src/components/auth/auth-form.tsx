"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { getApiErrorMessage } from "@/lib/api/errors";

interface AuthFormProps {
  mode: "login" | "register";
}

export function AuthForm({ mode }: AuthFormProps) {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const isRegister = mode === "register";

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setPending(true);

    const formData = new FormData(event.currentTarget);
    const email = String(formData.get("email") ?? "").trim();
    const password = String(formData.get("password") ?? "");

    if (isRegister && password.length < 8) {
      setError("Password must be at least 8 characters.");
      setPending(false);
      return;
    }

    try {
      const response = await fetch(isRegister ? "/api/register" : "/api/session", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      const body = await response.json().catch(() => undefined);

      if (!response.ok) {
        setError(getApiErrorMessage(response.status, body));
        return;
      }

      router.replace("/dashboard");
      router.refresh();
    } catch {
      setError("Unable to reach Ledger AI. Please try again.");
    } finally {
      setPending(false);
    }
  }

  return (
    <form className="auth-form" onSubmit={handleSubmit}>
      <div className="form-field">
        <label htmlFor="email">Email address</label>
        <input
          autoComplete="email"
          id="email"
          name="email"
          placeholder="you@company.com"
          required
          type="email"
        />
      </div>

      <div className="form-field">
        <div className="label-row">
          <label htmlFor="password">Password</label>
          {isRegister ? <span>8 characters minimum</span> : null}
        </div>
        <input
          autoComplete={isRegister ? "new-password" : "current-password"}
          id="password"
          minLength={isRegister ? 8 : 1}
          name="password"
          required
          type="password"
        />
      </div>

      {error ? (
        <p className="form-error" role="alert">
          {error}
        </p>
      ) : null}

      <button className="primary-button" disabled={pending} type="submit">
        {pending
          ? isRegister
            ? "Creating account…"
            : "Signing in…"
          : isRegister
            ? "Create account"
            : "Sign in"}
      </button>

      <p className="auth-switch">
        {isRegister ? "Already have an account?" : "New to Ledger AI?"}{" "}
        <Link href={isRegister ? "/login" : "/register"}>
          {isRegister ? "Sign in" : "Create an account"}
        </Link>
      </p>
    </form>
  );
}
