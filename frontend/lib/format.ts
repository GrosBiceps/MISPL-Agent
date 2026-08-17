export function formatTokenCount(n: number): string {
  if (n < 1000) return String(n);
  return `${(n / 1000).toFixed(1).replace(".", ",")}k`;
}

export function formatLastActive(dateStr: string | null): string {
  if (!dateStr) return "Jamais";
  const date = new Date(dateStr);
  const today = new Date();
  const diffDays = Math.floor(
    (Date.UTC(today.getFullYear(), today.getMonth(), today.getDate()) -
      Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate())) /
      86400000
  );
  if (diffDays <= 0) return "Aujourd'hui";
  if (diffDays === 1) return "Hier";
  return `Il y a ${diffDays} j`;
}
