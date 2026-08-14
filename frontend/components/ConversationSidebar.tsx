"use client";

import { ConversationSummary } from "../lib/api";
import { groupConversationsByDate } from "../lib/conversationGroups";

interface Props {
  conversations: ConversationSummary[];
  activeId: number | null;
  collapsed: boolean;
  error: string | null;
  userDisplayName: string;
  onToggleCollapse: () => void;
  onNew: () => void;
  onSelect: (id: number) => void;
  onDelete: (id: number) => void;
}

export default function ConversationSidebar({
  conversations,
  activeId,
  collapsed,
  error,
  userDisplayName,
  onToggleCollapse,
  onNew,
  onSelect,
  onDelete,
}: Props) {
  if (collapsed) {
    return (
      <aside className="conv-sidebar conv-sidebar-collapsed">
        <button
          className="ghost conv-sidebar-toggle"
          onClick={onToggleCollapse}
          aria-label="Afficher l'historique"
        >
          »
        </button>
      </aside>
    );
  }

  const groups = groupConversationsByDate(conversations);

  return (
    <aside className="conv-sidebar">
      <div className="conv-sidebar-header">
        <span className="conv-sidebar-logo">MISPL Agent</span>
        <button
          className="ghost conv-sidebar-toggle"
          onClick={onToggleCollapse}
          aria-label="Masquer l'historique"
        >
          «
        </button>
      </div>
      <button className="conv-sidebar-new-btn" onClick={onNew}>
        + Nouvelle conversation
      </button>
      {error && <div className="conv-sidebar-error">{error}</div>}
      <div className="conv-sidebar-list">
        {conversations.length === 0 && !error && (
          <p className="conv-sidebar-empty">Aucune conversation pour l&apos;instant</p>
        )}
        {groups.map((group) => (
          <div key={group.label} className="conv-sidebar-group">
            <div className="conv-sidebar-group-label">{group.label}</div>
            {group.conversations.map((conv) => (
              <div
                key={conv.id}
                className={`conv-sidebar-item${conv.id === activeId ? " active" : ""}`}
                role="button"
                tabIndex={0}
                onClick={() => onSelect(conv.id)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    if (e.key === " ") {
                      e.preventDefault();
                    }
                    onSelect(conv.id);
                  }
                }}
              >
                <span className="conv-sidebar-item-title">{conv.title}</span>
                <button
                  className="conv-sidebar-item-delete"
                  aria-label="Supprimer la conversation"
                  onClick={(e) => {
                    e.stopPropagation();
                    if (window.confirm("Supprimer cette conversation ?")) {
                      onDelete(conv.id);
                    }
                  }}
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        ))}
      </div>
      <div className="conv-sidebar-footer">{userDisplayName}</div>
    </aside>
  );
}
