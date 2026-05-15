import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native';
import { colors } from '../lib/theme';

// The "tasto blu" — the single most important action in the demo. Tapping it
// uploads the active template's audio to the backend and starts the post-call
// pipeline. Visual style mimics a phone Answer button.

export function BlueCallButton({
  onPress,
  busy,
  disabled,
}: {
  onPress: () => void;
  busy?: boolean;
  disabled?: boolean;
}) {
  return (
    <Pressable
      onPress={onPress}
      disabled={busy || disabled}
      style={({ pressed }) => [
        styles.outer,
        { opacity: pressed ? 0.85 : disabled ? 0.5 : 1, transform: [{ scale: pressed ? 0.98 : 1 }] },
      ]}
    >
      <View style={styles.inner}>
        {busy ? (
          <ActivityIndicator color="#fff" size="large" />
        ) : (
          <Text style={styles.icon}>📞</Text>
        )}
      </View>
      <Text style={styles.caption}>{busy ? 'Processing…' : 'Answer & analyze'}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  outer: { alignItems: 'center', gap: 12 },
  inner: {
    width: 120,
    height: 120,
    borderRadius: 60,
    backgroundColor: colors.brand,
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: colors.brand,
    shadowOpacity: 0.5,
    shadowRadius: 20,
    shadowOffset: { width: 0, height: 8 },
    elevation: 12,
  },
  icon: { fontSize: 52, color: '#fff' },
  caption: { color: colors.textMuted, fontSize: 13, letterSpacing: 0.5, textTransform: 'uppercase' },
});
