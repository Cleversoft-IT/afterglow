import { useMemo } from 'react';
import { View } from 'react-native';
import { Card, List, Text, useTheme } from 'react-native-paper';
import type { AppTheme } from '../lib/paperTheme';

type Turn = { speaker: string; text: string };

// Parse a transcript that uses "Operator: …" / "Caller: …" line prefixes
// (seed convention) OR "S1: …" / "S2: …" prefixes (Speechmatics raw output
// — both speaker and channel diarization use the same Sn label scheme).
// We tolerate Italian-localized labels too ("Operatore" / "Chiamante").
// Speakers map: S1 + first untagged segment → Operator, S2 + everything
// else → Caller. We only render two colors, so additional Sn channels
// (rare with two-party diarization) collapse to Caller.
const SPEAKER_RE =
  /^\s*(Operator|Caller|Operatore|Chiamante|S\d+)\s*:\s*/i;
// Inline match used by the safety-net split — same captures as SPEAKER_RE
// but anchored on a word boundary rather than line start, so we can break
// a single-line transcript into turns when newlines never made it through.
const SPEAKER_INLINE_RE =
  /\b(Operator|Caller|Operatore|Chiamante|S\d+)\s*:\s*/gi;

function normaliseSpeaker(raw: string): 'Operator' | 'Caller' {
  const lower = raw.toLowerCase();
  if (lower.startsWith('o')) return 'Operator';
  if (lower.startsWith('c')) return 'Caller';
  // Sn: by convention S1 is the operator (left channel in our stereo TTS),
  // any other Sn collapses to Caller for the 2-color render.
  return lower === 's1' ? 'Operator' : 'Caller';
}

function splitOnInlineSpeakers(text: string): string[] {
  // If the transcript is a single line containing 2+ inline speaker tags,
  // split before each tag so the line-based parser below can take over.
  if (/\r?\n/.test(text)) return text.split(/\r?\n/);
  const matches = text.match(SPEAKER_INLINE_RE) ?? [];
  if (matches.length < 2) return [text];
  return text
    .split(/(?=\b(?:Operator|Caller|Operatore|Chiamante|S\d+)\s*:\s*)/i)
    .map((s) => s.trim())
    .filter((s) => s.length > 0);
}

function parseTurns(text: string): Turn[] {
  const lines = splitOnInlineSpeakers(text);
  const turns: Turn[] = [];
  let current: Turn | null = null;
  for (const line of lines) {
    const m = line.match(SPEAKER_RE);
    if (m) {
      if (current) turns.push(current);
      current = { speaker: normaliseSpeaker(m[1]), text: line.slice(m[0].length).trim() };
    } else if (current) {
      // Continuation line of the current speaker.
      const append = line.trim();
      if (append) current.text = current.text ? `${current.text} ${append}` : append;
    } else if (line.trim()) {
      // Transcript starts without a speaker tag — treat as caller.
      current = { speaker: 'Caller', text: line.trim() };
    }
  }
  if (current) turns.push(current);
  return turns;
}

export function TranscriptList({ text }: { text: string }) {
  const theme = useTheme<AppTheme>();
  const turns = useMemo(() => parseTurns(text), [text]);

  if (turns.length === 0) {
    return (
      <Card mode="elevated">
        <Card.Title title="Transcript" />
        <Card.Content>
          <Text variant="bodyMedium" style={{ color: theme.colors.onSurfaceVariant, lineHeight: 20 }}>
            {text}
          </Text>
        </Card.Content>
      </Card>
    );
  }

  return (
    <Card mode="elevated">
      <Card.Title title="Transcript" subtitle={`${turns.length} turns`} />
      <Card.Content style={{ paddingHorizontal: 0 }}>
        <List.Accordion
          id="transcript"
          title="View turns"
          left={(p) => <List.Icon {...p} icon="format-list-bulleted-square" />}
        >
          <View style={{ paddingHorizontal: 16, paddingBottom: 8, gap: 12 }}>
            {turns.map((t, i) => {
              const isOperator = t.speaker === 'Operator';
              const accent = isOperator ? theme.colors.primary : theme.colors.success;
              return (
                <View key={i} style={{ gap: 4 }}>
                  <Text
                    variant="labelSmall"
                    style={{ fontWeight: '700', color: accent, letterSpacing: 0.5 }}
                  >
                    {t.speaker.toUpperCase()}
                  </Text>
                  <Text
                    variant="bodyMedium"
                    style={{ lineHeight: 20, color: theme.colors.onSurface }}
                  >
                    {t.text}
                  </Text>
                </View>
              );
            })}
          </View>
        </List.Accordion>
      </Card.Content>
    </Card>
  );
}
