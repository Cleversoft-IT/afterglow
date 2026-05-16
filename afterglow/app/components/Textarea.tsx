import { StyleSheet, TextInput, TextInputProps } from 'react-native';
import { colors, radius, spacing } from '../lib/theme';

export function Textarea({ style, ...rest }: TextInputProps) {
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

const styles = StyleSheet.create({
  input: {
    backgroundColor: colors.surfaceAlt,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: radius.md,
    color: colors.text,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    fontSize: 14,
    minHeight: 96,
  },
});
