export type CertaintyLevel = "certain" | "probable" | "check" | null;

export interface CertaintyExtraction {
  level: CertaintyLevel;
  rationale: string | null;
  cleanedContent: string;
}

const SECTION_HEADING = /^##\s*Niveau de certitude\s*$/im;
const EMOJIS = ["✅", "⚠️", "🔬"];

// Le LLM n'enrobe pas toujours le mot de niveau en gras — "✅ Certain — ..."
// est aussi fréquent que "✅ **Certain** — ...". Si le mot nu n'est pas
// retiré, il survit dans la justification et se retrouve dupliqué à côté du
// badge ("✅ CertainCertain — ...").
const LEVEL_WORDS: Record<string, RegExp> = {
  "✅": /^certain\b/i,
  "⚠️": /^probable\b/i,
  "🔬": /^à vérifier(?: dans glims)?\b/i,
};

// Extrait la justification qui suit le marqueur de niveau (emoji, gras ou
// non), ex : "✅ **Certain** — fonction documentée" ou "✅ Certain — fonction
// documentée" -> "fonction documentée". Retourne null si rien d'exploitable
// ne suit le niveau.
function extractRationale(sectionBody: string, emoji: string): string | null {
  const lines = sectionBody
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter((l) => l.length > 0);
  const line = lines.find((l) => l.includes(emoji));
  if (!line) return null;

  let text = line.slice(line.indexOf(emoji) + emoji.length).trim();
  // Retire les marqueurs de gras sans perdre le texte qu'ils entourent, pour
  // que le mot de niveau soit détectable qu'il ait été en gras ou non.
  text = text.replace(/\*\*/g, "").trim();
  // Retire le mot de niveau lui-même (ex: "Certain"), déjà affiché par le badge.
  const levelWord = LEVEL_WORDS[emoji];
  if (levelWord) {
    text = text.replace(levelWord, "").trim();
  }
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
