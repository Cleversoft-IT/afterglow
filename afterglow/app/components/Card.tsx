import { useMemo } from 'react';
import { StyleSheet, View, type ViewProps } from 'react-native';
import { useTheme } from '../lib/ThemeContext';
import { radius, spacing } from '../lib/theme';

export function Card({ style, children, ...rest }: ViewProps) {
  const { colors, shadows } = useTheme();
  const styles = useMemo(
    () =>
      StyleSheet.create({
        card: {
          backgroundColor: colors.surface,
          borderRadius: radius.lg,
          borderWidth: StyleSheet.hairlineWidth,
          borderColor: colors.border,
          padding: spacing.lg,
          gap: spacing.sm,
          ...shadows.card,
        },
      }),
    [colors, shadows],
  );

  return (
    <View style={[styles.card, style]} {...rest}>
      {children}
    </View>
  );
}
