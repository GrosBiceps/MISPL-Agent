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
const AXIS_WIDTH = 12; // percentage of viewBox width reserved for Y-axis labels
const VIEW_WIDTH = 100;
const PLOT_WIDTH = VIEW_WIDTH - AXIS_WIDTH;
const LABEL_TOP_MARGIN = 12; // reserve space above bars for per-bar value labels

export default function UsageChart({ userId, days = 30, endDate }: Props) {
  const [data, setData] = useState<UsageDay[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setData(null);
    setError(null);
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
  const barWidth = PLOT_WIDTH / data.length;
  const allZero = totals.every((t) => t === 0);
  const showBarLabels = data.length <= 14;

  const totalTokens = totals.reduce((sum, t) => sum + t, 0);
  const totalRequests = data.reduce((sum, d) => sum + d.request_count, 0);
  const avgPerDay = data.length > 0 ? Math.round(totalTokens / data.length) : 0;

  const plotHeight = CHART_HEIGHT - LABEL_TOP_MARGIN;
  const axisLines = [0, 0.5, 1].map((frac) => ({
    frac,
    value: Math.round(max * frac),
    y: LABEL_TOP_MARGIN + plotHeight * (1 - frac),
  }));

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
      <svg
        viewBox={`0 0 ${VIEW_WIDTH} ${CHART_HEIGHT}`}
        preserveAspectRatio="none"
        style={{ width: "100%", height: CHART_HEIGHT, display: "block" }}
      >
        {axisLines.map(({ frac, value, y }) => (
          <g key={frac}>
            <line
              x1={AXIS_WIDTH}
              x2={VIEW_WIDTH}
              y1={y}
              y2={y}
              stroke="var(--ink-soft)"
              strokeOpacity={0.2}
              strokeWidth={0.3}
              vectorEffect="non-scaling-stroke"
            />
            <text
              x={AXIS_WIDTH - 1}
              y={y}
              textAnchor="end"
              dominantBaseline="middle"
              fontSize={5}
              fill="var(--ink-soft)"
            >
              {formatTokenCount(value)}
            </text>
          </g>
        ))}
        {data.map((d, i) => {
          const total = d.prompt_tokens + d.completion_tokens;
          const h = Math.max((total / max) * (plotHeight - 4), BAR_MIN_HEIGHT);
          const x = AXIS_WIDTH + i * barWidth;
          const barY = CHART_HEIGHT - h;
          return (
            <g key={d.date}>
              <rect
                x={x + barWidth * 0.15}
                y={barY}
                width={barWidth * 0.7}
                height={h}
                fill="var(--accent)"
                rx="1"
              >
                <title>
                  {d.date} — {total} tokens ({d.prompt_tokens} prompt / {d.completion_tokens} réponse), {d.request_count} requête(s)
                </title>
              </rect>
              {showBarLabels && total > 0 && (
                <text
                  x={x + barWidth / 2}
                  y={Math.max(barY - 2, 5)}
                  textAnchor="middle"
                  fontSize={5}
                  fill="var(--ink-soft)"
                >
                  {formatTokenCount(total)}
                </text>
              )}
            </g>
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
          paddingLeft: `${AXIS_WIDTH}%`,
        }}
      >
        <span>{data[0].date}</span>
        <span>{data[data.length - 1].date}</span>
      </div>
    </div>
  );
}
