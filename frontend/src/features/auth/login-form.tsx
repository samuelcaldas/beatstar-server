"use client";

import { useState, type FormEvent } from "react";
import { NetworkError, RateLimitedError, UnauthorizedError } from "../../lib/api-client";

export interface Credentials {
  email: string;
  password: string;
}

interface LoginFormProps {
  /** Establishes the session; rejects with an ApiError subclass when the server refuses it. */
  signIn: (credentials: Credentials) => Promise<void>;
  onSignedIn: () => void;
}

/** Collects administrator credentials and reports why a sign-in attempt failed. */
export function LoginForm({ signIn, onSignedIn }: LoginFormProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending) return;
    setPending(true);
    setMessage(null);
    try {
      await signIn({ email: email.trim(), password });
      onSignedIn();
    } catch (failure) {
      setMessage(describeFailure(failure));
    } finally {
      setPending(false);
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <label htmlFor="login-email">E-mail</label>
      <input id="login-email" type="email" autoComplete="username" required value={email} onChange={(e) => setEmail(e.target.value)} />
      <label htmlFor="login-password">Senha</label>
      <input id="login-password" type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
      {message && <p role="alert">{message}</p>}
      <button type="submit" disabled={pending}>
        {pending ? "Entrando…" : "Entrar"}
      </button>
    </form>
  );
}

/** Maps a sign-in failure to the message shown to the administrator; unknown failures propagate. */
function describeFailure(failure: unknown): string {
  if (failure instanceof UnauthorizedError) return failure.message;
  if (failure instanceof RateLimitedError) return rateLimitMessage(failure.retryAfterSeconds);
  if (failure instanceof NetworkError) return failure.message;
  throw failure;
}

function rateLimitMessage(retryAfterSeconds: number | undefined): string {
  if (retryAfterSeconds === undefined) return "Muitas tentativas. Tente novamente em instantes.";
  return `Muitas tentativas. Aguarde ${retryAfterSeconds} segundos.`;
}
