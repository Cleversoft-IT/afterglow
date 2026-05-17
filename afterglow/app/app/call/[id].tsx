import { useLocalSearchParams, useRouter } from 'expo-router';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';
import {
  ActivityIndicator,
  Banner,
  Button,
  Card,
  Chip,
  Divider,
  Text,
  useTheme,
} from 'react-native-paper';
import { api, ApiError } from '../../lib/api';
import { ContactAvatar } from '../../components/ContactAvatar';
import { TranscriptList } from '../../components/TranscriptList';
import { resolveFromCallDetail } from '../../lib/callerResolver';
import { formatDateTime } from '../../lib/dateFormat';
import { flagFromE164 } from '../../lib/flagFromE164';
import { useLocale } from '../../lib/LocaleContext';
import type { AppTheme } from '../../lib/paperTheme';
import type { CallDetailView, FieldDefinitionLite } from '../../lib/types';

// Action types whose side effect lives on the operator's own device (the
// booking happens inside Afterglow itself, not against an external CRM).
// We don't want the UI to flag them as "Simulated" even though the backend
// catalog classifies them as `mock_external` — that classification is
// pipeline-internal, not user-facing.
const REAL_ON_DEVICE = new Set([
  'booking.create',
  'appointment.create',
  'appointment.create_inspection',
]);

function statusChip(call: CallDetailView, theme: AppTheme): {
  label: string;
  icon: string;
  style: { backgroundColor: string };
  textColor: string;
} {
  if (call.status === 'completed') {
    return {
      label: 'Completed',
      icon: 'check-circle-outline',
      style: { backgroundColor: theme.colors.successContainer },
      textColor: theme.colors.onSuccessContainer,
    };
  }
  if (call.status === 'failed') {
    // `failure_kind` is server-computed (see backend/app/api/calls.py).
    // We treat the legacy/null case as 'missed' so older fixture data
    // keeps rendering with the friendlier label.
    if (call.failure_kind === 'pipeline_error') {
      return {
        label: 'Pipeline error',
        icon: 'alert-circle-outline',
        style: { backgroundColor: theme.colors.errorContainer },
        textColor: theme.colors.onErrorContainer,
      };
    }
    return {
      label: 'Missed',
      icon: 'phone-missed',
      style: { backgroundColor: theme.colors.secondaryContainer },
      textColor: theme.colors.onSecondaryContainer,
    };
  }
  if (call.status === 'transcribing' || call.status === 'analyzing') {
    return {
      label: 'Analyzing…',
      icon: 'progress-clock',
      style: { backgroundColor: theme.colors.secondaryContainer },
      textColor: theme.colors.onSecondaryContainer,
    };
  }
  const label = call.status
    ? call.status[0].toUpperCase() + call.status.slice(1)
    : '';
  return {
    label,
    icon: 'progress-clock',
    style: { backgroundColor: theme.colors.secondaryContainer },
    textColor: theme.colors.onSecondaryContainer,
  };
}

function formatValue(v: unknown): string {
  if (v == null) return '—';
  if (Array.isArray(v)) return v.join(', ');
  if (typeof v === 'object') return JSON.stringify(v);
  return String(v);
}

