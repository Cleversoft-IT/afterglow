import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { Card } from '../components/Card';
import { api, ApiError } from '../lib/api';
import { colors, radius, spacing } from '../lib/theme';
import type { TemplateView } from '../lib/types';

export default function SimulatorScreen() {
  const router = useRouter();
  const [template, setTemplate] = useState<TemplateView | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const t = await api.getActiveTemplate();
        setTemplate(t);
      } catch (e) {
        setError(e instanceof ApiError ? e.message : String(e));
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (loading) return <ActivityIndicator color={colors.brand} style={{ marginTop: 32 }} />;

  return (
    <ScrollView contentContainerStyle={styles.scroll}>
      <Card>
        <Text style={styles.heading}>Incoming call simulator</Text>
        {template ? (
          <>
            <Text style={styles.body}>
              Active template: <Text style={styles.bold}>{template.name}</Text> ({template.domain_hint})
            </Text>
            <Text style={styles.body}>
              Tap the button below to ring the dialer with this sector's demo recording. Pick the blue
              Afterglow handset to let the AI take the call and run the post-call pipeline.
            </Text>
          </>
        ) : (
          <Text style={styles.body}>
            No active template. Go to Templates and activate one first.
          </Text>
        )}
      </Card>

      <View style={styles.cta}>
        <Pressable
          onPress={() => router.push('/incoming-call')}
          disabled={!template}
          style={({ pressed }) => [
            styles.trigger,
            { opacity: !template ? 0.5 : pressed ? 0.85 : 1, transform: [{ scale: pressed ? 0.98 : 1 }] },
          ]}
        >
          <Ionicons name="call" size={22} color="#fff" />
          <Text style={styles.triggerText}>Trigger incoming call</Text>
        </Pressable>
        <Text style={styles.hint}>Plays a ringtone, then the demo recording on accept.</Text>
      </View>

      {error ? (
        <Card>
          <Text style={styles.error}>{error}</Text>
        </Card>
      ) : null}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  scroll: { padding: spacing.lg, gap: spacing.lg },
  heading: { color: colors.text, fontWeight: '700', fontSize: 16 },
  body: { color: colors.textMuted, lineHeight: 20 },
  bold: { color: colors.text, fontWeight: '700' },
  cta: { alignItems: 'center', paddingVertical: spacing.xl, gap: spacing.md },
  trigger: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    backgroundColor: colors.brand,
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.xl,
    borderRadius: radius.pill,
    shadowColor: colors.brand,
    shadowOpacity: 0.5,
    shadowRadius: 16,
    shadowOffset: { width: 0, height: 6 },
    elevation: 8,
  },
  triggerText: { color: '#fff', fontWeight: '700', fontSize: 15, letterSpacing: 0.3 },
  hint: { color: colors.textSubtle, fontSize: 12 },
  error: { color: colors.danger },
});
