// Locale-aware date/time formatting via Intl.DateTimeFormat (built-in on
// both web and Hermes/RN). Locale toggles between Italian (DD/MM/YYYY,
// 24h, Italian month/day labels) and English (MM/DD/YYYY, 12h, English).
// We never format the year for compact list rows (DayMonth helpers).

export type Locale = 'it' | 'en';

const TAG: Record<Locale, string> = { it: 'it-IT', en: 'en-US' };

// Cache formatters — Intl.DateTimeFormat construction is non-trivial and
// these helpers are called inside lists that re-render frequently.
const cache = new Map<string, Intl.DateTimeFormat>();
function fmt(loc: Locale, opts: Intl.DateTimeFormatOptions): Intl.DateTimeFormat {
  const key = TAG[loc] + ':' + JSON.stringify(opts);
  let f = cache.get(key);
  if (!f) {
    f = new Intl.DateTimeFormat(TAG[loc], opts);
    cache.set(key, f);
  }
  return f;
}

function parse(iso: string): Date {
  return new Date(iso);
}

export function formatDate(iso: string, loc: Locale): string {
  return fmt(loc, { day: '2-digit', month: '2-digit', year: 'numeric' }).format(parse(iso));
}

export function formatDayMonth(iso: string, loc: Locale): string {
  return fmt(loc, { day: '2-digit', month: '2-digit' }).format(parse(iso));
}

export function formatDayMonthShort(iso: string, loc: Locale): string {
  return fmt(loc, { day: 'numeric', month: 'short' }).format(parse(iso));
}

export function formatTime(iso: string, loc: Locale): string {
  return fmt(loc, { hour: '2-digit', minute: '2-digit', hour12: loc === 'en' }).format(parse(iso));
}

export function formatTimeWithSeconds(iso: string, loc: Locale): string {
  return fmt(loc, {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: loc === 'en',
  }).format(parse(iso));
}

export function formatDateTime(iso: string, loc: Locale): string {
  return formatDate(iso, loc) + ' ' + formatTime(iso, loc);
}

// Format a `YYYY-MM-DD` date + `HH:MM` time pair (as emitted by the backend
// for bookings) without going through a Date round-trip that would shift
// timezone. Returns `DD/MM HH:MM` or `M/D h:MM a`.
export function formatBookingSlot(
  date: string | null | undefined,
  time: string | null | undefined,
  loc: Locale,
): string {
  if (!date && !time) return '';
  // Combine into a local-time ISO so the formatter picks the user's
  // numeric style. If only date is present, append midnight.
  const safeTime = time ?? '00:00';
  const iso = `${date ?? '1970-01-01'}T${safeTime}`;
  // Validity check MUST come before any Intl.DateTimeFormat call:
  // custom-template extracts can emit natural-language dates like
  // "next Tuesday", and Intl throws RangeError("Invalid time value")
  // before our fallback path could fire. Belt-and-suspenders try/catch
  // around the formatters guards against locale/timezone edge cases.
  const d = parse(iso);
  if (Number.isNaN(d.getTime())) return [date, time].filter(Boolean).join(' ');
  try {
    const day = date ? formatDayMonth(iso, loc) : '';
    const hour = time ? formatTime(iso, loc) : '';
    return [day, hour].filter(Boolean).join(' ');
  } catch {
    return [date, time].filter(Boolean).join(' ');
  }
}

function startOfDay(d: Date): number {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
}

// "Today / Yesterday / D MMM" (EN) or "Oggi / Ieri / D MMM" (IT).
export function relativeDay(iso: string, loc: Locale, now: Date = new Date()): string {
  const d = parse(iso);
  const diffDays = Math.round((startOfDay(now) - startOfDay(d)) / 86_400_000);
  if (diffDays === 0) return loc === 'it' ? 'Oggi' : 'Today';
  if (diffDays === 1) return loc === 'it' ? 'Ieri' : 'Yesterday';
  return formatDayMonthShort(iso, loc);
}

// "just now / N min ago / yesterday / N days ago / ..." — calendar-day first.
// Same calendar day → hour-based (min/h/adesso); different calendar day →
// day/week/month/year buckets so the description always agrees with the
// section header produced by `relativeDay` above. A 9-hour gap that crosses
// midnight reports as "yesterday", not "9 h ago".
export function formatRelativeTime(iso: string, loc: Locale, now: Date = new Date()): string {
  const d = parse(iso);
  const diffDays = Math.round((startOfDay(now) - startOfDay(d)) / 86_400_000);
  if (diffDays <= 0) {
    // Same calendar day (or future-clamped). Hour-based description.
    // Future timestamps (e.g. seed calls shifted to today but with a clock
    // hour later than now) collapse to "just now" instead of leaking a
    // negative sign into the "N min fa / ago" branch.
    const diffMs = Math.max(0, now.getTime() - d.getTime());
    const mins = Math.round(diffMs / 60_000);
    if (mins < 1) return loc === 'it' ? 'adesso' : 'just now';
    if (mins < 60) return loc === 'it' ? `${mins} min fa` : `${mins} min ago`;
    const hours = Math.round(mins / 60);
    return loc === 'it' ? `${hours} h fa` : `${hours}h ago`;
  }
  if (diffDays === 1) return loc === 'it' ? 'ieri' : 'yesterday';
  if (diffDays < 7) return loc === 'it' ? `${diffDays} giorni fa` : `${diffDays} days ago`;
  const weeks = Math.floor(diffDays / 7);
  if (weeks < 4) {
    if (weeks === 1) return loc === 'it' ? 'una settimana fa' : 'a week ago';
    return loc === 'it' ? `${weeks} settimane fa` : `${weeks} weeks ago`;
  }
  const months = Math.floor(diffDays / 30);
  if (months === 1) return loc === 'it' ? 'un mese fa' : 'a month ago';
  if (months < 12) return loc === 'it' ? `${months} mesi fa` : `${months} months ago`;
  const years = Math.floor(diffDays / 365);
  if (years === 1) return loc === 'it' ? 'un anno fa' : 'a year ago';
  return loc === 'it' ? `${years} anni fa` : `${years} years ago`;
}
