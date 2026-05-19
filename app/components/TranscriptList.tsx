import { useMemo } from 'react';
import { View } from 'react-native';
import { Card, List, Text, useTheme } from 'react-native-paper';
import type { AppTheme } from '../lib/paperTheme';

type Turn = { speaker: string; text: string };

// Parse a transcript that uses "Operator: …" / "Caller: …" line prefixes
// (the convention used by both the seed and the live Speechmatics output).
// We tolerate Italian-localized labels too ("Operatore" / "Chiamante") so
// the same component works for any pipeline output.
const SPEAKER_RE = /^\s*(Operator|Caller|Operatore|Chiamante)\s*:\s*/i;

function parseTurns(text: string): Turn[] {
  const lines = text.split(/\r?\n/);
  const turns: Turn[] = [];
  let current: Turn | null = null;
  for (const line of lines) {
    const m = line.match(SPEAKER_RE);
    if (m) {
      if (current) turns.push(current);
      const speakerRaw = m[1].toLowerCase();
      const speaker = speakerRaw.startsWith('o') ? 'Operator' : 'Caller';
      current = { speaker, text: line.slice(m[0].length).trim() };
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
