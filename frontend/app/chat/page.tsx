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
import EmptyState from "../../components/EmptyState";
import ThinkingIndicator from "../../components/ThinkingIndicator";
import BetaBadge from "../../components/BetaBadge";
import ConversationSidebar from "../../components/ConversationSidebar";

interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: SourceOut[];
  warning?: string[];
}

const EXAMPLES = [
  "Comment utiliser Substr pour extraire une sous-chaine ?",
  "Comment formater la date du jour en MISPL ?",
  "Comment écrire un log d'audit avec AddLogEntry ?",
  "Comment récupérer l'utilisateur connecté ?",
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

  useEffect(() => {
    getMe()
      .then(setUser)
      .catch(() => router.push("/login?expired=1"));
  }, [router]);

  useEffect(() => {
    const stored = localStorage.getItem(SIDEBAR_COLLAPSED_KEY);
    if (stored === "true") setSidebarCollapsed(true);
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
      localStorage.setItem(SIDEBAR_COLLAPSED_KEY, String(next));
      return next;
    });
  }

  async function handleAsk(q: string) {
    if (!q.trim() || loading) return;
    const history = messages
      .filter((m) => m.role === "user" || m.role === "assistant")
      .slice(-12)
      .map((m) => ({ role: m.role, content: m.content }));
    setMessages((prev) => [...prev, { role: "user", content: q }]);
    setQuestion("");
    setLoading(true);
    try {
      const result = await askChat(q, labContext || undefined, history, activeConversationId);
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
      const content =
        err instanceof ApiError
          ? err.message
          : "Impossible de contacter le serveur — vérifiez votre connexion ou réessayez dans quelques instants.";
      setMessages((prev) => [...prev, { role: "assistant", content }]);
    } finally {
      setLoading(false);
    }
  }

  function handleReset() {
    setMessages([]);
    setActiveConversationId(null);
  }

  async function handleSelectConversation(id: number) {
    if (loading) return;
    if (id === activeConversationId) return;
    try {
      const detail = await getConversation(id);
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

  return (
    <div className="app-layout">
      <ConversationSidebar
        conversations={conversations}
        activeId={activeConversationId}
        collapsed={sidebarCollapsed}
        error={sidebarError}
        userDisplayName={user.display_name}
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
          <header style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 24, flexShrink: 0 }}>
            <h1 style={{ fontSize: 22 }}>Assistant MISPL</h1>
            <BetaBadge />
          </header>

          <div className="chat-scroll-area" ref={scrollAreaRef}>
            {messages.length === 0 && !loading ? (
              <EmptyState examples={EXAMPLES} onPick={handleAsk} />
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
            <div className="card">
              <label style={{ display: "block", fontSize: 12, color: "var(--ink-soft)", marginBottom: 6 }}>
                Contexte labo (optionnel)
              </label>
              <input
                value={labContext}
                onChange={(e) => setLabContext(e.target.value)}
                placeholder="ex: Analyseur Cobas c702, tube EDTA, unités SI"
                style={{ marginBottom: 12 }}
              />
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  handleAsk(question);
                }}
                style={{ display: "flex", gap: 8 }}
              >
                <input
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  placeholder="Posez votre question MISPL..."
                  style={{ flex: 1 }}
                />
                <button type="submit" disabled={loading}>
                  {loading ? "..." : "Envoyer"}
                </button>
              </form>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
