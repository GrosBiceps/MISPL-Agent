"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { askChat, getMe, logout, ApiError, MeResponse, SourceOut } from "../../lib/api";
import { getInitials } from "../../lib/avatar";
import ChatMessage from "../../components/ChatMessage";
import EmptyState from "../../components/EmptyState";
import ThinkingIndicator from "../../components/ThinkingIndicator";
import BetaBadge from "../../components/BetaBadge";

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

export default function ChatPage() {
  const router = useRouter();
  const [user, setUser] = useState<MeResponse | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [question, setQuestion] = useState("");
  const [labContext, setLabContext] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    getMe()
      .then(setUser)
      .catch(() => router.push("/login?expired=1"));
  }, [router]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

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
      const result = await askChat(q, labContext || undefined, history);
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
  }

  async function handleLogout() {
    await logout().catch(() => {});
    router.push("/login");
  }

  if (!user) {
    return <main style={{ padding: 40 }}>Chargement...</main>;
  }

  return (
    <main style={{ maxWidth: 780, margin: "0 auto", padding: "2rem 1.5rem 1rem" }}>
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <h1 style={{ fontSize: 22 }}>Assistant MISPL</h1>
            <BetaBadge />
          </div>
          <p style={{ color: "var(--ink-soft)", fontSize: 13 }}>{user.display_name}</p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button className="ghost" onClick={handleReset}>
            Nouvelle conversation
          </button>
          <button className="ghost" onClick={handleLogout}>
            Déconnexion
          </button>
        </div>
      </header>

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
    </main>
  );
}
