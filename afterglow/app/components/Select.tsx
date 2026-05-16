import { Pressable, StyleSheet, Text, View } from 'react-native';
import { colors, radius, spacing } from '../lib/theme';

type Option = { label: string; value: string };

export function Select({
  value,
  options,
  onChange,
  placeholder,
}: {
  value: string | null | undefined;
  options: Option[];
  onChange: (next: string) => void;
  placeholder?: string;
}) {
  return (
    <View style={styles.row}>
      {options.map((opt) => {
        const active = value === opt.value;
        return (
          <Pressable
            key={opt.value}
            onPress={() => onChange(opt.value)}
            style={[styles.chip, active && styles.chipActive]}
          >
            <Text style={[styles.label, active && styles.labelActive]}>{opt.label}</Text>
          </Pressable>
        );
      })}
      {value == null && placeholder ? (
        <Text style={styles.placeholder}>{placeholder}</Text>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm, alignItems: 'center' },
  chip: {
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs,
    borderRadius: radius.pill,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surfaceAlt,
  },
  chipActive: { borderColor: colors.brand, backgroundColor: colors.brand },
  label: { color: colors.textMuted, fontSize: 12, fontWeight: '500' },
  labelActive: { color: '#fff', fontWeight: '700' },
  placeholder: { color: colors.textSubtle, fontSize: 12 },
});
