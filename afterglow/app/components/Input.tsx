import { useMemo } from 'react';
import { StyleSheet, TextInput, TextInputProps } from 'react-native';
import { useTheme } from '../lib/ThemeContext';
import { radius, spacing } from '../lib/theme';

export function Input({ style, ...rest }: TextInputProps) {
  const { colors } = useTheme();
  const styles = useMemo(
    () =>
      StyleSheet.create({
        input: {
          backgroundColor: colors.surface,
          borderColor: colors.border,
          borderWidth: 1,
          borderRadius: radius.lg,
          color: colors.text,
          paddingHorizontal: spacing.lg,
          paddingVertical: spacing.md + 2,
          fontSize: 15,
          minHeight: 48,
        },
      }),
    [colors],
  );

  return (
    <TextInput placeholderTextColor={colors.textSubtle} {...rest} style={[styles.input, style]} />
  );
}
