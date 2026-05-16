import { useMemo } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text } from 'react-native';
import { useTheme } from '../lib/ThemeContext';
import { radius, spacing, type ColorPalette } from '../lib/theme';

type Variant = 'primary' | 'secondary' | 'danger' | 'ghost';

function variantStyle(colors: ColorPalette, variant: Variant) {
  const map = {
    primary: { bg: colors.brand, fg: colors.onPrimary, border: colors.brand },
    secondary: { bg: colors.surface, fg: colors.text, border: colors.border },
    danger: { bg: colors.surface, fg: colors.danger, border: colors.border },
    ghost: { bg: 'transparent', fg: colors.textMuted, border: 'transparent' },
  };
  return map[variant];
}

export function Button({
  title,
  onPress,
  disabled,
  loading,
  variant = 'primary',
}: {
  title: string;
  onPress?: () => void;
  disabled?: boolean;
  loading?: boolean;
  variant?: Variant;
}) {
  const { colors } = useTheme();
  const styles = useMemo(() => createStyles(), []);
  const v = variantStyle(colors, variant);

  return (
    <Pressable
      onPress={onPress}
      disabled={disabled || loading}
      accessibilityRole="button"
      accessibilityState={{ disabled: disabled || loading, busy: loading }}
      style={({ pressed }) => [
        styles.btn,
        {
          backgroundColor: v.bg,
          borderColor: v.border,
          opacity: disabled ? 0.45 : pressed ? 0.88 : 1,
        },
      ]}
    >
      {loading ? (
        <ActivityIndicator color={v.fg} size="small" />
      ) : (
        <Text style={[styles.label, { color: v.fg }]}>{title}</Text>
      )}
    </Pressable>
  );
}

function createStyles() {
  return StyleSheet.create({
    btn: {
      paddingVertical: spacing.md + 2,
      paddingHorizontal: spacing.xl,
      borderRadius: radius.pill,
      borderWidth: 1,
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: 44,
    },
    label: { fontWeight: '500', fontSize: 15 },
  });
}
