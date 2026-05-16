import { useMemo } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useTheme } from '../lib/ThemeContext';
import { radius, spacing } from '../lib/theme';

export function Checkbox({
  value,
  onChange,
  label,
}: {
  value: boolean;
  onChange: (next: boolean) => void;
  label: string;
}) {
  const { colors } = useTheme();
  const styles = useMemo(
    () =>
      StyleSheet.create({
        row: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm + 2 },
        box: {
          width: 20,
          height: 20,
          borderRadius: radius.sm,
          borderWidth: 1,
          borderColor: colors.border,
          backgroundColor: colors.surface,
          alignItems: 'center',
          justifyContent: 'center',
        },
        boxOn: { backgroundColor: colors.brand, borderColor: colors.brand },
        tick: { color: colors.onPrimary, fontSize: 12, fontWeight: '600' },
        label: { color: colors.text, fontSize: 15 },
      }),
    [colors],
  );

  return (
    <Pressable
      style={styles.row}
      onPress={() => onChange(!value)}
      accessibilityRole="checkbox"
      accessibilityState={{ checked: value }}
    >
      <View style={[styles.box, value && styles.boxOn]}>
        {value ? <Text style={styles.tick}>✓</Text> : null}
      </View>
      <Text style={styles.label}>{label}</Text>
    </Pressable>
  );
}
