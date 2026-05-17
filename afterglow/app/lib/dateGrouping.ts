export type DateSection<T> = { title: string; data: T[] };

function startOfDay(d: Date): number {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
}

const MONTHS = [
  'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
];

export function relativeDay(iso: string, now: Date = new Date()): string {
  const d = new Date(iso);
  const dayStart = startOfDay(d);
  const nowStart = startOfDay(now);
  const diffDays = Math.round((nowStart - dayStart) / 86_400_000);
  if (diffDays === 0) return 'Today';
  if (diffDays === 1) return 'Yesterday';
  return `${d.getDate()} ${MONTHS[d.getMonth()]}`;
}

export function formatRelativeTime(iso: string, now: Date = new Date()): string {
  const d = new Date(iso);
  const diffMs = now.getTime() - d.getTime();
  const mins = Math.round(diffMs / 60_000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins} min ago`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const hh = String(d.getHours()).padStart(2, '0');
  const mm = String(d.getMinutes()).padStart(2, '0');
  return `${hh}:${mm}`;
}

export function groupByDay<T extends { created_at: string }>(items: T[]): DateSection<T>[] {
  const groups = new Map<string, T[]>();
  for (const item of items) {
    const key = relativeDay(item.created_at);
    const arr = groups.get(key);
    if (arr) arr.push(item);
    else groups.set(key, [item]);
  }
  return Array.from(groups.entries()).map(([title, data]) => ({ title, data }));
}
