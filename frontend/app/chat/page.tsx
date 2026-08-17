"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  askChat,
  getMe,
  logout,
  listConversations,
  getConversation,
  deleteConversation,
  ApiError,
  MeResponse,
  SourceOut,
  ConversationSummary,
} from "../../lib/api";
import { getInitials } from "../../lib/avatar";
import ChatMessage from "../../components/ChatMessage";
import EmptyState, { Suggestion } from "../../components/EmptyState";
import ThinkingIndicator from "../../components/ThinkingIndicator";
import BetaBadge from "../../components/BetaBadge";
import ConversationSidebar from "../../components/ConversationSidebar";
import ChatComposer from "../../components/ChatComposer";

interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: SourceOut[];
  warning?: string[];
}

const SUGGESTIONS: Suggestion[] = [
  {
    category: "Chaînes & syntaxe",
    question: "Comment utiliser Substr pour extraire une sous-chaine ?",
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <polyline
          points="8,7 3,12 8,17"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <polyline
          points="16,7 21,12 16,17"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    ),
  },
  {
    category: "Dates & formats",
    question: "Comment formater la date du jour en MISPL ?",
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <rect x="3" y="5" width="18" height="16" rx="2.5" stroke="currentColor" strokeWidth="1.8" />
        <line x1="3" y1="10" x2="21" y2="10" stroke="currentColor" strokeWidth="1.8" />
        <line x1="8" y1="3" x2="8" y2="7" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
        <line x1="16" y1="3" x2="16" y2="7" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      </svg>
    ),
  },
  {
    category: "Traçabilité & audit",
    question: "Comment écrire un log d'audit avec AddLogEntry ?",
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path
          d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8l-5-5Z"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinejoin="round"
        />
        <line x1="9" y1="13" x2="15" y2="13" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
        <line x1="9" y1="17" x2="13" y2="17" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      </svg>
    ),
  },
  {
    category: "Contexte & session",
    question: "Comment récupérer l'utilisateur connecté ?",
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <circle cx="12" cy="8" r="3.5" stroke="currentColor" strokeWidth="1.8" />
        <path
          d="M5 20a7 7 0 0 1 14 0"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
        />
      </svg>
    ),
  },
];

const SIDEBAR_COLLAPSED_KEY = "sidebar-collapsed";

