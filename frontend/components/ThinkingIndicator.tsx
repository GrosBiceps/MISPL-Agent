import AssistantAvatarIcon from "./AssistantAvatarIcon";

export default function ThinkingIndicator() {
  return (
    <div style={{ display: "flex", gap: 8, alignItems: "flex-start", margin: "12px 0" }}>
      <AssistantAvatarIcon />
      <div className="thinking">
        <span className="dot" />
        <span className="dot" />
        <span className="dot" />
        <span style={{ marginLeft: 6 }}>Recherche dans la documentation GLIMS...</span>
      </div>
    </div>
  );
}
