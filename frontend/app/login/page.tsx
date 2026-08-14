"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { login, ApiError } from "../../lib/api";

export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginForm />
    </Suspense>
  );
}

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(
    searchParams.get("expired") === "1" ? "Session expirée, reconnectez-vous." : null
  );
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(email, password);
      router.push("/chat");
    } catch (err) {
      if (err instanceof ApiError && err.status === 423) {
        setError("Compte verrouillé temporairement — trop de tentatives. Réessayez dans 15 minutes.");
      } else if (err instanceof ApiError) {
        setError("Email ou mot de passe incorrect.");
      } else {
        setError("Serveur indisponible — vérifiez que l'API est démarrée.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <main style={{ maxWidth: 380, margin: "10vh auto", padding: "0 20px" }}>
      <div className="card">
        <h1 style={{ fontSize: 22, marginBottom: 4 }}>Assistant MISPL</h1>
        <p style={{ color: "var(--ink-soft)", fontSize: 13, marginBottom: 20 }}>
          Connexion technicien
        </p>
        <form onSubmit={handleSubmit}>
          <label style={{ display: "block", fontSize: 12.5, color: "var(--ink-soft)", marginBottom: 6 }}>
            Email
          </label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            style={{ marginBottom: 14 }}
          />
          <label style={{ display: "block", fontSize: 12.5, color: "var(--ink-soft)", marginBottom: 6 }}>
            Mot de passe
          </label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            style={{ marginBottom: 14 }}
          />
          {error && (
            <div className="error-banner" style={{ marginBottom: 14 }}>
              {error}
            </div>
          )}
          <button type="submit" disabled={loading} style={{ width: "100%" }}>
            {loading ? "Connexion..." : "Se connecter"}
          </button>
        </form>
      </div>
    </main>
  );
}
