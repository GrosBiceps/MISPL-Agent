import Link from "next/link";
import BetaBadge from "../components/BetaBadge";

export default function Home() {
  return (
    <main
      style={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        textAlign: "center",
        padding: "0 20px",
        position: "relative",
      }}
    >
      <div
        style={{
          position: "absolute",
          top: 24,
          left: 24,
          fontFamily: "var(--serif)",
          fontWeight: 600,
          fontSize: 15,
        }}
      >
        MISPL Agent
      </div>
      <div style={{ position: "absolute", top: 26, right: 24 }}>
        <BetaBadge />
      </div>
      <h1 style={{ fontSize: 32, marginBottom: 12 }}>Assistant MISPL pour GLIMS</h1>
      <p style={{ color: "var(--ink-soft)", fontSize: 15, maxWidth: 400, margin: "0 0 28px" }}>
        Réponses sourcées depuis la documentation MISPL — sans hallucination.
      </p>
      <Link
        href="/login"
        style={{
          display: "inline-block",
          background: "var(--accent)",
          color: "#fff",
          fontFamily: "var(--sans)",
          fontSize: 14,
          fontWeight: 500,
          padding: "12px 28px",
          borderRadius: 10,
          textDecoration: "none",
        }}
      >
        Se connecter
      </Link>
    </main>
  );
}
