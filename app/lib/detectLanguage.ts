// Quick word-based language detection for the wizard chat. The wizard
// runs a Gemini call that needs the user's language in its system prompt;
// proper detection (Compact Language Detector, fastText, etc.) is overkill
// for ~10 messages. We just look for high-frequency function words and
// pick the language with the most hits — defaulting to English when no
// signal is present, which matches the wizard's default tone.
//
// Supported: en, it, es, fr. Codes match what the backend wizard accepts
// in WizardChatRequest.language.

export type DetectedLanguage = 'en' | 'it' | 'es' | 'fr';

const STOPWORDS: Record<DetectedLanguage, ReadonlyArray<string>> = {
  en: [
    'the', 'and', 'is', 'are', 'a', 'an', 'of', 'to', 'for', 'in', 'on', 'with',
    'i', 'we', 'you', 'have', 'has', 'do', 'does', 'my', 'our', 'your', 'this',
    'that', 'about', 'when', 'how', 'what',
  ],
  it: [
    'il', 'la', 'lo', 'gli', 'le', 'di', 'che', 'e', 'un', 'una', 'uno', 'ho',
    'abbiamo', 'sono', 'è', 'sei', 'siamo', 'siete', 'mi', 'ti', 'ci', 'vi',
    'per', 'con', 'su', 'da', 'al', 'del', 'della', 'gestisco', 'nostro',
    'mio', 'cosa', 'quando', 'come', 'anche',
  ],
  es: [
    'el', 'la', 'los', 'las', 'de', 'que', 'y', 'un', 'una', 'unos', 'unas',
    'tengo', 'tenemos', 'soy', 'es', 'son', 'somos', 'me', 'te', 'nos', 'os',
    'para', 'con', 'sobre', 'desde', 'al', 'del', 'cuando', 'cómo', 'qué',
  ],
  fr: [
    'le', 'la', 'les', 'de', 'que', 'et', 'un', 'une', 'des', 'je', 'tu', 'il',
    'elle', 'nous', 'vous', 'ils', 'elles', 'ai', 'avons', 'suis', 'est', 'sont',
    'pour', 'avec', 'sur', 'depuis', 'du', 'au', 'aux', 'quand', 'comment', 'quoi',
  ],
};

function tokenise(text: string): string[] {
  return text
    .toLowerCase()
    .normalize('NFD')
    .split(/[^\p{L}']+/u)
    .filter((w) => w.length > 0);
}

export function detectLanguage(text: string): DetectedLanguage {
  const words = tokenise(text);
  if (words.length === 0) return 'en';
  const counts: Record<DetectedLanguage, number> = { en: 0, it: 0, es: 0, fr: 0 };
  for (const lang of Object.keys(STOPWORDS) as DetectedLanguage[]) {
    const stopwords = new Set(STOPWORDS[lang]);
    // Compare on the un-normalised form too so we don't penalise IT
    // accented function words like "è" stripped by NFD.
    const accented = tokenise(text.toLowerCase());
    for (const w of accented) {
      if (stopwords.has(w)) counts[lang] += 1;
    }
  }
  // Pick highest count; ties → English.
  let best: DetectedLanguage = 'en';
  let bestCount = counts.en;
  for (const lang of ['it', 'es', 'fr'] as const) {
    if (counts[lang] > bestCount) {
      best = lang;
      bestCount = counts[lang];
    }
  }
  return bestCount > 0 ? best : 'en';
}
