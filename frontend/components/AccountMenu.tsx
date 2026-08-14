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
}

export default function AccountMenu({ displayName, onLogout }: Props) {
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
        className="ghost"
        onClick={() => setOpen((v) => !v)}
        style={{ display: "flex", alignItems: "center", gap: 8, padding: "6px 10px" }}
        aria-expanded={open}
        aria-haspopup="true"
      >
        <UserAvatarBadge initials={getInitials(displayName)} size={26} />
        <span style={{ fontSize: 13.5 }}>{displayName}</span>
      </button>
      {open && (
        <div
          className="card"
          style={{
            position: "absolute",
            top: "calc(100% + 8px)",
            right: 0,
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
          <button className="ghost" onClick={onLogout} style={{ width: "100%", textAlign: "left", padding: "8px 0" }}>
            Déconnexion
          </button>
        </div>
      )}
    </div>
  );
}
