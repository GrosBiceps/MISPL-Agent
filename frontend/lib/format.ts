import { parseAsUtc } from "./conversationGroups";

export function formatTokenCount(n: number): string {
  if (n < 1000) return String(n);
  return `${(n / 1000).toFixed(1).replace(".", ",")}k`;
}

export function formatCount(n: number): string {
  return n.toLocaleString("fr-FR");
}

export function formatLastActive(dateStr: string | null): string {
  if (!dateStr) return "Jamais";
  const date = parseAsUtc(dateStr);
  const today = new Date();
  // Comparaison en jour calendaire LOCAL des deux côtés — date.getUTC*()
  // comparé à today.get*() (locaux) décalait le résultat d'un jour pour un
  // instant proche de minuit UTC (ex: 2026-08-26T23:30:00 = 27/08 01h30 à
  // Paris, mais lu comme "26/08" côté UTC → affichait "Hier" au lieu
  // d'"Aujourd'hui").
  const diffDays = Math.floor(
    (Date.UTC(today.getFullYear(), today.getMonth(), today.getDate()) -
      Date.UTC(date.getFullYear(), date.getMonth(), date.getDate())) /
      86400000
  );
  if (diffDays <= 0) return "Aujourd'hui";
  if (diffDays === 1) return "Hier";
  return `Il y a ${diffDays} j`;
}
