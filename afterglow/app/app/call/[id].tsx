import { Ionicons } from '@expo/vector-icons';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { Badge } from '../../components/Badge';
import { Button } from '../../components/Button';
import { Card } from '../../components/Card';
import { api, ApiError } from '../../lib/api';
import { useTheme } from '../../lib/ThemeContext';
import { radius, spacing } from '../../lib/theme';
import type { CallDetailView, FieldDefinitionLite } from '../../lib/types';

export default function CallDetailScreen() {
  const { colors } = useTheme();
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const [call, setCall] = useState<CallDetailView | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyAction, setBusyAction] = useState<string | null>(null);

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

  const undo = async (actionId: string) => {
    setBusyAction(actionId);
    try {
      await api.undoAction(actionId);
      await load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setBusyAction(null);
    }
  };

  const redo = async (actionId: string) => {
    setBusyAction(actionId);
    try {
      await api.redoAction(actionId);
      await load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setBusyAction(null);
    }
  };

  const labelByKey = useMemo(() => {
    const out: Record<string, FieldDefinitionLite> = {};
    for (const def of call?.extracted?.field_definitions ?? []) {
      out[def.key] = def;
    }
    return out;
  }, [call]);

  const styles = useMemo(
    () =>
      StyleSheet.create({
        scroll: { padding: spacing.lg, gap: spacing.lg, paddingBottom: spacing.xxxl },
        headerRow: {
          flexDirection: 'row',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: spacing.md,
        },
        callerLink: {
          flexDirection: 'row',
          alignItems: 'center',
          gap: spacing.xs,
          paddingHorizontal: spacing.sm + 2,
          paddingVertical: 5,
          borderRadius: radius.pill,
          backgroundColor: colors.infoBg,
          borderWidth: StyleSheet.hairlineWidth,
          borderColor: colors.infoBorder,
          flexShrink: 1,
        },
        heading: { color: colors.text, fontSize: 16, fontWeight: '600' },
        meta: { color: colors.textMuted, fontSize: 13 },
        errorBanner: {
          color: colors.danger,
          fontSize: 12,
          marginTop: spacing.sm,
          paddingTop: spacing.sm,
          borderTopWidth: StyleSheet.hairlineWidth,
          borderTopColor: colors.border,
        },
        section: { color: colors.text, fontWeight: '600', fontSize: 15, marginBottom: 4 },
        classifyRow: { flexDirection: 'row', gap: 6, flexWrap: 'wrap', marginBottom: spacing.sm },
        fieldRow: {
          flexDirection: 'row',
          justifyContent: 'space-between',
          gap: spacing.md,
          paddingVertical: 6,
          borderTopWidth: StyleSheet.hairlineWidth,
          borderTopColor: colors.border,
        },
        fieldLabel: { color: colors.text, fontSize: 13, fontWeight: '600' },
        fieldKey: { color: colors.textSubtle, fontSize: 10, fontFamily: 'monospace', marginTop: 1 },
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
      }),
    [colors],
  );

  if (loading) return <ActivityIndicator color={colors.brand} style={{ marginTop: 32 }} />;
  if (error || !call) return <Text style={styles.error}>{error ?? 'Call not found.'}</Text>;

  const extracted = call.extracted;
  const callerDisplay = call.customer?.display_name ?? call.phone_e164;

  return (
    <ScrollView contentContainerStyle={styles.scroll}>
      <Card>
        <View style={styles.headerRow}>
          {call.customer_id ? (
            <Pressable
              onPress={() => router.push(`/customer/${call.customer_id}` as never)}
              style={({ pressed }) => [styles.callerLink, pressed && { opacity: 0.7 }]}
            >
              <Ionicons name="person-circle-outline" size={20} color={colors.brand} />
              <Text style={styles.heading}>{callerDisplay}</Text>
              <Ionicons name="chevron-forward" size={16} color={colors.brand} />
            </Pressable>
          ) : (
            <Text style={styles.heading}>{callerDisplay}</Text>
          )}
          <Badge tone={call.status === 'completed' ? 'success' : call.status === 'failed' ? 'danger' : 'warning'}>
            {call.status}
          </Badge>
        </View>
        {call.customer?.display_name ? (
          <Text style={styles.meta}>{call.phone_e164}</Text>
        ) : null}
        <Text style={styles.meta}>
          {new Date(call.created_at).toLocaleString()}
          {call.detected_language ? ` · ${call.detected_language}` : ''}
        </Text>
        {call.error ? <Text style={styles.errorBanner}>{call.error}</Text> : null}
      </Card>

      {extracted ? (
        <Card>
          <Text style={styles.section}>Extracted</Text>
          <View style={styles.classifyRow}>
            {extracted.intent ? <Badge tone="brand">{`intent · ${extracted.intent}`}</Badge> : null}
            {extracted.sentiment ? <Badge>{`sentiment · ${extracted.sentiment}`}</Badge> : null}
            {extracted.urgency ? <Badge tone="warning">{`urgency · ${extracted.urgency}`}</Badge> : null}
          </View>
          {Object.entries(extracted.fields).map(([k, v]) => {
            const def = labelByKey[k];
            return (
              <View key={k} style={styles.fieldRow}>
                <View style={{ flex: 1 }}>
                  <Text style={styles.fieldLabel}>{def?.label ?? k}</Text>
                  <Text style={styles.fieldKey}>{k}</Text>
                </View>
                <Text style={styles.fieldValue}>{formatValue(v)}</Text>
              </View>
            );
          })}
        </Card>
      ) : null}

      {call.executed_actions.length > 0 ? (
        <Card>
          <Text style={styles.section}>Actions ({call.executed_actions.length})</Text>
          {call.executed_actions.map((a) => {
            const isUndone = a.status === 'undone' || a.status === 'reverted';
            const isSimulated = a.is_simulated ?? a.result?.mock === true;
            const canUndo = a.can_undo ?? false;
            return (
              <View key={a.id} style={styles.actionRow}>
                <View style={{ flex: 1, gap: 4 }}>
                  <View style={styles.actionHeader}>
                    <Text style={styles.actionTitle}>{a.title}</Text>
                    {isSimulated ? <Badge tone="brand">Simulated</Badge> : null}
                  </View>
                  <Text style={styles.actionMeta}>{a.action_type}</Text>
                  {a.summary ? <Text style={styles.actionSummary}>{a.summary}</Text> : null}
                </View>
                {isUndone && canUndo ? (
                  <Button
                    title="Redo"
                    variant="secondary"
                    onPress={() => redo(a.id)}
                    loading={busyAction === a.id}
                  />
                ) : isUndone ? (
                  <Badge tone="danger">Undone</Badge>
                ) : canUndo ? (
                  <Button
                    title="Undo"
                    variant="danger"
                    onPress={() => undo(a.id)}
                    loading={busyAction === a.id}
                  />
                ) : null}
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

