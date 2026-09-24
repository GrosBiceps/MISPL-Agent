"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { changePassword, getMe, logout, ApiError, type MeResponse } from "../../lib/api";

// Changement de mot de passe : obligatoire après une création de compte ou
// une réinitialisation par un admin (mot de passe temporaire), possible à
// tout moment sinon. Les mots de passe ne vivent que dans l'état React de ce
// formulaire : jamais stockés (localStorage, URL), jamais journalisés.
export default function ChangePasswordPage() {
  const router = useRouter();
  const [me, setMe] = useState<MeResponse | null>(null);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    getMe()
      .then(setMe)
      .catch(() => router.push("/login?expired=1"));
  }, [router]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (newPassword !== confirmPassword) {
      setError("Les deux saisies du nouveau mot de passe ne correspondent pas.");
      return;
    }
    setLoading(true);
    try {
      await changePassword(currentPassword, newPassword);
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      router.push("/chat");
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        router.push("/login?expired=1");
      } else if (err instanceof ApiError && err.message === "invalid_current_password") {
        setError("Mot de passe actuel incorrect.");
      } else if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Serveur indisponible — vérifiez que l'API est démarrée.");
      }
    } finally {
      setLoading(false);
    }
  }

  async function handleLogout() {
    try {
      await logout();
    } finally {
      router.push("/login");
    }
  }

  if (!me) {
    return <main style={{ padding: 40 }}>Chargement...</main>;
  }

  const labelStyle = { display: "block", fontSize: 12.5, color: "var(--ink-soft)", marginBottom: 6 } as const;

  return (
    <main style={{ maxWidth: 420, margin: "10vh auto", padding: "0 20px" }}>
      <div className="card">
        <h1 style={{ fontSize: 22, marginBottom: 4 }}>Nouveau mot de passe</h1>
        <p style={{ color: "var(--ink-soft)", fontSize: 13, marginBottom: 20 }}>
          {me.must_change_password
            ? "Votre mot de passe est temporaire : choisissez-en un personnel pour continuer."
            : "Choisissez un nouveau mot de passe."}
        </p>
        <p style={{ color: "var(--ink-soft)", fontSize: 12, marginBottom: 16 }}>
          Au moins 12 caractères mêlant 3 familles (minuscules, majuscules, chiffres, caractères
          spéciaux), ou une phrase de passe d&apos;au moins 16 caractères. Il ne doit pas contenir
          votre identifiant ni votre nom.
        </p>
        <form onSubmit={handleSubmit}>
          <label style={labelStyle}>Mot de passe actuel</label>
          <input
            type="password"
            autoComplete="current-password"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            required
            style={{ marginBottom: 14 }}
          />
          <label style={labelStyle}>Nouveau mot de passe</label>
          <input
            type="password"
            autoComplete="new-password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            required
            minLength={12}
            maxLength={256}
            style={{ marginBottom: 14 }}
          />
          <label style={labelStyle}>Confirmer le nouveau mot de passe</label>
          <input
            type="password"
            autoComplete="new-password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            required
            style={{ marginBottom: 14 }}
          />
          {error && (
            <div className="error-banner" style={{ marginBottom: 14 }}>
              {error}
            </div>
          )}
          <button type="submit" disabled={loading} style={{ width: "100%", marginBottom: 10 }}>
            {loading ? "Enregistrement..." : "Enregistrer"}
          </button>
        </form>
        <button type="button" onClick={handleLogout} style={{ width: "100%" }}>
          Se déconnecter
        </button>
      </div>
    </main>
  );
}
