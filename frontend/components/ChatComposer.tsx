"use client";

import { useEffect, useRef, useState } from "react";

interface Props {
  question: string;
  onQuestionChange: (value: string) => void;
  labContext: string;
  onLabContextChange: (value: string) => void;
  loading: boolean;
  onSubmit: () => void;
}

const MAX_TEXTAREA_HEIGHT = 160;

export default function ChatComposer({
  question,
  onQuestionChange,
  labContext,
  onLabContextChange,
  loading,
  onSubmit,
}: Props) {
  const [contextOpen, setContextOpen] = useState(false);
  const [focused, setFocused] = useState(false);
  const popoverRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const contextInputRef = useRef<HTMLInputElement>(null);

  const hasContext = labContext.trim().length > 0;
  const canSend = question.trim().length > 0 && !loading;

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, MAX_TEXTAREA_HEIGHT)}px`;
  }, [question]);

  useEffect(() => {
    if (!contextOpen) return;
    contextInputRef.current?.focus();
    function handleClickOutside(e: MouseEvent) {
      if (popoverRef.current && !popoverRef.current.contains(e.target as Node)) {
        setContextOpen(false);
      }
    }
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") setContextOpen(false);
    }
    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [contextOpen]);

  return (
    <div className="composer-wrapper">
      {hasContext && (
        <div className="composer-chip">
          <span className="composer-chip-label">Contexte</span>
          <span className="composer-chip-value">{labContext}</span>
          <button
            type="button"
            className="composer-chip-clear"
            aria-label="Retirer le contexte labo"
            onClick={() => onLabContextChange("")}
          >
            ×
          </button>
        </div>
      )}

      <div ref={popoverRef} style={{ position: "relative" }}>
        {contextOpen && (
          <div className="composer-popover">
            <p className="composer-popover-title">Contexte labo (optionnel)</p>
            <input
              ref={contextInputRef}
              value={labContext}
              onChange={(e) => onLabContextChange(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  setContextOpen(false);
                }
              }}
              placeholder="ex: Analyseur Cobas c702, tube EDTA, unités SI"
            />
            <p className="composer-popover-hint">
              Ajouté à chaque question pour préciser votre environnement.
            </p>
          </div>
        )}

        <form
          className={`composer${focused ? " focused" : ""}`}
          onSubmit={(e) => {
            e.preventDefault();
            if (canSend) onSubmit();
          }}
        >
          <button
            type="button"
            className={`composer-plus${hasContext ? " active" : ""}`}
            onClick={() => setContextOpen((v) => !v)}
            aria-label="Ajouter un contexte labo"
            aria-expanded={contextOpen}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <line x1="12" y1="5" x2="12" y2="19" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              <line x1="5" y1="12" x2="19" y2="12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
          </button>

          <textarea
            ref={textareaRef}
            className="composer-input"
            value={question}
            onChange={(e) => onQuestionChange(e.target.value)}
            onFocus={() => setFocused(true)}
            onBlur={() => setFocused(false)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                if (canSend) onSubmit();
              }
            }}
            placeholder="Posez votre question MISPL..."
            rows={1}
          />

          <button
            type="submit"
            className="composer-send"
            disabled={!canSend}
            aria-label="Envoyer la question"
          >
            {loading ? (
              <span className="composer-spinner" aria-hidden="true" />
            ) : (
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <line x1="12" y1="19" x2="12" y2="5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                <polyline
                  points="6,11 12,5 18,11"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
