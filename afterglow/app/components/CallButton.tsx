import { Ionicons } from '@expo/vector-icons';
import { useMemo } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useTheme } from '../lib/ThemeContext';

export type CallButtonVariant = 'accept' | 'ai' | 'decline';

type Spec = {
  bg: string;
  icon: React.ComponentProps<typeof Ionicons>['name'];
  rotate?: string;
  label: string;
  size: number;
};

export function CallButton({
  variant,
  onPress,
  disabled,
}: {
  variant: CallButtonVariant;
  onPress: () => void;
  disabled?: boolean;
}) {
  const { colors, shadows } = useTheme();

  const spec: Spec = useMemo(() => {
    const map: Record<CallButtonVariant, Spec> = {
      accept: {
        bg: colors.accentSoft,
        icon: 'call',
        label: 'Human',
        size: 64,
      },
      ai: {
        bg: colors.callAfterglow,
        icon: 'sparkles',
        label: 'Afterglow',
        size: 80,
      },
      decline: {
        bg: colors.danger,
        icon: 'call',
        rotate: '135deg',
        label: 'Decline',
        size: 64,
      },
    };
    return map[variant];
  }, [colors, variant]);

  const styles = useMemo(
    () =>
      StyleSheet.create({
        column: { alignItems: 'center', gap: 10 },
        button: {
          alignItems: 'center',
          justifyContent: 'center',
          ...shadows.raised,
        },
        label: {
          color: colors.textMuted,
          fontSize: 12,
          fontWeight: '500',
        },
      }),
    [colors, shadows],
  );

  const iconSize = Math.round(spec.size * 0.42);

  return (
    <View style={styles.column}>
      <Pressable
        onPress={onPress}
        disabled={disabled}
        accessibilityLabel={spec.label}
        accessibilityRole="button"
        style={({ pressed }) => [
          styles.button,
          {
            width: spec.size,
            height: spec.size,
            borderRadius: spec.size / 2,
            backgroundColor: spec.bg,
            opacity: disabled ? 0.4 : pressed ? 0.9 : 1,
            transform: [{ scale: pressed ? 0.96 : 1 }],
          },
        ]}
      >
        <View style={spec.rotate ? { transform: [{ rotate: spec.rotate }] } : undefined}>
          <Ionicons
            name={spec.icon}
            size={iconSize}
            color={variant === 'ai' ? '#FFFFFF' : colors.onPrimary}
          />
        </View>
      </Pressable>
      <Text style={styles.label}>{spec.label}</Text>
    </View>
  );
}
