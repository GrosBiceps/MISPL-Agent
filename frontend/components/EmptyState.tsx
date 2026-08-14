interface Props {
  examples: string[];
  onPick: (q: string) => void;
}

export default function EmptyState({ examples, onPick }: Props) {
  return (
    <div style={{ textAlign: "center", padding: "3rem 1rem" }}>
      <p style={{ fontSize: 16, fontWeight: 500, color: "var(--ink-soft)", marginBottom: 20 }}>
        Posez votre première question MISPL
      </p>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, textAlign: "left" }}>
        {examples.map((ex) => (
          <button key={ex} className="ghost" onClick={() => onPick(ex)} style={{ fontSize: 13 }}>
            {ex}
          </button>
        ))}
      </div>
    </div>
  );
}
