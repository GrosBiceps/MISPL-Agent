"use client";

import { ConversationSummary } from "../lib/api";
import { groupConversationsByDate } from "../lib/conversationGroups";
import AccountMenu from "./AccountMenu";
import AssistantAvatarIcon from "./AssistantAvatarIcon";

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
  onLogout: () => void;
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
  onLogout,
}: Props) {
  if (collapsed) {
    return (
      <aside className="conv-sidebar conv-sidebar-collapsed">
        <div className="rail-logo" aria-hidden="true">
          <AssistantAvatarIcon size={30} />
        </div>

        <button
          className="rail-btn"
          onClick={onToggleCollapse}
          aria-label="Afficher l'historique"
          title="Afficher l'historique"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <rect
              x="3"
              y="4"
              width="18"
              height="16"
              rx="2.5"
              stroke="currentColor"
              strokeWidth="1.7"
            />
            <line x1="9" y1="4" x2="9" y2="20" stroke="currentColor" strokeWidth="1.7" />
          </svg>
        </button>

        <button
          className="rail-btn"
          onClick={onNew}
          aria-label="Nouvelle conversation"
          title="Nouvelle conversation"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path
              d="M12 4H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-6"
              stroke="currentColor"
              strokeWidth="1.7"
              strokeLinecap="round"
            />
            <path
              d="M18.4 2.6a1.98 1.98 0 0 1 2.8 2.8L13.6 13l-3.5.7.7-3.5 7.6-7.6Z"
              stroke="currentColor"
              strokeWidth="1.7"
              strokeLinejoin="round"
            />
          </svg>
        </button>

        <div className="rail-spacer" />

        <AccountMenu displayName={userDisplayName} onLogout={onLogout} compact />
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
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.stopPropagation();
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
      <div className="conv-sidebar-footer">
        <AccountMenu displayName={userDisplayName} onLogout={onLogout} />
      </div>
    </aside>
  );
}
