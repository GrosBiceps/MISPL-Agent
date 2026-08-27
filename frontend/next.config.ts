import type { NextConfig } from "next";

// Même variable d'env / valeur par défaut que frontend/lib/api.ts, pour que
// le connect-src du CSP autorise exactement l'origine backend réellement
// appelée par le client.
const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

// CSP pragmatique : 'unsafe-inline' sur script-src/style-src évite d'avoir à
// générer et maintenir des hashes de build pour les scripts/styles inline de
// Next.js (App Router, HMR en dev, etc.) — un CSP strict par hash sortirait
// du périmètre de cette tâche (durcissement des en-têtes de réponse). Les
// autres en-têtes (nosniff, DENY, Referrer-Policy) sont eux non négociables.
const CSP = [
  "default-src 'self'",
  `connect-src 'self' ${API_BASE}`,
  "script-src 'self' 'unsafe-inline'",
  "style-src 'self' 'unsafe-inline'",
].join("; ");

const nextConfig: NextConfig = {
  /* config options here */
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "Content-Security-Policy", value: CSP },
        ],
      },
    ];
  },
};

export default nextConfig;
