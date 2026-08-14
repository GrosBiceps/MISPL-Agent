import { ConversationSummary } from "./api";

export interface ConversationGroup {
  label: string;
  conversations: ConversationSummary[];
}

const GROUP_LABELS = ["Aujourd'hui", "Hier", "7 derniers jours", "Plus ancien"] as const;

function startOfDay(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate());
}

// Le backend sérialise des timestamps naïfs (sans offset), ex. "2026-08-13T22:30:00.123456".
// new Date() interprèterait cette chaîne comme heure locale au lieu d'UTC — on force l'UTC ici.
function parseAsUtc(isoString: string): Date {
  const hasOffset = /Z$|[+-]\d{2}:\d{2}$/.test(isoString);
  return new Date(hasOffset ? isoString : `${isoString}Z`);
}

export function groupConversationsByDate(
  conversations: ConversationSummary[],
  now: Date = new Date()
): ConversationGroup[] {
  const today = startOfDay(now);
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);
  const weekAgo = new Date(today);
  weekAgo.setDate(weekAgo.getDate() - 7);

  const buckets: Record<(typeof GROUP_LABELS)[number], ConversationSummary[]> = {
    "Aujourd'hui": [],
    Hier: [],
    "7 derniers jours": [],
    "Plus ancien": [],
  };

  for (const conv of conversations) {
    const updated = parseAsUtc(conv.updated_at);
    if (updated >= today) {
      buckets["Aujourd'hui"].push(conv);
    } else if (updated >= yesterday) {
      buckets.Hier.push(conv);
    } else if (updated >= weekAgo) {
      buckets["7 derniers jours"].push(conv);
    } else {
      buckets["Plus ancien"].push(conv);
    }
  }

  return GROUP_LABELS.map((label) => ({ label, conversations: buckets[label] })).filter(
    (g) => g.conversations.length > 0
  );
}
