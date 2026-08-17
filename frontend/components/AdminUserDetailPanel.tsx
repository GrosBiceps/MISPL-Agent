"use client";

import { AdminUser } from "../lib/api";
import { formatTokenCount, formatLastActive } from "../lib/format";
import UsageChart from "./UsageChart";

interface Props {
  user: AdminUser;
  onClose: () => void;
}

export default function AdminUserDetailPanel({ user, onClose }: Props) {
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="card modal-card" style={{ maxWidth: 480 }} onClick={(e) => e.stopPropagation()}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 }}>
          <div>
            <h2 style={{ fontSize: 17 }}>{user.display_name}</h2>
            <p style={{ fontSize: 12.5, color: "var(--ink-soft)", margin: "2px 0 0" }}>{user.email}</p>
          </div>
          <button className="ghost" onClick={onClose} style={{ padding: "4px 10px", fontSize: 12 }}>
            Fermer
          </button>
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

        <p
          style={{
            fontSize: 11,
            textTransform: "uppercase",
            letterSpacing: "0.05em",
            color: "var(--ink-soft)",
            marginBottom: 8,
          }}
        >
          Consommation — 30 derniers jours
        </p>
        <UsageChart userId={user.id} days={30} />
      </div>
    </div>
  );
}
