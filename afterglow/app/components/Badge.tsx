import { Chip, useTheme } from 'react-native-paper';
import type { ReactNode } from 'react';

type Tone = 'neutral' | 'success' | 'warning' | 'danger' | 'brand';

export function Badge({
  tone = 'neutral',
  children,
}: {
  tone?: Tone;
  children: ReactNode;
}) {
  const theme = useTheme();
  const colorByTone: Record<Tone, { bg: string; fg: string }> = {
    neutral: { bg: theme.colors.surfaceVariant, fg: theme.colors.onSurfaceVariant },
    success: { bg: theme.colors.tertiaryContainer, fg: theme.colors.onTertiaryContainer },
    warning: { bg: theme.colors.secondaryContainer, fg: theme.colors.onSecondaryContainer },
    danger: { bg: theme.colors.errorContainer, fg: theme.colors.onErrorContainer },
    brand: { bg: theme.colors.primaryContainer, fg: theme.colors.onPrimaryContainer },
  };
  const c = colorByTone[tone];
  return (
    <Chip
      compact
      mode="flat"
      style={{ backgroundColor: c.bg, alignSelf: 'flex-start' }}
      textStyle={{ color: c.fg, fontSize: 12 }}
    >
      {children as string}
    </Chip>
  );
}
