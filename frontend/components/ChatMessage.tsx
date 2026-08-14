import ReactMarkdown from "react-markdown";
import { SourceOut } from "../lib/api";

interface Props {
  role: "user" | "assistant";
  content: string;
  sources?: SourceOut[];
  warning?: string[];
}

export default function ChatMessage({ role, content, sources, warning }: Props) {
  if (role === "user") {
    return (
      <div style={{ textAlign: "right", margin: "12px 0" }}>
        <span
          style={{
            display: "inline-block",
            background: "var(--accent)",
            color: "#fff",
            padding: "10px 14px",
            borderRadius: "12px 12px 3px 12px",
            maxWidth: "80%",
            fontSize: 14,
          }}
        >
          {content}
        </span>
      </div>
    );
  }

  return (
    <div style={{ margin: "12px 0" }}>
      {warning && warning.length > 0 && (
        <div className="warning-banner">
          ⚠️ Donnée potentiellement sensible détectée ({warning.join(", ")})
        </div>
      )}
      <div className="card" style={{ fontSize: 14, lineHeight: 1.6 }}>
        <ReactMarkdown>{content}</ReactMarkdown>
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
  );
}
