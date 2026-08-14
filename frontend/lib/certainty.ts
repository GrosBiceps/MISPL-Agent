export type CertaintyLevel = "certain" | "probable" | "check" | null;

export interface CertaintyExtraction {
  level: CertaintyLevel;
  cleanedContent: string;
}

const SECTION_HEADING = /^##\s*Niveau de certitude\s*$/im;

// Détecte la section "## Niveau de certitude" du Markdown de réponse
// (format imposé par CLAUDE.md), extrait le niveau (✅/⚠️/🔬) et retire
// la section du texte pour éviter un affichage en double avec le badge.
export function extractCertainty(markdown: string): CertaintyExtraction {
  const headingMatch = SECTION_HEADING.exec(markdown);
  if (!headingMatch) {
    return { level: null, cleanedContent: markdown };
  }

  const sectionStart = headingMatch.index;
  const afterHeading = markdown.slice(sectionStart + headingMatch[0].length);
  const nextHeadingMatch = /^##\s/m.exec(afterHeading);
  const sectionEnd = nextHeadingMatch
    ? sectionStart + headingMatch[0].length + nextHeadingMatch.index
    : markdown.length;

  const sectionBody = markdown.slice(sectionStart, sectionEnd);

  let level: CertaintyLevel = null;
  if (sectionBody.includes("✅")) level = "certain";
  else if (sectionBody.includes("⚠️")) level = "probable";
  else if (sectionBody.includes("🔬")) level = "check";

  if (level === null) {
    return { level: null, cleanedContent: markdown };
  }

  const cleanedContent = (markdown.slice(0, sectionStart) + markdown.slice(sectionEnd)).trim();
  return { level, cleanedContent };
}
