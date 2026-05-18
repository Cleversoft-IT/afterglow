import type { Locale } from './dateFormat';
import { relativeDay } from './dateFormat';

export type DateSection<T> = { title: string; data: T[] };

// Group `items` into day-buckets using `relativeDay` as the bucket label.
// `keyFn` lets the caller swap the grouping date (e.g. group calls by their
// booking date instead of their created_at). The keyFn MUST return a valid
// ISO string — caller is responsible for the fallback when the alternate
// field is missing or malformed (a sensible default is item.created_at).
export function groupByDay<T extends { created_at: string }>(
  items: T[],
  loc: Locale = 'it',
  now: Date = new Date(),
  keyFn: (item: T) => string = (item) => item.created_at,
): DateSection<T>[] {
  const groups = new Map<string, T[]>();
  for (const item of items) {
    const key = relativeDay(keyFn(item), loc, now);
    const arr = groups.get(key);
    if (arr) arr.push(item);
    else groups.set(key, [item]);
  }
  return Array.from(groups.entries()).map(([title, data]) => ({ title, data }));
}
