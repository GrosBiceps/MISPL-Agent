import { SourceOut } from "../lib/api";

interface Props {
  sources: SourceOut[];
}

/**
 * Découpe une chaîne source du RAG en fichier + section.
 * Le retriever produit des libellés du type
 * "02_functions/table_order/order_functions.md — Cas d'usage CHU — Ajout multiple"
 * ou simplement "rag_knowledge_base" (pas de section).
 */
function splitSource(source: string): { file: string; section: string | null } {
  const parts = source.split(/\s+—\s+/);
  if (parts.length < 2) return { file: source, section: null };
  return { file: parts[0], section: parts.slice(1).join(" — ") };
}

export default function SourcesPanel({ sources }: Props) {
  return (
    <details className="sources-panel">
      <summary className="sources-summary">
        <svg
          className="sources-chevron"
          width="12"
          height="12"
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
        <span>Sources documentaires</span>
        <span className="sources-count">{sources.length}</span>
      </summary>

      <ul className="sources-list">
        {sources.map((s, i) => {
          const { file, section } = splitSource(s.source);
          return (
            <li key={i} className="sources-item">
              {s.exact_match ? (
                <span className="sources-badge exact" title="Correspondance exacte">
                  <svg width="11" height="11" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                    <polyline
                      points="4,13 9,18 20,6"
                      stroke="currentColor"
                      strokeWidth="3"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                  Exact
                </span>
              ) : (
                <span className="sources-badge rank">{i + 1}</span>
              )}

              <div className="sources-body">
                {s.function_name && <code className="sources-fn">{s.function_name}</code>}
                <div className="sources-file" title={s.source}>
                  {file}
                </div>
                {section && (
                  <div className="sources-section" title={section}>
                    {section}
                  </div>
                )}
              </div>
            </li>
          );
        })}
      </ul>
    </details>
  );
}
