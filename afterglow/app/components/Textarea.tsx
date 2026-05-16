import { useMemo } from 'react';
import { StyleSheet, TextInput, TextInputProps } from 'react-native';
import { useTheme } from '../lib/ThemeContext';
import { radius, spacing } from '../lib/theme';

export function Textarea({ style, ...rest }: TextInputProps) {
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
          paddingVertical: spacing.md + 4,
          fontSize: 15,
          lineHeight: 22,
          minHeight: 120,
        },
      }),
    [colors],
  );

  return (
    <TextInput
      placeholderTextColor={colors.textSubtle}
      multiline
      textAlignVertical="top"
      {...rest}
      style={[styles.input, style]}
    />
  );
}
