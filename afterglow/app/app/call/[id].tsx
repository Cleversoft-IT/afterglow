import { useLocalSearchParams } from 'expo-router';
import { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, ScrollView, StyleSheet, Text, View } from 'react-native';
import { Badge } from '../../components/Badge';
import { Button } from '../../components/Button';
import { Card } from '../../components/Card';
import { api, ApiError } from '../../lib/api';
import { colors, spacing } from '../../lib/theme';
import type { CallDetailView } from '../../lib/types';

export default function CallDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const [call, setCall] = useState<CallDetailView | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reverting, setReverting] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!id) return;
    try {
      setError(null);
      const data = await api.getCall(id);
      setCall(data);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  const revert = async (actionId: string) => {
    setReverting(actionId);
    try {
      await api.revertAction(actionId);
      await load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setReverting(null);
    }
  };

  if (loading) return <ActivityIndicator color={colors.brand} style={{ marginTop: 32 }} />;
  if (error || !call) return <Text style={styles.error}>{error ?? 'Call not found.'}</Text>;

  const extracted = call.extracted;

  return (
    <ScrollView contentContainerStyle={styles.scroll}>
      <Card>
        <View style={styles.headerRow}>
          <Text style={styles.heading}>{call.phone_e164}</Text>
          <Badge tone={call.status === 'completed' ? 'success' : 'warning'}>{call.status}</Badge>
        </View>
        <Text style={styles.meta}>
          {new Date(call.created_at).toLocaleString()}
          {call.detected_language ? ` · ${call.detected_language}` : ''}
        </Text>
      </Card>

      {extracted ? (
        <Card>
          <Text style={styles.section}>Extracted</Text>
          <View style={styles.classifyRow}>
            {extracted.intent ? <Badge tone="brand">{`intent · ${extracted.intent}`}</Badge> : null}
            {extracted.sentiment ? <Badge>{`sentiment · ${extracted.sentiment}`}</Badge> : null}
            {extracted.urgency ? <Badge tone="warning">{`urgency · ${extracted.urgency}`}</Badge> : null}
          </View>
          {Object.entries(extracted.fields).map(([k, v]) => (
            <View key={k} style={styles.fieldRow}>
              <Text style={styles.fieldLabel}>{k}</Text>
              <Text style={styles.fieldValue}>{formatValue(v)}</Text>
            </View>
          ))}
        </Card>
      ) : null}

      {call.executed_actions.length > 0 ? (
        <Card>
          <Text style={styles.section}>Actions ({call.executed_actions.length})</Text>
          {call.executed_actions.map((a) => {
            const isReverted = a.status === 'reverted';
            const isMock = a.result?.mock === true;
            return (
              <View key={a.id} style={styles.actionRow}>
                <View style={{ flex: 1, gap: 4 }}>
                  <View style={styles.actionHeader}>
                    <Text style={styles.actionTitle}>{a.title}</Text>
                    {isMock ? <Badge tone="brand">Simulated</Badge> : null}
                  </View>
                  <Text style={styles.actionMeta}>{a.action_type}</Text>
                  {a.summary ? <Text style={styles.actionSummary}>{a.summary}</Text> : null}
                </View>
                {isReverted ? (
                  <Badge tone="danger">Reverted</Badge>
                ) : (
                  <Button
                    title="Revert"
                    variant="danger"
                    onPress={() => revert(a.id)}
                    loading={reverting === a.id}
                  />
                )}
              </View>
            );
          })}
        </Card>
      ) : null}

      {call.raw_transcript?.text ? (
        <Card>
          <Text style={styles.section}>Transcript</Text>
          <Text style={styles.transcript}>{call.raw_transcript.text}</Text>
        </Card>
      ) : null}
    </ScrollView>
  );
}

function formatValue(v: unknown): string {
  if (v == null) return '—';
  if (Array.isArray(v)) return v.join(', ');
  if (typeof v === 'object') return JSON.stringify(v);
  return String(v);
}

const styles = StyleSheet.create({
  scroll: { padding: spacing.lg, gap: spacing.md },
  headerRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  heading: { color: colors.text, fontSize: 18, fontWeight: '700' },
  meta: { color: colors.textMuted, fontSize: 13 },
  section: { color: colors.text, fontWeight: '700', fontSize: 15, marginBottom: 4 },
  classifyRow: { flexDirection: 'row', gap: 6, flexWrap: 'wrap' },
  fieldRow: { flexDirection: 'row', justifyContent: 'space-between', gap: spacing.md },
  fieldLabel: { color: colors.textMuted, fontSize: 13 },
  fieldValue: { color: colors.text, fontSize: 13, flex: 1, textAlign: 'right' },
  actionRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    paddingVertical: spacing.sm,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.border,
  },
  actionHeader: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm, flexWrap: 'wrap' },
  actionTitle: { color: colors.text, fontWeight: '600' },
  actionMeta: { color: colors.textSubtle, fontSize: 11, fontFamily: 'monospace' },
  actionSummary: { color: colors.textMuted, fontSize: 13 },
  transcript: { color: colors.textMuted, lineHeight: 20, fontSize: 13 },
  error: { color: colors.danger, padding: spacing.lg },
});
