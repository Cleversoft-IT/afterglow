import { useRouter } from 'expo-router';
import { useEffect, useState } from 'react';
import { ActivityIndicator, ScrollView, StyleSheet, Text, View } from 'react-native';
import { BlueCallButton } from '../components/BlueCallButton';
import { Card } from '../components/Card';
import { api, ApiError } from '../lib/api';
import { resolveAudioBlob, type AudioDomain } from '../lib/audio';
import { colors, spacing } from '../lib/theme';
import type { TemplateView } from '../lib/types';

const DEMO_PHONE_BY_DOMAIN: Record<string, string> = {
  restaurant: '+393331112233',
  dentist: '+393339991122',
  bodyshop: '+393338883344',
};

const POLL_INTERVAL_MS = 1500;
const POLL_TIMEOUT_MS = 30000;

export default function SimulatorScreen() {
  const router = useRouter();
  const [template, setTemplate] = useState<TemplateView | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState<string | null>(null);

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

  const startCall = async () => {
    if (!template) return;
    setBusy(true);
    setError(null);
    setProgress('Loading audio…');
    try {
      const domain = template.domain_hint as AudioDomain;
      const blob = await resolveAudioBlob(domain);
      const phone = DEMO_PHONE_BY_DOMAIN[domain] ?? '+393331112233';
      setProgress('Uploading call…');
      const submitted = await api.submitAudio(blob, phone, `${domain}.mp3`);

      const deadline = Date.now() + POLL_TIMEOUT_MS;
      while (Date.now() < deadline) {
        const detail = await api.getCall(submitted.call_id);
        setProgress(`Call ${detail.status}…`);
        if (detail.status === 'completed' || detail.status === 'failed') {
          router.replace(`/call/${detail.id}`);
          return;
        }
        await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS));
      }
      setError('Pipeline timed out after 30s.');
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setBusy(false);
      setProgress(null);
    }
  };

  if (loading) return <ActivityIndicator color={colors.brand} style={{ marginTop: 32 }} />;

  return (
    <ScrollView contentContainerStyle={styles.scroll}>
      <Card>
        <Text style={styles.heading}>Incoming call</Text>
        {template ? (
          <>
            <Text style={styles.body}>
              Active template: <Text style={styles.bold}>{template.name}</Text> ({template.domain_hint})
            </Text>
            <Text style={styles.body}>
              Tap the blue button to play the demo recording for this sector and run the post-call pipeline.
            </Text>
          </>
        ) : (
          <Text style={styles.body}>
            No active template. Go to Templates and activate one first.
          </Text>
        )}
      </Card>

      <View style={styles.cta}>
        <BlueCallButton onPress={startCall} busy={busy} disabled={!template} />
        {progress ? <Text style={styles.progress}>{progress}</Text> : null}
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
  cta: { alignItems: 'center', paddingVertical: spacing.xl },
  progress: { color: colors.textMuted, marginTop: spacing.md },
  error: { color: colors.danger },
});
