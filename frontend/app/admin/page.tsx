"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  getMe,
  listAdminUsers,
  createAdminUser,
  updateAdminUser,
  resetAdminPassword,
  revokeAdminSessions,
  ApiError,
  MeResponse,
  AdminUser,
} from "../../lib/api";
import { getInitials } from "../../lib/avatar";
import { formatTokenCount, formatLastActive } from "../../lib/format";
import UserAvatarBadge from "../../components/UserAvatarBadge";
import Toggle from "../../components/Toggle";
import AdminUserDetailPanel from "../../components/AdminUserDetailPanel";

function CreateUserModal({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: (user: AdminUser, tempPassword: string) => void;
}) {
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [platformRole, setPlatformRole] = useState("user");
  const [canUseDsiMode, setCanUseDsiMode] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const result = await createAdminUser({
        email,
        display_name: displayName,
        platform_role: platformRole,
        can_use_dsi_mode: canUseDsiMode,
      });
      const { temporary_password, ...user } = result;
      onCreated({ ...user, total_tokens_30d: 0, last_active_at: null }, temporary_password);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Échec de la création du compte");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="card modal-card" onClick={(e) => e.stopPropagation()}>
        <h2 style={{ fontSize: 17, marginBottom: 16 }}>Nouveau compte</h2>
        {error && (
          <div className="error-banner" style={{ marginBottom: 12 }}>
            {error}
          </div>
        )}
        <form onSubmit={handleSubmit}>
          <label className="field-label">Email</label>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            style={{ marginBottom: 12 }}
          />
          <label className="field-label">Nom affiché</label>
          <input
            required
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            style={{ marginBottom: 12 }}
          />
          <label className="field-label">Rôle</label>
          <select
            value={platformRole}
            onChange={(e) => setPlatformRole(e.target.value)}
            style={{ marginBottom: 12 }}
          >
            <option value="user">Utilisateur</option>
            <option value="admin">Administrateur</option>
          </select>
          <label style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 18, fontSize: 13.5 }}>
            <input
              type="checkbox"
              checked={canUseDsiMode}
              onChange={(e) => setCanUseDsiMode(e.target.checked)}
              style={{ width: "auto" }}
            />
            Accès mode DSI
          </label>
          <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
            <button type="button" className="ghost" onClick={onClose}>
              Annuler
            </button>
            <button type="submit" disabled={submitting}>
              {submitting ? "..." : "Créer"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function AdminPage() {
  const router = useRouter();
  const [me, setMe] = useState<MeResponse | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [tempPasswordBanner, setTempPasswordBanner] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedUser, setSelectedUser] = useState<AdminUser | null>(null);

  useEffect(() => {
    getMe()
      .then((m) => {
        if (m.platform_role !== "admin") {
          router.push("/chat");
          return;
        }
        setMe(m);
      })
      .catch(() => router.push("/login?expired=1"));
  }, [router]);

  useEffect(() => {
    if (me) refreshUsers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [me]);

  async function refreshUsers() {
    try {
      const list = await listAdminUsers();
      setUsers(list);
      setLoadError(null);
    } catch {
      setLoadError("Impossible de charger la liste des comptes");
    }
  }

  async function handleToggle(id: number, field: "can_use_dsi_mode" | "is_active", value: boolean) {
    const previousValue = users.find((u) => u.id === id)?.[field];
    setUsers((prev) => prev.map((u) => (u.id === id ? { ...u, [field]: value } : u)));
    setActionError(null);
    try {
      const updated = await updateAdminUser(id, { [field]: value });
      setUsers((prev) => prev.map((u) => (u.id === id ? { ...u, ...updated } : u)));
    } catch (err) {
      if (previousValue !== undefined) {
        setUsers((prev) => prev.map((u) => (u.id === id ? { ...u, [field]: previousValue } : u)));
      }
      setActionError(err instanceof ApiError ? err.message : "Échec de la mise à jour");
    }
  }

  async function handleResetPassword(id: number) {
    setActionError(null);
    try {
      const result = await resetAdminPassword(id);
      setTempPasswordBanner(`Nouveau mot de passe temporaire : ${result.temporary_password}`);
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Échec de la réinitialisation");
    }
  }

  async function handleRevokeSessions(id: number) {
    setActionError(null);
    try {
      await revokeAdminSessions(id);
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Échec de la révocation des sessions");
    }
  }

  if (!me) {
    return <main style={{ padding: 40 }}>Chargement...</main>;
  }

  return (
    <main className="admin-page">
      <div className="admin-header">
        <h1 style={{ fontSize: 22 }}>Administration</h1>
        <button onClick={() => setShowCreateModal(true)}>+ Nouveau compte</button>
      </div>

      {tempPasswordBanner && (
        <div className="warning-banner" style={{ marginBottom: 16, display: "flex", justifyContent: "space-between", gap: 12 }}>
          <span>{tempPasswordBanner}</span>
          <button className="ghost" onClick={() => setTempPasswordBanner(null)} style={{ padding: "2px 10px", fontSize: 12 }}>
            OK
          </button>
        </div>
      )}
      {actionError && (
        <div className="error-banner" style={{ marginBottom: 16 }}>
          {actionError}
        </div>
      )}
      {loadError && (
        <div className="error-banner" style={{ marginBottom: 16 }}>
          {loadError}
        </div>
      )}

      <div className="admin-table-wrapper">
        <table className="admin-table">
          <thead>
            <tr>
              <th>Compte</th>
              <th>Rôle</th>
              <th>Mode DSI</th>
              <th>Actif</th>
              <th>Tokens (30j)</th>
              <th>Dernière activité</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id}>
                <td>
                  <button className="link-cell" onClick={() => setSelectedUser(u)}>
                    <UserAvatarBadge initials={getInitials(u.display_name)} size={28} />
                    <div>
                      <div className="link-cell-name" style={{ fontSize: 13.5 }}>
                        {u.display_name}
                      </div>
                      <div style={{ fontSize: 11.5, color: "var(--ink-soft)" }}>{u.email}</div>
                    </div>
                  </button>
                </td>
                <td>
                  <span className={`role-badge${u.platform_role === "admin" ? " admin" : ""}`}>
                    {u.platform_role === "admin" ? "Admin" : "Utilisateur"}
                  </span>
                </td>
                <td>
                  <Toggle
                    checked={u.can_use_dsi_mode}
                    onChange={(v) => handleToggle(u.id, "can_use_dsi_mode", v)}
                    label={`Mode DSI pour ${u.display_name}`}
                  />
                </td>
                <td>
                  <Toggle
                    checked={u.is_active}
                    onChange={(v) => handleToggle(u.id, "is_active", v)}
                    label={`Compte actif pour ${u.display_name}`}
                  />
                </td>
                <td>{formatTokenCount(u.total_tokens_30d)}</td>
                <td>{formatLastActive(u.last_active_at)}</td>
                <td>
                  <div style={{ display: "flex", gap: 6 }}>
                    <button
                      className="ghost"
                      onClick={() => handleResetPassword(u.id)}
                      style={{ fontSize: 12, padding: "6px 10px" }}
                    >
                      Réinitialiser
                    </button>
                    <button
                      className="ghost"
                      onClick={() => handleRevokeSessions(u.id)}
                      style={{ fontSize: 12, padding: "6px 10px" }}
                    >
                      Révoquer
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {showCreateModal && (
        <CreateUserModal
          onClose={() => setShowCreateModal(false)}
          onCreated={(user, tempPassword) => {
            setUsers((prev) => [...prev, user]);
            setTempPasswordBanner(`Mot de passe temporaire pour ${user.email} : ${tempPassword}`);
            setShowCreateModal(false);
          }}
        />
      )}
      {selectedUser && (
        <AdminUserDetailPanel user={selectedUser} onClose={() => setSelectedUser(null)} />
      )}
    </main>
  );
}
