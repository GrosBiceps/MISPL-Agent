"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { AdminUser, UpdateUserPayload, updateAdminUser, ApiError, UserBase } from "../lib/api";
import { formatTokenCount, formatLastActive } from "../lib/format";
import { useFocusTrap } from "../lib/useFocusTrap";
import UsageChart from "./UsageChart";

interface Props {
  user: AdminUser;
  onClose: () => void;
  onUpdated: (user: UserBase) => void;
}

const PERIOD_PRESETS = [7, 30, 90];

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

export default function AdminUserDetailPanel({ user, onClose, onUpdated }: Props) {
  const router = useRouter();
  const containerRef = useFocusTrap(onClose);
  const [days, setDays] = useState(30);
  const [endDate, setEndDate] = useState(todayIso());

  const [editing, setEditing] = useState(false);
  const [displayName, setDisplayName] = useState(user.display_name);
  const [email, setEmail] = useState(user.email);
  const [platformRole, setPlatformRole] = useState(user.platform_role);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const savingRef = useRef(false);

  useEffect(() => {
    setDisplayName(user.display_name);
    setEmail(user.email);
    setPlatformRole(user.platform_role);
  }, [user.id, user.display_name, user.email, user.platform_role]);

  async function handleSave() {
    if (savingRef.current) return; // garde de ré-entrance synchrone, plus fiable que le seul `disabled` du bouton
    savingRef.current = true;
    setSaving(true);
    setSaveError(null);
    const payload: UpdateUserPayload = {};
    if (displayName !== user.display_name) payload.display_name = displayName;
    if (email !== user.email) payload.email = email;
    if (platformRole !== user.platform_role) payload.platform_role = platformRole;
    if (Object.keys(payload).length === 0) {
      setEditing(false);
      setSaving(false);
      savingRef.current = false;
      return;
    }
    try {
      const updated = await updateAdminUser(user.id, payload);
      onUpdated(updated);
      setEditing(false);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        router.push("/login?expired=1");
        return;
      }
      setSaveError(err instanceof ApiError ? err.message : "Échec de l'enregistrement");
    } finally {
      setSaving(false);
      savingRef.current = false;
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        ref={containerRef}
        role="dialog"
        aria-modal="true"
        className="card modal-card"
        style={{ maxWidth: 480 }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ marginBottom: 16 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12 }}>
            {editing ? (
              <div style={{ flex: 1 }}>
                <label className="field-label">Nom affiché</label>
                <input
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  style={{ marginBottom: 10 }}
                />
                <label className="field-label">Email</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  style={{ marginBottom: 10 }}
                />
                <label className="field-label">Rôle</label>
                <select value={platformRole} onChange={(e) => setPlatformRole(e.target.value)}>
                  <option value="user">Utilisateur</option>
                  <option value="admin">Administrateur</option>
                </select>
              </div>
            ) : (
              <div>
                <h2 style={{ fontSize: 17 }}>{user.display_name}</h2>
                <p style={{ fontSize: 12.5, color: "var(--ink-soft)", margin: "2px 0 0" }}>{user.email}</p>
              </div>
            )}
            <div style={{ display: "flex", gap: 8, flexShrink: 0 }}>
              {editing ? (
                <>
                  <button
                    className="ghost"
                    onClick={() => {
                      setEditing(false);
                      setSaveError(null);
                      setDisplayName(user.display_name);
                      setEmail(user.email);
                      setPlatformRole(user.platform_role);
                    }}
                    style={{ padding: "4px 10px", fontSize: 12 }}
                    disabled={saving}
                  >
                    Annuler
                  </button>
                  <button onClick={handleSave} style={{ padding: "4px 10px", fontSize: 12 }} disabled={saving}>
                    {saving ? "..." : "Enregistrer"}
                  </button>
                </>
              ) : (
                <button className="ghost" onClick={() => setEditing(true)} style={{ padding: "4px 10px", fontSize: 12 }}>
                  Modifier
                </button>
              )}
              <button className="ghost" onClick={onClose} style={{ padding: "4px 10px", fontSize: 12 }}>
                Fermer
              </button>
            </div>
          </div>
          {saveError && (
            <div className="error-banner" style={{ marginTop: 10, fontSize: 12.5 }}>
              {saveError}
            </div>
          )}
        </div>

        <div style={{ display: "flex", gap: 20, marginBottom: 20, fontSize: 12.5 }}>
          <div>
            <div style={{ color: "var(--ink-soft)" }}>Tokens (30j)</div>
            <div style={{ fontSize: 16, fontWeight: 600 }}>{formatTokenCount(user.total_tokens_30d)}</div>
          </div>
          <div>
            <div style={{ color: "var(--ink-soft)" }}>Dernière activité</div>
            <div style={{ fontSize: 16, fontWeight: 600 }}>{formatLastActive(user.last_active_at)}</div>
          </div>
        </div>

        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: 8,
            marginBottom: 8,
          }}
        >
          <p
            style={{
              fontSize: 11,
              textTransform: "uppercase",
              letterSpacing: "0.05em",
              color: "var(--ink-soft)",
              margin: 0,
            }}
          >
            Consommation — {days} derniers jours
          </p>
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            {PERIOD_PRESETS.map((preset) => (
              <button
                key={preset}
                type="button"
                className="ghost"
                onClick={() => setDays(preset)}
                style={{
                  fontSize: 11,
                  padding: "3px 8px",
                  borderColor: preset === days ? "var(--accent)" : undefined,
                  color: preset === days ? "var(--accent)" : undefined,
                }}
              >
                {preset} jours
              </button>
            ))}
            <input
              type="date"
              value={endDate}
              max={todayIso()}
              onChange={(e) => setEndDate(e.target.value)}
              style={{ fontSize: 11, padding: "2px 6px" }}
            />
          </div>
        </div>
        <UsageChart userId={user.id} days={days} endDate={endDate} />
      </div>
    </div>
  );
}
