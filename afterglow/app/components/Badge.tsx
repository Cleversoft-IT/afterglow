import { StyleSheet, Text, View } from 'react-native';
import { colors, radius, spacing } from '../lib/theme';

type Tone = 'neutral' | 'success' | 'warning' | 'danger' | 'brand';

const toneBg: Record<Tone, string> = {
  neutral: colors.surfaceAlt,
  success: 'rgba(52, 211, 153, 0.15)',
  warning: 'rgba(251, 191, 36, 0.15)',
  danger: 'rgba(248, 113, 113, 0.15)',
  brand: 'rgba(59, 130, 246, 0.15)',
};

const toneFg: Record<Tone, string> = {
  neutral: colors.textMuted,
  success: colors.success,
  warning: colors.warning,
  danger: colors.danger,
  brand: colors.brand,
};

export function Badge({ tone = 'neutral', children }: { tone?: Tone; children: string }) {
  return (
    <View style={[styles.wrap, { backgroundColor: toneBg[tone] }]}>
      <Text style={[styles.text, { color: toneFg[tone] }]}>{children}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    alignSelf: 'flex-start',
    paddingHorizontal: spacing.sm,
    paddingVertical: 2,
    borderRadius: radius.pill,
  },
  text: {
    fontSize: 12,
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
});
