"use client";

import { useState, isValidElement, ReactNode } from "react";

function extractText(node: ReactNode): string {
  if (typeof node === "string") return node;
  if (Array.isArray(node)) return node.map(extractText).join("");
  if (isValidElement(node)) {
    const props = node.props as { children?: ReactNode };
    return extractText(props.children);
  }
  return "";
}

interface Props {
  children?: ReactNode;
}

export default function CodeBlock({ children }: Props) {
  const [status, setStatus] = useState<"idle" | "copied" | "error">("idle");

  async function handleCopy() {
    const text = extractText(children);
    try {
      await navigator.clipboard.writeText(text);
      setStatus("copied");
      setTimeout(() => setStatus("idle"), 1500);
    } catch {
      // Presse-papiers indisponible (contexte non sécurisé, permission refusée)
      // — on signale l'échec à l'utilisateur au lieu d'échouer silencieusement.
      setStatus("error");
      setTimeout(() => setStatus("idle"), 2000);
    }
  }

  return (
    <div className="code-block-wrapper">
      <button type="button" className="copy-btn" onClick={handleCopy}>
        {status === "copied" ? "Copié ✓" : status === "error" ? "Indisponible" : "Copier"}
      </button>
      <pre>{children}</pre>
    </div>
  );
}
