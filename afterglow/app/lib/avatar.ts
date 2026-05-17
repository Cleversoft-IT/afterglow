export const AVATAR_PALETTE = [
  '#EF5350',
  '#EC407A',
  '#AB47BC',
  '#7E57C2',
  '#5C6BC0',
  '#42A5F5',
  '#26A69A',
  '#66BB6A',
  '#FFA726',
  '#8D6E63',
  '#78909C',
] as const;

function hashCode(str: string): number {
  let h = 0;
  for (let i = 0; i < str.length; i++) {
    h = (h << 5) - h + str.charCodeAt(i);
    h |= 0;
  }
  return h;
}

export function colorFromPhone(phone: string): string {
  if (!phone) return AVATAR_PALETTE[0];
  return AVATAR_PALETTE[Math.abs(hashCode(phone)) % AVATAR_PALETTE.length];
}

export function initialsFromName(name: string): string {
  // Phone-number strings (e.g. unknown callers shown as "+15550009999")
  // would otherwise compute a "+" or a digit as their initial, which looks
  // ugly in the colored circle. Detect them and skip — the ContactAvatar
  // falls back to a generic icon when initials are empty.
  const looksLikePhone = /^\+?[\d\s().-]+$/.test(name.trim());
  if (looksLikePhone) return '';

  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length >= 2) {
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  }
  if (parts.length === 1) {
    return parts[0][0].toUpperCase();
  }
  return '';
}
