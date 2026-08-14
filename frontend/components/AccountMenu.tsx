"use client";

import { useEffect, useRef, useState } from "react";
import { useTheme, Theme } from "../lib/theme-context";
import { getInitials } from "../lib/avatar";
import UserAvatarBadge from "./UserAvatarBadge";

const THEME_OPTIONS: { value: Theme; label: string; swatch: string }[] = [
  { value: "green", label: "Vert", swatch: "#6f7d6a" },
  { value: "purple", label: "Violet", swatch: "#5F4D84" },
  { value: "orange", label: "Orange", swatch: "#D66E0B" },
];

interface Props {
  displayName: string;
  onLogout: () => void;
  compact?: boolean;
}

export default function AccountMenu({ displayName, onLogout, compact = false }: Props) {
  const { theme, setTheme } = useTheme();
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function handleClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open]);

  return (
    <div ref={menuRef} style={{ position: "relative" }}>
      <button
        onClick={() => setOpen((v) => !v)}
        className={compact ? "rail-btn" : undefined}
        style={
          compact
            ? undefined
            : {
                display: "flex",
                alignItems: "center",
                gap: 8,
                width: "100%",
                background: "transparent",
                border: "none",
                padding: "6px 0",
                color: "var(--ink-soft)",
                fontFamily: "var(--sans)",
              }
        }
        aria-expanded={open}
        aria-haspopup="true"
        aria-label={`Paramètres du compte (${displayName})`}
        title={compact ? displayName : undefined}
      >
        <UserAvatarBadge initials={getInitials(displayName)} size={26} />
        {!compact && (
          <>
            <span
              style={{
                flex: 1,
                textAlign: "left",
                fontSize: 13.5,
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
            >
              {displayName}
            </span>
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              style={{ color: "var(--accent)", flexShrink: 0 }}
              aria-hidden="true"
            >
              <circle cx="12" cy="12" r="3" />
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1Z" />
            </svg>
          </>
        )}
      </button>
      {open && (
        <div
          className="card"
          style={{
            position: "absolute",
            bottom: "calc(100% + 8px)",
            left: 0,
            width: 220,
            padding: 16,
            zIndex: 10,
          }}
        >
          <p
            style={{
              fontSize: 11,
              textTransform: "uppercase",
              letterSpacing: "0.05em",
              color: "var(--ink-soft)",
              marginBottom: 10,
            }}
          >
            Couleur de l&apos;interface
          </p>
          <div style={{ display: "flex", gap: 10, marginBottom: 16 }}>
            {THEME_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                onClick={() => setTheme(opt.value)}
                aria-label={opt.label}
                aria-pressed={theme === opt.value}
                style={{
                  width: 28,
                  height: 28,
                  borderRadius: "50%",
                  background: opt.swatch,
                  border: theme === opt.value ? "2px solid var(--ink)" : "2px solid transparent",
                  padding: 0,
                  cursor: "pointer",
                }}
              />
            ))}
          </div>
          <button
            onClick={onLogout}
            style={{
              width: "100%",
              textAlign: "left",
              padding: "8px 0",
              background: "transparent",
              border: "none",
              color: "var(--accent-text)",
              fontSize: 13.5,
            }}
          >
            Déconnexion
          </button>
        </div>
      )}
    </div>
  );
}
