import { useEffect, useState } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import { Icon, Text, useTheme } from 'react-native-paper';

type Props = {
  // How many calls are currently in a non-terminal pipeline state. The
  // chip auto-hides when this drops to zero — the parent computes it from
  // the polled list, so dismissal is implicit (no Dismiss button).
  inFlightCount: number;
  // Timestamp (epoch ms) of the most recent submit, used to render an
  // elapsed counter. Optional: when null or when N>1 the counter is
  // suppressed because a single "since" wouldn't reflect every call.
  startedAtMs?: number | null;
  onPress?: () => void;
};

function useElapsedSeconds(startedAtMs: number | null | undefined, active: boolean) {
  const [elapsed, setElapsed] = useState(() =>
    startedAtMs ? Math.max(0, Math.floor((Date.now() - startedAtMs) / 1000)) : 0,
  );

  useEffect(() => {
    if (!active || !startedAtMs) return;
    setElapsed(Math.max(0, Math.floor((Date.now() - startedAtMs) / 1000)));
    const id = setInterval(() => {
      setElapsed(Math.max(0, Math.floor((Date.now() - startedAtMs) / 1000)));
    }, 1000);
    return () => clearInterval(id);
  }, [startedAtMs, active]);

  return elapsed;
}

function formatElapsed(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return s === 0 ? `${m}m` : `${m}m ${s}s`;
}

export function AnalyzingChip({ inFlightCount, startedAtMs, onPress }: Props) {
  const theme = useTheme();
  const active = inFlightCount > 0;
  const showCounter = active && inFlightCount === 1 && Boolean(startedAtMs);
  const elapsed = useElapsedSeconds(startedAtMs ?? null, showCounter);

  if (!active) return null;

  const label =
    inFlightCount > 1
      ? `Analyzing ${inFlightCount} calls`
      : showCounter
        ? `Analyzing 1 call · ${formatElapsed(elapsed)}`
        : 'Analyzing 1 call';

  return (
    <View style={styles.row}>
      <Pressable
        onPress={onPress}
        accessibilityRole="button"
        accessibilityLabel={label}
        style={({ pressed }) => [
          styles.chip,
          {
            backgroundColor: theme.colors.primaryContainer,
            opacity: pressed ? 0.85 : 1,
          },
        ]}
      >
        <Icon source="creation" size={16} color={theme.colors.primary} />
        <Text
          variant="labelMedium"
          style={{ color: theme.colors.onPrimaryContainer, fontWeight: '600' }}
        >
          {label}
        </Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    justifyContent: 'center',
    paddingTop: 4,
    paddingBottom: 8,
  },
  chip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 999,
  },
});