export default function CallDetailScreen() {
  const theme = useTheme<AppTheme>();
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const { locale } = useLocale();
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

  const labelByKey = useMemo(() => {
    const out: Record<string, FieldDefinitionLite> = {};
    for (const def of call?.extracted?.field_definitions ?? []) out[def.key] = def;
    return out;
  }, [call]);

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

  if (loading) {
    return (
      <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center' }}>
        <ActivityIndicator />
      </View>
    );
  }
  if (error || !call) {
    return (
      <Banner visible icon="alert-circle-outline" actions={[{ label: 'Retry', onPress: load }]}>
        {error ?? 'Call not found.'}
      </Banner>
    );
  }

  const resolvedCaller = resolveFromCallDetail(call);
  const callerDisplay = resolvedCaller.display_name;
  const sc = statusChip(call, theme);
  const extracted = call.extracted;
  const flag = flagFromE164(call.phone_e164);

  return (
    <ScrollView contentContainerStyle={styles.scroll}>
      <Card mode="elevated">
        <Card.Title
          title={callerDisplay}
          titleVariant="titleMedium"
          subtitle={
            <View style={styles.subtitleRow}>
              <Text style={{ fontSize: 18 }}>{flag}</Text>
              <Text variant="bodyMedium" style={{ color: theme.colors.onSurfaceVariant }}>
                {call.phone_e164}
              </Text>
              {call.detected_language ? (
                <Chip compact mode="outlined">{call.detected_language}</Chip>
              ) : null}
            </View>
          }
          left={() => (
            <ContactAvatar
              phone={call.phone_e164}
              name={callerDisplay}
              avatarUrl={resolvedCaller.avatar_url}
              size={56}
            />
          )}
          leftStyle={{ marginRight: 16 }}
          right={() => (
            <Chip
              mode="flat"
              compact
              icon={sc.icon}
              style={[{ marginRight: 12 }, sc.style]}
              textStyle={{ color: sc.textColor }}
            >
              {sc.label}
            </Chip>
          )}
        />
        <Card.Content>
          <Text variant="bodySmall" style={{ color: theme.colors.onSurfaceVariant }}>
            {formatDateTime(call.created_at, locale)}
          </Text>
          {call.error && call.failure_kind === 'pipeline_error' ? (
            <Text variant="bodySmall" style={{ color: theme.colors.error, marginTop: 8 }}>
              {call.error}
            </Text>
          ) : null}
        </Card.Content>
        {call.customer_id ? (
          <Card.Actions>
            <Button
              mode="text"
              icon="account-circle-outline"
              onPress={() => router.push(`/customer/${call.customer_id}` as never)}
            >
              Open contact
            </Button>
          </Card.Actions>
        ) : null}
      </Card>

      {extracted ? (
        <Card mode="elevated">
          <Card.Title title="Extracted" />
          <Card.Content>
            <View style={styles.chipRow}>
              {extracted.intent ? (
                <Chip mode="flat" compact icon="target">{`intent · ${extracted.intent}`}</Chip>
              ) : null}
              {extracted.sentiment ? (
                <Chip mode="flat" compact icon="emoticon-outline">{`sentiment · ${extracted.sentiment}`}</Chip>
              ) : null}
              {extracted.urgency ? (
                <Chip mode="flat" compact icon="clock-alert-outline">{`urgency · ${extracted.urgency}`}</Chip>
              ) : null}
            </View>
            {Object.entries(extracted.fields).map(([k, v], i) => {
              const def = labelByKey[k];
              return (
                <View key={k}>
                  {i > 0 ? <Divider /> : null}
                  <View style={styles.fieldRow}>
                    <View style={{ flex: 1 }}>
                      <Text variant="bodyMedium" style={{ fontWeight: '600' }}>
                        {def?.label ?? k}
                      </Text>
                    </View>
                    <Text variant="bodyMedium" style={{ flex: 1, textAlign: 'right' }}>
                      {formatValue(v)}
                    </Text>
                  </View>
                </View>
              );
            })}
          </Card.Content>
        </Card>
      ) : null}

      {call.executed_actions.length > 0 ? (
        <Card mode="elevated">
          <Card.Title title={`Actions (${call.executed_actions.length})`} />
          <Card.Content>
            {call.executed_actions.map((a, i) => {
              const isUndone = a.status === 'undone' || a.status === 'reverted';
              const isSimulated = REAL_ON_DEVICE.has(a.action_type)
                ? false
                : (a.is_simulated ?? a.result?.mock === true);
              const canUndo = a.can_undo ?? false;
              return (
                <View key={a.id}>
                  {i > 0 ? <Divider style={{ marginVertical: 12 }} /> : null}
                  <View style={styles.actionRow}>
                    <View style={{ flex: 1, gap: 6 }}>
                      <View style={styles.actionHeader}>
                        <Text variant="bodyLarge" style={{ fontWeight: '600' }}>
                          {a.title}
                        </Text>
                        {isSimulated ? (
                          <Chip mode="outlined" compact icon="record-circle-outline">
                            Simulated
                          </Chip>
                        ) : null}
                      </View>
                      {a.summary ? (
                        <Text variant="bodySmall" style={{ color: theme.colors.onSurfaceVariant }}>
                          {a.summary}
                        </Text>
                      ) : null}
                    </View>
                    {isUndone && canUndo ? (
                      <Button
                        mode="text"
                        icon="redo"
                        loading={busyAction === a.id}
                        onPress={() => redo(a.id)}
                      >
                        Redo
                      </Button>
                    ) : isUndone ? (
                      <Chip mode="flat" compact icon="cancel">
                        Undone
                      </Chip>
                    ) : canUndo ? (
                      <Button
                        mode="text"
                        icon="undo"
                        loading={busyAction === a.id}
                        onPress={() => undo(a.id)}
                      >
                        Undo
                      </Button>
                    ) : null}
                  </View>
                </View>
              );
            })}
          </Card.Content>
        </Card>
      ) : null}

      {call.raw_transcript?.text ? <TranscriptList text={call.raw_transcript.text} /> : null}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  scroll: { padding: 16, gap: 20, paddingBottom: 48 },
  chipRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginBottom: 12 },
  fieldRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: 12,
    paddingVertical: 10,
  },
  actionRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 16,
  },
  actionHeader: { flexDirection: 'row', alignItems: 'center', gap: 8, flexWrap: 'wrap' },
  subtitleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    flexWrap: 'wrap',
    marginTop: 2,
  },
});
