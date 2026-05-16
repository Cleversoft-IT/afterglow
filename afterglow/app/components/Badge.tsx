import { useMemo } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { useTheme } from '../lib/ThemeContext';
import { radius, spacing, type ColorPalette } from '../lib/theme';

type Tone = 'neutral' | 'success' | 'warning' | 'danger' | 'brand';

function toneColors(colors: ColorPalette): Record<Tone, { bg: string; fg: string }> {
  return {
    neutral: { bg: colors.surfaceAlt, fg: colors.textMuted },
    success: { bg: 'rgba(16, 163, 127, 0.1)', fg: colors.success },
    warning: { bg: 'rgba(180, 83, 9, 0.1)', fg: colors.warning },
    danger: { bg: 'rgba(196, 30, 58, 0.08)', fg: colors.danger },
    brand: { bg: colors.infoBg, fg: colors.callAfterglow },
  };
}

export function Badge({ tone = 'neutral', children }: { tone?: Tone; children: string }) {
  const { colors, isDark } = useTheme();
  const palette = useMemo(() => {
    const base = toneColors(colors);
    if (!isDark) return base;
    return {
      ...base,
      success: { bg: 'rgba(52, 211, 153, 0.15)', fg: colors.success },
      warning: { bg: 'rgba(251, 191, 36, 0.15)', fg: colors.warning },
      danger: { bg: 'rgba(248, 113, 113, 0.15)', fg: colors.danger },
    };
  }, [colors, isDark]);

  const styles = useMemo(
    () =>
      StyleSheet.create({
        wrap: {
          alignSelf: 'flex-start',
          paddingHorizontal: spacing.sm + 2,
          paddingVertical: 3,
          borderRadius: radius.pill,
        },
        text: {
          fontSize: 12,
          fontWeight: '500',
          letterSpacing: 0.1,
        },
      }),
    [],
  );

  const t = palette[tone];
  return (
    <View style={[styles.wrap, { backgroundColor: t.bg }]}>
      <Text style={[styles.text, { color: t.fg }]}>{children}</Text>
    </View>
  );
}
