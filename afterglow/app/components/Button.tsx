import { Pressable, StyleSheet, Text, ActivityIndicator } from 'react-native';
import { colors, radius, spacing } from '../lib/theme';

type Variant = 'primary' | 'secondary' | 'danger' | 'ghost';

const variantStyle = {
  primary: { bg: colors.brand, fg: '#fff', border: colors.brand },
  secondary: { bg: colors.surfaceAlt, fg: colors.text, border: colors.border },
  danger: { bg: 'transparent', fg: colors.danger, border: colors.danger },
  ghost: { bg: 'transparent', fg: colors.textMuted, border: 'transparent' },
};

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
  const v = variantStyle[variant];
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled || loading}
      style={({ pressed }) => [
        styles.btn,
        { backgroundColor: v.bg, borderColor: v.border, opacity: pressed ? 0.7 : disabled ? 0.5 : 1 },
      ]}
    >
      {loading ? (
        <ActivityIndicator color={v.fg} />
      ) : (
        <Text style={[styles.label, { color: v.fg }]}>{title}</Text>
      )}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  btn: {
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.lg,
    borderRadius: radius.md,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  label: { fontWeight: '600', fontSize: 15 },
});
