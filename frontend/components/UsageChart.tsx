"use client";

import { useEffect, useState } from "react";
import { getUserUsageDaily, UsageDay } from "../lib/api";

interface Props {
  userId: number;
  days?: number;
}

const CHART_HEIGHT = 120;
const BAR_MIN_HEIGHT = 3;

export default function UsageChart({ userId, days = 30 }: Props) {
  const [data, setData] = useState<UsageDay[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setData(null);
    setError(null);
    getUserUsageDaily(userId, days)
      .then((rows) => {
        if (!cancelled) setData(rows);
      })
      .catch(() => {
        if (!cancelled) setError("Impossible de charger l'historique d'usage");
      });
    return () => {
      cancelled = true;
    };
  }, [userId, days]);

  if (error) {
    return <p style={{ fontSize: 12.5, color: "var(--ink-soft)" }}>{error}</p>;
  }
  if (!data) {
    return <p style={{ fontSize: 12.5, color: "var(--ink-soft)" }}>Chargement...</p>;
  }

  const totals = data.map((d) => d.prompt_tokens + d.completion_tokens);
  const max = Math.max(...totals, 1);
  const barWidth = 100 / data.length;
  const allZero = totals.every((t) => t === 0);

  return (
    <div>
      {allZero && (
        <p style={{ fontSize: 12, color: "var(--ink-soft)", marginBottom: 6 }}>
          Aucune activité sur cette période.
        </p>
      )}
      <svg
        viewBox={`0 0 100 ${CHART_HEIGHT}`}
        preserveAspectRatio="none"
        style={{ width: "100%", height: CHART_HEIGHT, display: "block" }}
      >
        {data.map((d, i) => {
          const total = d.prompt_tokens + d.completion_tokens;
          const h = Math.max((total / max) * (CHART_HEIGHT - 4), BAR_MIN_HEIGHT);
          const x = i * barWidth;
          return (
            <rect
              key={d.date}
              x={x + barWidth * 0.15}
              y={CHART_HEIGHT - h}
              width={barWidth * 0.7}
              height={h}
              fill="var(--accent)"
              rx="1"
            >
              <title>
                {d.date} — {total} tokens ({d.prompt_tokens} prompt / {d.completion_tokens} réponse), {d.request_count} requête(s)
              </title>
            </rect>
          );
        })}
      </svg>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          fontSize: 10,
          color: "var(--ink-soft)",
          marginTop: 4,
        }}
      >
        <span>{data[0].date}</span>
        <span>{data[data.length - 1].date}</span>
      </div>
    </div>
  );
}
