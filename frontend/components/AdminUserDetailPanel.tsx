"use client";

import { useState } from "react";
import { AdminUser } from "../lib/api";
import { formatTokenCount, formatLastActive } from "../lib/format";
import UsageChart from "./UsageChart";

interface Props {
  user: AdminUser;
  onClose: () => void;
}

const PERIOD_PRESETS = [7, 30, 90];

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

export default function AdminUserDetailPanel({ user, onClose }: Props) {
  const [days, setDays] = useState(30);
  const [endDate, setEndDate] = useState(todayIso());

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
