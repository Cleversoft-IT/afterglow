import { Ionicons } from '@expo/vector-icons';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { colors } from '../lib/theme';

export type CallButtonVariant = 'accept' | 'ai' | 'decline';

type Spec = {
  bg: string;
  shadow: string;
  icon: React.ComponentProps<typeof Ionicons>['name'];
  rotate?: string;
  label: string;
  size: number;
};

const SPECS: Record<CallButtonVariant, Spec> = {
  accept: {
    bg: '#22c55e',
    shadow: '#16a34a',
    icon: 'call',
    label: 'Human',
    size: 64,
  },
  ai: {
    bg: colors.brand,
    shadow: colors.brandStrong,
    icon: 'sparkles',
    label: 'Afterglow',
    size: 80,
  },
  decline: {
    bg: '#ef4444',
    shadow: '#b91c1c',
    icon: 'call',
    rotate: '135deg',
    label: 'Decline',
    size: 64,
  },
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
  const spec = SPECS[variant];
  const iconSize = Math.round(spec.size * 0.45);

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
            shadowColor: spec.shadow,
            opacity: disabled ? 0.4 : pressed ? 0.85 : 1,
            transform: [{ scale: pressed ? 0.95 : 1 }],
          },
        ]}
      >
        <View style={spec.rotate ? { transform: [{ rotate: spec.rotate }] } : undefined}>
          <Ionicons name={spec.icon} size={iconSize} color="#fff" />
        </View>
      </Pressable>
      <Text style={styles.label}>{spec.label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  column: { alignItems: 'center', gap: 8 },
  button: {
    alignItems: 'center',
    justifyContent: 'center',
    shadowOpacity: 0.5,
    shadowRadius: 18,
    shadowOffset: { width: 0, height: 6 },
    elevation: 10,
  },
  label: {
    color: colors.textMuted,
    fontSize: 11,
    fontWeight: '600',
    letterSpacing: 0.5,
    textTransform: 'uppercase',
  },
});
