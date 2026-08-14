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
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    const text = extractText(children);
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // Presse-papiers indisponible (contexte non sécurisé, permission refusée)
      // — pas d'action, le bouton reste "Copier".
    }
  }

  return (
    <div className="code-block-wrapper">
      <button type="button" className="copy-btn" onClick={handleCopy}>
        {copied ? "Copié ✓" : "Copier"}
      </button>
      <pre>{children}</pre>
    </div>
  );
}
