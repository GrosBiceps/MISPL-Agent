import { ASSISTANT_AVATAR } from "../lib/avatar";

export default function ThinkingIndicator() {
  return (
    <div style={{ display: "flex", gap: 8, alignItems: "flex-start", margin: "12px 0" }}>
      <img
        src={ASSISTANT_AVATAR}
        alt=""
        style={{ width: 32, height: 32, borderRadius: "50%", flexShrink: 0 }}
      />
      <div className="thinking">
        <span className="dot" />
        <span className="dot" />
        <span className="dot" />
        <span style={{ marginLeft: 6 }}>Recherche dans la documentation GLIMS...</span>
      </div>
    </div>
  );
}
