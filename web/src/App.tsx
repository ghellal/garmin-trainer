import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import {
  createUserWithEmailAndPassword,
  onAuthStateChanged,
  sendEmailVerification,
  signInWithEmailAndPassword,
  signOut,
} from "firebase/auth";
import type { User } from "firebase/auth";
import { apiBaseUrl, firebaseAuth, firebaseConfigured } from "./firebase";

type ApiIdentity = { uid: string; email: string };
type Mode = "sign-in" | "create-account";

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [mode, setMode] = useState<Mode>("sign-in");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [identity, setIdentity] = useState<ApiIdentity | null>(null);
  const [apiError, setApiError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!firebaseAuth) return;
    return onAuthStateChanged(firebaseAuth, (nextUser) => {
      setUser(nextUser);
      setIdentity(null);
      setApiError("");
      setMessage("");
    });
  }, []);

  useEffect(() => {
    if (!firebaseAuth || !user?.emailVerified) return;

    let cancelled = false;
    void user
      .getIdToken()
      .then((token) =>
        fetch(`${apiBaseUrl}/api/v1/me`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
      )
      .then(async (response) => {
        if (!response.ok) {
          const payload = (await response.json().catch(() => ({}))) as {
            detail?: string;
          };
          throw new Error(payload.detail || `API request failed (${response.status}).`);
        }
        return (await response.json()) as ApiIdentity;
      })
      .then((result) => {
        if (!cancelled) setIdentity(result);
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setApiError(error instanceof Error ? error.message : "API request failed.");
        }
      });

    return () => {
      cancelled = true;
    };
  }, [user]);

  async function submitAuth(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!firebaseAuth) return;
    setBusy(true);
    setMessage("");
    setApiError("");

    try {
      if (mode === "create-account") {
        const credential = await createUserWithEmailAndPassword(
          firebaseAuth,
          email.trim(),
          password,
        );
        await sendEmailVerification(credential.user);
        setMessage("Check your inbox and verify your email before continuing.");
      } else {
        await signInWithEmailAndPassword(firebaseAuth, email.trim(), password);
      }
    } catch (error: unknown) {
      setMessage(error instanceof Error ? error.message : "Authentication failed.");
    } finally {
      setBusy(false);
    }
  }

  async function resendVerification() {
    if (!user) return;
    setBusy(true);
    try {
      await sendEmailVerification(user);
      setMessage("Verification email sent.");
    } catch (error: unknown) {
      setMessage(error instanceof Error ? error.message : "Could not send the email.");
    } finally {
      setBusy(false);
    }
  }

  async function refreshVerification() {
    if (!user || !firebaseAuth) return;
    setBusy(true);
    try {
      await user.reload();
      setUser(firebaseAuth.currentUser);
      setMessage("Account status refreshed.");
    } catch (error: unknown) {
      setMessage(error instanceof Error ? error.message : "Could not refresh account status.");
    } finally {
      setBusy(false);
    }
  }

  if (!firebaseConfigured || !firebaseAuth) {
    return (
      <main className="page-shell">
        <section className="card">
          <p className="eyebrow">GARMIN TRAINER · FOUNDATION</p>
          <h1>Configuration needed</h1>
          <p>
            Add the Firebase web-app settings to <code>web/.env.local</code> to enable sign-in.
          </p>
        </section>
      </main>
    );
  }

  return (
    <main className="page-shell">
      <section className="card">
        <p className="eyebrow">GARMIN TRAINER · FOUNDATION</p>
        <h1>Your training, thoughtfully adapted.</h1>
        <p className="intro">
          Sign in to verify the Firebase-to-API authentication path. Coaching features come next.
        </p>

        {!user && (
          <>
            <div className="mode-switch" role="tablist" aria-label="Authentication mode">
              <button
                className={mode === "sign-in" ? "active" : ""}
                onClick={() => setMode("sign-in")}
                type="button"
              >
                Sign in
              </button>
              <button
                className={mode === "create-account" ? "active" : ""}
                onClick={() => setMode("create-account")}
                type="button"
              >
                Create account
              </button>
            </div>
            <form className="auth-form" onSubmit={submitAuth}>
              <label>
                Email
                <input
                  autoComplete="email"
                  onChange={(event) => setEmail(event.target.value)}
                  required
                  type="email"
                  value={email}
                />
              </label>
              <label>
                Password
                <input
                  autoComplete={mode === "sign-in" ? "current-password" : "new-password"}
                  minLength={8}
                  onChange={(event) => setPassword(event.target.value)}
                  required
                  type="password"
                  value={password}
                />
              </label>
              <button className="primary-button" disabled={busy} type="submit">
                {busy ? "Please wait…" : mode === "sign-in" ? "Sign in" : "Create account"}
              </button>
            </form>
          </>
        )}

        {user && !user.emailVerified && (
          <div className="notice">
            <h2>Verify your email</h2>
            <p>We sent a verification link to {user.email}. The API stays locked until it is verified.</p>
            <div className="button-row">
              <button className="primary-button" disabled={busy} onClick={refreshVerification}>
                I verified my email
              </button>
              <button className="secondary-button" disabled={busy} onClick={resendVerification}>
                Resend email
              </button>
            </div>
          </div>
        )}

        {user?.emailVerified && (
          <div className="notice">
            <h2>Signed in as {user.email}</h2>
            {identity && <p className="success">API identity verified: {identity.uid}</p>}
            {apiError && <p className="error">{apiError}</p>}
            {!identity && !apiError && <p>Checking the authenticated API…</p>}
              <button
                className="secondary-button"
                onClick={() => {
                  if (firebaseAuth) void signOut(firebaseAuth);
                }}
              >
                Sign out
              </button>
          </div>
        )}

        {message && <p className="message" role="status">{message}</p>}
        <p className="privacy-note">Only the configured verified email is authorized by the API.</p>
      </section>
    </main>
  );
}
