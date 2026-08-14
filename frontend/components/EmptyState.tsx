import { ReactNode } from "react";
import AssistantAvatarIcon from "./AssistantAvatarIcon";

export interface Suggestion {
  category: string;
  question: string;
  icon: ReactNode;
}

interface Props {
  suggestions: Suggestion[];
  onPick: (q: string) => void;
  canUseDsiMode: boolean;
}

export default function EmptyState({ suggestions, onPick, canUseDsiMode }: Props) {
  return (
    <div className="empty-state">
      <div className="empty-header">
        <AssistantAvatarIcon size={40} />
        <div className="empty-header-text">
          <h2 className="empty-title">Que cherchez-vous à faire en MISPL ?</h2>
          <p className="empty-subtitle">
            Réponses sourcées depuis la documentation GLIMS, jamais inventées.
          </p>
        </div>
        <span className={`empty-mode${canUseDsiMode ? " dsi" : ""}`}>
          {canUseDsiMode ? "Mode DSI" : "Mode Technicien"}
        </span>
      </div>

      <div className="empty-grid">
        {suggestions.map((s) => (
          <button
            key={s.question}
            className="suggestion-card"
            onClick={() => onPick(s.question)}
            type="button"
          >
            <span className="suggestion-icon" aria-hidden="true">
              {s.icon}
            </span>
            <span className="suggestion-body">
              <span className="suggestion-category">{s.category}</span>
              <span className="suggestion-question">{s.question}</span>
            </span>
            <svg
              className="suggestion-arrow"
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              aria-hidden="true"
            >
              <polyline
                points="9,6 15,12 9,18"
                stroke="currentColor"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </button>
        ))}
      </div>

      <div className="empty-legend">
        <span className="empty-legend-title">Chaque réponse est qualifiée</span>
        <span className="empty-legend-items">
          <span>
            <strong>✅ Certain</strong> — syntaxe confirmée
          </span>
          <span>
            <strong>⚠️ Probable</strong> — inférée d&apos;une doc partielle
          </span>
          <span>
            <strong>🔬 À vérifier</strong> — pseudo-code, à tester dans GLIMS
          </span>
        </span>
      </div>
    </div>
  );
}
