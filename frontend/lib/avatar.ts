export function svgAvatar(bg: string, fg: string, label: string): string {
  const svg = `<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 40 40'><circle cx='20' cy='20' r='20' fill='${bg}'/><text x='50%' y='53%' font-family='sans-serif' font-size='15' font-weight='600' fill='${fg}' text-anchor='middle' dominant-baseline='middle'>${label}</text></svg>`;
  return "data:image/svg+xml," + encodeURIComponent(svg);
}

export function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

// Avatar assistant fixe — reprend l'identité visuelle de l'ancien app.py
// (fond sombre, texte vert émeraude), SVG inline pour éviter tout appel
// réseau tiers (ex-DiceBear).
export const ASSISTANT_AVATAR = svgAvatar("#0f172a", "#6ee7b7", "AI");
