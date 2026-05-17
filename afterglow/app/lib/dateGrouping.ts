import type { Locale } from './dateFormat';
import { relativeDay } from './dateFormat';

export type DateSection<T> = { title: string; data: T[] };

export function groupByDay<T extends { created_at: string }>(
  items: T[],
  loc: Locale = 'it',
  now: Date = new Date(),
): DateSection<T>[] {
  const groups = new Map<string, T[]>();
  for (const item of items) {
    const key = relativeDay(item.created_at, loc, now);
    const arr = groups.get(key);
    if (arr) arr.push(item);
    else groups.set(key, [item]);
  }
  return Array.from(groups.entries()).map(([title, data]) => ({ title, data }));
}
