"use client";

import { useEffect, useState } from "react";
import { getUserUsageDaily, UsageDay } from "../lib/api";
import { formatTokenCount } from "../lib/format";

interface Props {
  userId: number;
  days?: number;
  endDate?: string;
}

const CHART_HEIGHT = 120;
const BAR_MIN_HEIGHT = 3;
const TOP_PAD = 10; // headroom above the tallest bar
const AXIS_COL_WIDTH = 42; // px, HTML column for Y-axis labels (outside the SVG)

export default function UsageChart({ userId, days = 30, endDate }: Props) {
  const [data, setData] = useState<UsageDay[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;
    setData(null);
    setError(null);
    setHoveredIndex(null);
    getUserUsageDaily(userId, days, endDate)
      .then((rows) => {
        if (!cancelled) setData(rows);
      })
      .catch(() => {
        if (!cancelled) setError("Impossible de charger l'historique d'usage");
      });
    return () => {
      cancelled = true;
    };
  }, [userId, days, endDate]);

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
  const showBarLabels = data.length <= 14;

  const totalTokens = totals.reduce((sum, t) => sum + t, 0);
  const totalRequests = data.reduce((sum, d) => sum + d.request_count, 0);
  const avgPerDay = data.length > 0 ? Math.round(totalTokens / data.length) : 0;

  const plotHeight = CHART_HEIGHT - TOP_PAD;
  const axisLines = [0, 0.5, 1].map((frac) => ({
    frac,
    value: Math.round(max * frac),
    y: TOP_PAD + plotHeight * (1 - frac),
  }));

  const bars = data.map((d, i) => {
    const total = d.prompt_tokens + d.completion_tokens;
    const h = Math.max((total / max) * (plotHeight - 4), BAR_MIN_HEIGHT);
    const x = i * barWidth;
    const barY = CHART_HEIGHT - h;
    return { d, i, total, x, barY };
  });

  const hovered = hoveredIndex !== null ? bars[hoveredIndex] : null;

  return (
    <div>
      <div
        style={{
          display: "flex",
          gap: 20,
          marginBottom: 12,
          fontSize: 12.5,
        }}
      >
        <div>
          <div style={{ color: "var(--ink-soft)" }}>Total tokens</div>
          <div style={{ fontSize: 15, fontWeight: 600 }}>{formatTokenCount(totalTokens)}</div>
        </div>
        <div>
          <div style={{ color: "var(--ink-soft)" }}>Total requêtes</div>
          <div style={{ fontSize: 15, fontWeight: 600 }}>{formatTokenCount(totalRequests)}</div>
        </div>
        <div>
          <div style={{ color: "var(--ink-soft)" }}>Moyenne / jour</div>
          <div style={{ fontSize: 15, fontWeight: 600 }}>{formatTokenCount(avgPerDay)}</div>
        </div>
      </div>

      {allZero && (
        <p style={{ fontSize: 12, color: "var(--ink-soft)", marginBottom: 6 }}>
          Aucune activité sur cette période.
        </p>
      )}

      <div style={{ display: "flex" }}>
        {/* Axe Y — libellés HTML (hors SVG) pour éviter la déformation du
            texte causée par preserveAspectRatio="none" sur un viewBox non carré. */}
        <div style={{ position: "relative", width: AXIS_COL_WIDTH, height: CHART_HEIGHT, flexShrink: 0 }}>
          {axisLines.map(({ frac, value, y }) => (
            <div
              key={frac}
              style={{
                position: "absolute",
                top: `${(y / CHART_HEIGHT) * 100}%`,
                right: 6,
                transform: "translateY(-50%)",
                fontSize: 10.5,
                color: "var(--ink-soft)",
                whiteSpace: "nowrap",
              }}
            >
              {formatTokenCount(value)}
            </div>
          ))}
        </div>

        <div style={{ position: "relative", flex: 1, minWidth: 0 }}>
          <svg
            viewBox={`0 0 100 ${CHART_HEIGHT}`}
            preserveAspectRatio="none"
            style={{ width: "100%", height: CHART_HEIGHT, display: "block" }}
          >
            {axisLines.map(({ frac, y }) => (
              <line
                key={frac}
                x1={0}
                x2={100}
                y1={y}
                y2={y}
                stroke="var(--ink-soft)"
                strokeOpacity={0.2}
                strokeWidth={0.3}
                vectorEffect="non-scaling-stroke"
              />
            ))}
            {bars.map(({ d, i, total, x, barY }) => (
              <g
                key={d.date}
                onMouseEnter={() => setHoveredIndex(i)}
                onMouseLeave={() => setHoveredIndex((prev) => (prev === i ? null : prev))}
                style={{ cursor: "pointer" }}
              >
                {/* Zone de survol invisible sur toute la largeur de la colonne — plus
                    facile à cibler qu'une barre fine de 70% de large. */}
                <rect x={x} y={0} width={barWidth} height={CHART_HEIGHT} fill="transparent" />
                <rect
                  x={x + barWidth * 0.15}
                  y={barY}
                  width={barWidth * 0.7}
                  height={Math.max(CHART_HEIGHT - barY, BAR_MIN_HEIGHT)}
                  fill={hoveredIndex === i ? "var(--accent-solid)" : "var(--accent)"}
                  rx="1"
                >
                  <title>
                    {d.date} — {total} tokens ({d.prompt_tokens} prompt / {d.completion_tokens} réponse), {d.request_count} requête(s)
                  </title>
                </rect>
              </g>
            ))}
          </svg>

          {/* Libellés de valeur par barre — HTML, affichés en permanence pour les
              périodes courtes (≤14 jours). */}
          {showBarLabels &&
            bars.map(
              ({ d, i, total, x, barY }) =>
                total > 0 && (
                  <div
                    key={d.date}
                    style={{
                      position: "absolute",
                      left: `${x + barWidth / 2}%`,
                      top: `${Math.max((barY / CHART_HEIGHT) * 100 - 3, 0)}%`,
                      transform:
                        i === 0 ? "translate(0, -100%)" : i === bars.length - 1 ? "translate(-100%, -100%)" : "translate(-50%, -100%)",
                      fontSize: 10.5,
                      color: "var(--ink-soft)",
                      whiteSpace: "nowrap",
                      pointerEvents: "none",
                    }}
                  >
                    {formatTokenCount(total)}
                  </div>
                )
            )}

          {/* Infobulle de survol — nombre exact de tokens du jour survolé. */}
          {hovered && (
            <div
              style={{
                position: "absolute",
                left: `${Math.min(Math.max(hovered.x + barWidth / 2, 8), 92)}%`,
                top: `${Math.max((hovered.barY / CHART_HEIGHT) * 100 - 4, 0)}%`,
                transform: "translate(-50%, -100%)",
                background: "var(--surface)",
                border: "1px solid var(--line)",
                borderRadius: 6,
                padding: "6px 9px",
                fontSize: 11.5,
                lineHeight: 1.4,
                whiteSpace: "nowrap",
                boxShadow: "var(--shadow)",
                pointerEvents: "none",
                zIndex: 1,
              }}
            >
              <div style={{ fontWeight: 600 }}>{hovered.d.date}</div>
              <div>{formatTokenCount(hovered.total)} tokens</div>
              <div style={{ color: "var(--ink-soft)" }}>
                {hovered.d.prompt_tokens} prompt / {hovered.d.completion_tokens} réponse
              </div>
              <div style={{ color: "var(--ink-soft)" }}>{hovered.d.request_count} requête(s)</div>
            </div>
          )}
        </div>
      </div>

      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          fontSize: 10,
          color: "var(--ink-soft)",
          marginTop: 4,
          paddingLeft: AXIS_COL_WIDTH,
        }}
      >
        <span>{data[0].date}</span>
        <span>{data[data.length - 1].date}</span>
      </div>
    </div>
  );
}
