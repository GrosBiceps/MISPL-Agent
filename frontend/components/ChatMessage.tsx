import ReactMarkdown from "react-markdown";
import { SourceOut } from "../lib/api";
import { ASSISTANT_AVATAR, svgAvatar } from "../lib/avatar";
import { extractCertainty } from "../lib/certainty";
import CodeBlock from "./CodeBlock";

interface Props {
  role: "user" | "assistant";
  content: string;
  sources?: SourceOut[];
  warning?: string[];
  userInitials?: string;
}

const avatarStyle = { width: 32, height: 32, borderRadius: "50%", flexShrink: 0 } as const;

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
      <div style={{ display: "flex", justifyContent: "flex-end", alignItems: "flex-start", gap: 8, margin: "12px 0" }}>
        <span
          style={{
            display: "inline-block",
            background: "#5a6656",
            color: "#fff",
            padding: "10px 14px",
            borderRadius: "12px 12px 3px 12px",
            maxWidth: "80%",
            fontSize: 14,
          }}
        >
          {content}
        </span>
        <img src={svgAvatar("#6f7d6a", "#ffffff", userInitials || "?")} alt="" style={avatarStyle} />
      </div>
    );
  }

  const { level, rationale, cleanedContent } = extractCertainty(content);

  return (
    <div style={{ display: "flex", gap: 8, alignItems: "flex-start", margin: "12px 0" }}>
      <img src={ASSISTANT_AVATAR} alt="" style={avatarStyle} />
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
        {sources && sources.length > 0 && (
          <details style={{ marginTop: 6, fontSize: 12.5 }}>
            <summary style={{ cursor: "pointer", color: "var(--ink-soft)" }}>
              Sources documentaires ({sources.length})
            </summary>
            <ul style={{ marginTop: 8, paddingLeft: 18 }}>
              {sources.map((s, i) => (
                <li key={i} style={{ marginBottom: 4 }}>
                  <strong>{s.exact_match ? "EXACT" : `#${i + 1}`}</strong>
                  {s.function_name && ` · ${s.function_name}`}
                  <br />
                  <span style={{ color: "var(--ink-soft)" }}>{s.source}</span>
                </li>
              ))}
            </ul>
          </details>
        )}
      </div>
    </div>
  );
}
