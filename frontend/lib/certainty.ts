export type CertaintyLevel = "certain" | "probable" | "check" | null;

export interface CertaintyExtraction {
  level: CertaintyLevel;
  rationale: string | null;
  cleanedContent: string;
}

const SECTION_HEADING = /^##\s*Niveau de certitude\s*$/im;
const EMOJIS = ["✅", "⚠️", "🔬"];

// Extrait la justification qui suit le marqueur de niveau (emoji + gras),
// ex : "✅ **Certain** — fonction documentée, syntaxe confirmée"
// -> "fonction documentée, syntaxe confirmée". Retourne null si rien
// d'exploitable ne suit le niveau.
function extractRationale(sectionBody: string, emoji: string): string | null {
  const lines = sectionBody
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter((l) => l.length > 0);
  const line = lines.find((l) => l.includes(emoji));
  if (!line) return null;

  let text = line.slice(line.indexOf(emoji) + emoji.length).trim();
  // Retire le marqueur en gras du niveau, ex: **Certain**
  text = text.replace(/^\*\*[^*]+\*\*\s*/, "");
  // Retire un tiret de tête (—, -, --) séparant le niveau de la justification
  text = text.replace(/^[-—]+\s*/, "");
  text = text.trim();

  return text.length > 0 ? text : null;
}

// Détecte la section "## Niveau de certitude" du Markdown de réponse
// (format imposé par CLAUDE.md), extrait le niveau (✅/⚠️/🔬) et sa
// justification, et retire la section du texte pour éviter un affichage
// en double avec le badge.
export function extractCertainty(markdown: string): CertaintyExtraction {
  const headingMatch = SECTION_HEADING.exec(markdown);
  if (!headingMatch) {
    return { level: null, rationale: null, cleanedContent: markdown };
  }

  const sectionStart = headingMatch.index;
  const afterHeading = markdown.slice(sectionStart + headingMatch[0].length);
  const nextHeadingMatch = /^##\s/m.exec(afterHeading);
  const sectionEnd = nextHeadingMatch
    ? sectionStart + headingMatch[0].length + nextHeadingMatch.index
    : markdown.length;

  const sectionBody = markdown.slice(sectionStart, sectionEnd);

  let level: CertaintyLevel = null;
  let emoji: string | null = null;
  for (const e of EMOJIS) {
    if (sectionBody.includes(e)) {
      emoji = e;
      break;
    }
  }
  if (emoji === "✅") level = "certain";
  else if (emoji === "⚠️") level = "probable";
  else if (emoji === "🔬") level = "check";

  if (level === null) {
    return { level: null, rationale: null, cleanedContent: markdown };
  }

  const rationale = extractRationale(sectionBody, emoji as string);
  const cleanedContent = (markdown.slice(0, sectionStart) + markdown.slice(sectionEnd)).trim();
  return { level, rationale, cleanedContent };
}