export default function ChatPage() {
  const router = useRouter();
  const [user, setUser] = useState<MeResponse | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [question, setQuestion] = useState("");
  const [labContext, setLabContext] = useState("");
  const [loading, setLoading] = useState(false);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<number | null>(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [sidebarError, setSidebarError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const requestGenerationRef = useRef(0);

  useEffect(() => {
    getMe()
      .then(setUser)
      .catch(() => router.push("/login?expired=1"));
  }, [router]);

  useEffect(() => {
    try {
      const stored = localStorage.getItem(SIDEBAR_COLLAPSED_KEY);
      if (stored === "true") setSidebarCollapsed(true);
    } catch {
      // localStorage indisponible — la sidebar reste dépliée par défaut pour cette session.
    }
  }, []);

  useEffect(() => {
    if (user) refreshConversations();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function refreshConversations() {
    try {
      const list = await listConversations();
      setConversations(list);
      setSidebarError(null);
    } catch {
      setSidebarError("Impossible de charger l'historique");
    }
  }

  function toggleSidebar() {
    setSidebarCollapsed((prev) => {
      const next = !prev;
      try {
        localStorage.setItem(SIDEBAR_COLLAPSED_KEY, String(next));
      } catch {
        // localStorage indisponible — l'état reste correct en mémoire pour cette session.
      }
      return next;
    });
  }

  async function handleAsk(q: string) {
    if (!q.trim() || loading) return;
    const generation = ++requestGenerationRef.current;
    const history = messages
      .filter((m) => m.role === "user" || m.role === "assistant")
      .slice(-12)
      .map((m) => ({ role: m.role, content: m.content }));
    setMessages((prev) => [...prev, { role: "user", content: q }]);
    setQuestion("");
    setLoading(true);
    try {
      const result = await askChat(q, labContext || undefined, history, activeConversationId);
      if (requestGenerationRef.current !== generation) return;
      if (result.blocked) {
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: `🚫 Message bloqué — données sensibles détectées (${result.dlp_alerts.join(", ")}). Ne pas inclure de données patient (IPP, NIR...) dans les questions ou le contexte labo.`,
          },
        ]);
      } else {
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: result.response ?? "",
            sources: result.sources,
            warning: result.dlp_alerts.length > 0 ? result.dlp_alerts : undefined,
          },
        ]);
        if (result.conversation_id !== null && result.conversation_id !== activeConversationId) {
          setActiveConversationId(result.conversation_id);
        }
        refreshConversations();
      }
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        router.push("/login?expired=1");
        return;
      }
      if (requestGenerationRef.current !== generation) return;
      const content =
        err instanceof ApiError
          ? err.message
          : "Impossible de contacter le serveur — vérifiez votre connexion ou réessayez dans quelques instants.";
      setMessages((prev) => [...prev, { role: "assistant", content }]);
    } finally {
      if (requestGenerationRef.current === generation) setLoading(false);
    }
  }

  function handleReset() {
    requestGenerationRef.current++;
    setMessages([]);
    setActiveConversationId(null);
    setLoading(false);
  }

  async function handleSelectConversation(id: number) {
    if (loading) return;
    if (id === activeConversationId) return;
    const generation = ++requestGenerationRef.current;
    try {
      const detail = await getConversation(id);
      if (requestGenerationRef.current !== generation) return;
      setMessages(
        detail.messages.map((m) => ({
          role: m.role,
          content: m.content,
          sources: m.sources ?? undefined,
        }))
      );
      setActiveConversationId(id);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        router.push("/login?expired=1");
        return;
      }
      if (requestGenerationRef.current !== generation) return;
      setSidebarError("Impossible de charger cette conversation");
    }
  }

  async function handleDeleteConversation(id: number) {
    if (loading) return;
    try {
      await deleteConversation(id);
      setConversations((prev) => prev.filter((c) => c.id !== id));
      if (id === activeConversationId) {
        handleReset();
      }
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        router.push("/login?expired=1");
        return;
      }
      setSidebarError("Impossible de supprimer cette conversation");
    }
  }

  async function handleLogout() {
    await logout().catch(() => {});
    router.push("/login");
  }

  if (!user) {
    return <main style={{ padding: 40 }}>Chargement...</main>;
  }

  const activeTitle =
    activeConversationId === null
      ? null
      : conversations.find((c) => c.id === activeConversationId)?.title ?? null;

  return (
    <div className="app-layout">
      <ConversationSidebar
        conversations={conversations}
        activeId={activeConversationId}
        collapsed={sidebarCollapsed}
        error={sidebarError}
        userDisplayName={user.display_name}
        isAdmin={user.platform_role === "admin"}
        onToggleCollapse={toggleSidebar}
        onNew={handleReset}
        onSelect={handleSelectConversation}
        onDelete={handleDeleteConversation}
        onLogout={handleLogout}
      />
      <main
        className="chat-main"
        onWheel={(e) => {
          const area = scrollAreaRef.current;
          if (!area || area.contains(e.target as Node)) return;
          area.scrollTop += e.deltaY;
        }}
      >
        <div className="chat-content">
          <header className="chat-header">
            <h1 className="chat-header-title" title={activeTitle ?? undefined}>
              {activeTitle ?? "Assistant MISPL"}
            </h1>
            {!activeTitle && <BetaBadge />}
          </header>

          <div className="chat-scroll-area" ref={scrollAreaRef}>
            {messages.length === 0 && !loading ? (
              <EmptyState
                suggestions={SUGGESTIONS}
                onPick={handleAsk}
                canUseDsiMode={user.can_use_dsi_mode}
              />
            ) : (
              <div>
                {messages.map((m, i) => (
                  <ChatMessage
                    key={i}
                    role={m.role}
                    content={m.content}
                    sources={m.sources}
                    warning={m.warning}
                    userInitials={getInitials(user.display_name)}
                  />
                ))}
                {loading && <ThinkingIndicator />}
                <div ref={bottomRef} />
              </div>
            )}
          </div>

          <div className="sticky-input-bar">
            <ChatComposer
              question={question}
              onQuestionChange={setQuestion}
              labContext={labContext}
              onLabContextChange={setLabContext}
              loading={loading}
              onSubmit={() => handleAsk(question)}
            />
          </div>
        </div>
      </main>
    </div>
  );
}
