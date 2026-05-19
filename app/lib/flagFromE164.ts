// Map an E.164 phone number to a country flag emoji using a small prefix
// table — no external library, no runtime allocation per row. Falls back
// to the globe emoji when the prefix is unknown.

type Entry = { prefix: string; flag: string };

// Longest-first so the lookup picks "+1" only after "+1 NANP areas" fail
// (we only have one NANP entry and treat it as US — enough for the demo).
const TABLE: Entry[] = [
  { prefix: '+39',  flag: '🇮🇹' }, // Italy
  { prefix: '+44',  flag: '🇬🇧' }, // United Kingdom
  { prefix: '+49',  flag: '🇩🇪' }, // Germany
  { prefix: '+33',  flag: '🇫🇷' }, // France
  { prefix: '+34',  flag: '🇪🇸' }, // Spain
  { prefix: '+351', flag: '🇵🇹' }, // Portugal
  { prefix: '+41',  flag: '🇨🇭' }, // Switzerland
  { prefix: '+43',  flag: '🇦🇹' }, // Austria
  { prefix: '+31',  flag: '🇳🇱' }, // Netherlands
  { prefix: '+32',  flag: '🇧🇪' }, // Belgium
  { prefix: '+353', flag: '🇮🇪' }, // Ireland
  { prefix: '+30',  flag: '🇬🇷' }, // Greece
  { prefix: '+45',  flag: '🇩🇰' }, // Denmark
  { prefix: '+46',  flag: '🇸🇪' }, // Sweden
  { prefix: '+47',  flag: '🇳🇴' }, // Norway
  { prefix: '+358', flag: '🇫🇮' }, // Finland
  { prefix: '+48',  flag: '🇵🇱' }, // Poland
  { prefix: '+1',   flag: '🇺🇸' }, // US/Canada
];

// Sort by length descending so longer prefixes match first.
const SORTED = [...TABLE].sort((a, b) => b.prefix.length - a.prefix.length);

export function flagFromE164(phone: string): string {
  if (!phone) return '🌐';
  const trimmed = phone.replace(/\s+/g, '');
  for (const { prefix, flag } of SORTED) {
    if (trimmed.startsWith(prefix)) return flag;
  }
  return '🌐';
}
