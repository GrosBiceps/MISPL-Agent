export default function BetaBadge() {
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        fontSize: 11,
        fontWeight: 600,
        letterSpacing: "0.06em",
        textTransform: "uppercase",
        color: "var(--accent)",
        background: "var(--accent-soft)",
        border: "1px solid var(--line)",
        padding: "3px 10px",
        borderRadius: 999,
      }}
    >
      Beta
    </span>
  );
}
