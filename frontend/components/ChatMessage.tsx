import ReactMarkdown from "react-markdown";
import { SourceOut } from "../lib/api";
import { extractCertainty } from "../lib/certainty";
import CodeBlock from "./CodeBlock";
import AssistantAvatarIcon from "./AssistantAvatarIcon";
import UserAvatarBadge from "./UserAvatarBadge";
import SourcesPanel from "./SourcesPanel";

interface Props {
  role: "user" | "assistant";
  content: string;
  sources?: SourceOut[];
  warning?: string[];
  userInitials?: string;
}

const CERTAINTY_LABEL: Record<string, string> = {
  certain: "✅ Certain",
  probable: "⚠️ Probable",
  check: "🔬 À vérifier",
};

const CERTAINTY_CLASS: Record<string, string> = {
  certain: "cert-certain",
  probable: "cert-probable",
  check: "cert-check",
};

export default function ChatMessage({ role, content, sources, warning, userInitials }: Props) {
  if (role === "user") {
    return (
      <div style={{ display: "flex", justifyContent: "flex-end", alignItems: "flex-start", gap: 8, margin: "16px 0" }}>
        <span
          style={{
            display: "inline-block",
            background: "var(--accent-solid)",
            color: "var(--accent-solid-text)",
            padding: "10px 14px",
            borderRadius: "12px 12px 3px 12px",
            maxWidth: "72%",
            fontSize: 14,
            boxShadow: "var(--shadow)",
          }}
        >
          {content}
        </span>
        <UserAvatarBadge initials={userInitials || "?"} />
      </div>
    );
  }

  const { level, rationale, cleanedContent } = extractCertainty(content);

  return (
    <div style={{ display: "flex", gap: 8, alignItems: "flex-start", margin: "16px 0" }}>
      <AssistantAvatarIcon />
      <div style={{ flex: 1, minWidth: 0 }}>
        {warning && warning.length > 0 && (
          <div className="warning-banner">
            ⚠️ Donnée potentiellement sensible détectée ({warning.join(", ")})
          </div>
        )}
        <div className="card" style={{ fontSize: 14, lineHeight: 1.6 }}>
          {level && (
            <div style={{ marginBottom: 10 }}>
              <span className={`cert-badge ${CERTAINTY_CLASS[level]}`}>{CERTAINTY_LABEL[level]}</span>
              {rationale && <span style={{ marginLeft: 8, fontSize: 12.5, color: "var(--ink-soft)" }}>{rationale}</span>}
            </div>
          )}
          <ReactMarkdown components={{ pre: CodeBlock }}>{cleanedContent}</ReactMarkdown>
        </div>
        {sources && sources.length > 0 && <SourcesPanel sources={sources} />}
      </div>
    </div>
  );
}
