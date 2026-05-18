import { useLocalSearchParams, useRouter } from 'expo-router';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, View } from 'react-native';
import {
  ActivityIndicator,
  Banner,
  Button,
  Card,
  Chip,
  Dialog,
  Divider,
  IconButton,
  Portal,
  Snackbar,
  Surface,
  Text,
  useTheme,
} from 'react-native-paper';
import { api, ApiError } from '../../lib/api';
import { AgentReasoningTrail } from '../../components/AgentReasoningTrail';
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
const REAL_ON_DEVICE = new Set(['booking.create']);

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
  if (call.status === 'needs_review' || call.review_flag) {
    return {
      label: 'Needs review',
      icon: 'alert-circle-outline',
      style: { backgroundColor: theme.colors.tertiaryContainer },
      textColor: theme.colors.onTertiaryContainer,
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

// Channel labels expand single-token machine values (whatsapp/sms/email/phone)
// into their canonical human-facing form. Anything not in the map falls back
// to a generic single-token capitalization so values like `dinner` or
// `gluten` don't appear as raw lowercase in the operator UI.
const CHANNEL_LABELS: Record<string, string> = {
  whatsapp: 'WhatsApp',
  sms: 'SMS',
  email: 'Email',
  phone: 'Phone',
};

function prettyValue(v: unknown): string {
  if (v == null) return '—';
  if (Array.isArray(v)) return v.map(prettyValue).join(', ');
  if (typeof v === 'object') return JSON.stringify(v);
  const str = String(v);
  const mapped = CHANNEL_LABELS[str.toLowerCase()];
  if (mapped) return mapped;
  // Capitalize single-token all-lowercase strings (`dinner` → `Dinner`).
  // Leave dates, mixed-case, and multi-word strings untouched.
  if (/^[a-z]+$/.test(str)) {
    return str.charAt(0).toUpperCase() + str.slice(1);
  }
  return str;
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
  const [regenDialogVisible, setRegenDialogVisible] = useState(false);
  const [regenerating, setRegenerating] = useState(false);
  const [regenSuccess, setRegenSuccess] = useState(false);

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

  const regenerateBriefing = async () => {
    if (!id) return;
    setRegenDialogVisible(false);
    setRegenerating(true);
    try {
      const updated = await api.regenerateSummary(id);
      setCall(updated);
      setRegenSuccess(true);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setRegenerating(false);
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

  const customerId = call.customer_id;
  const goToCustomer = customerId
    ? () => router.push(`/customer/${customerId}` as never)
    : undefined;
  const customerTags = call.customer?.tags ?? [];

  return (
    <ScrollView contentContainerStyle={styles.scroll}>
      <Card mode="elevated">
        <Card.Content style={styles.headerCard}>
          <Pressable
            onPress={goToCustomer}
            disabled={!goToCustomer}
            style={styles.headerRow}
          >
            <ContactAvatar
              phone={call.phone_e164}
              name={callerDisplay}
              avatarUrl={resolvedCaller.avatar_url}
              size={56}
              isCustomer={resolvedCaller.is_customer}
            />
            <View style={styles.headerText}>
              <Text variant="titleMedium" numberOfLines={1}>
                {callerDisplay}
              </Text>
              <View style={styles.subtitleRow}>
                <Text style={{ fontSize: 18 }}>{flag}</Text>
                <Text variant="bodyMedium" style={{ color: theme.colors.onSurfaceVariant }}>
                  {call.phone_e164}
                </Text>
              </View>
              <Text variant="bodySmall" style={{ color: theme.colors.onSurfaceVariant }}>
                {formatDateTime(call.created_at, locale)}
              </Text>
              {customerTags.length > 0 ? (
                <View style={styles.tagRow}>
                  {customerTags.slice(0, 4).map((t) => (
                    <Chip key={t} mode="outlined" compact>
                      {t}
                    </Chip>
                  ))}
                </View>
              ) : null}
              {call.error && call.failure_kind === 'pipeline_error' ? (
                <Text
                  variant="bodySmall"
                  style={{ color: theme.colors.error, marginTop: 4 }}
                >
                  {call.error}
                </Text>
              ) : null}
            </View>
            <View style={styles.headerRight}>
              <Chip
                mode="flat"
                compact
                icon={sc.icon}
                style={sc.style}
                textStyle={{ color: sc.textColor }}
              >
                {sc.label}
              </Chip>
            </View>
          </Pressable>
        </Card.Content>
      </Card>

      {call.review_flag ? (
        <Banner
          visible
          icon="alert-circle-outline"
          style={{ backgroundColor: theme.colors.tertiaryContainer }}
        >
          {`Needs human review · ${call.review_flag.reason}` +
            (call.review_flag.severity ? ` (${call.review_flag.severity})` : '')}
        </Banner>
      ) : null}

      <AgentReasoningTrail callId={call.id} />

      {extracted ? (
        <Card mode="elevated">
          <Card.Title
            title="Extracted"
            right={(props) => (
              <IconButton
                {...props}
                icon="refresh"
                mode="contained-tonal"
                size={20}
                accessibilityLabel="Regenerate briefing"
                disabled={
                  call.status !== 'completed' || !extracted || regenerating
                }
                loading={regenerating}
                onPress={() => setRegenDialogVisible(true)}
              />
            )}
          />
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
            {extracted.briefing ? (
              <Surface mode="flat" style={styles.briefingSurface}>
                <Text
                  variant="labelSmall"
                  style={{
                    color: theme.colors.onSurfaceVariant,
                    textTransform: 'uppercase',
                    letterSpacing: 0.8,
                    marginBottom: 4,
                  }}
                >
                  Next-call briefing
                </Text>
                <Text variant="bodyMedium" style={{ fontStyle: 'italic' }}>
                  {extracted.briefing}
                </Text>
              </Surface>
            ) : null}
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
                      {prettyValue(v)}
                    </Text>
                  </View>
                </View>
              );
            })}
          </Card.Content>
        </Card>
      ) : call.status === 'needs_review' ? (
        <Card mode="elevated">
          <Card.Content>
            <Text variant="titleMedium" style={{ marginBottom: 6 }}>
              Extracted
            </Text>
            <Text variant="bodySmall" style={{ color: theme.colors.onSurfaceVariant }}>
              Pipeline did not finalize — review the agent trail above.
            </Text>
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

      <Portal>
        <Dialog
          visible={regenDialogVisible}
          onDismiss={() => setRegenDialogVisible(false)}
        >
          <Dialog.Title>Regenerate briefing?</Dialog.Title>
          <Dialog.Content>
            <Text variant="bodyMedium">
              Re-runs the briefing prompt with the current transcript and prior facts.
              Extracted fields and executed actions are unchanged.
            </Text>
          </Dialog.Content>
          <Dialog.Actions>
            <Button onPress={() => setRegenDialogVisible(false)}>Cancel</Button>
            <Button onPress={regenerateBriefing}>Regenerate</Button>
          </Dialog.Actions>
        </Dialog>
        <Snackbar
          visible={regenSuccess}
          onDismiss={() => setRegenSuccess(false)}
          duration={3000}
        >
          Briefing updated
        </Snackbar>
      </Portal>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  scroll: { padding: 16, gap: 20, paddingBottom: 48 },
  chipRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginBottom: 12 },
  briefingSurface: {
    borderRadius: 12,
    paddingVertical: 12,
    paddingHorizontal: 14,
    marginBottom: 12,
  },
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
  headerCard: { padding: 16 },
  headerRow: { flexDirection: 'row', alignItems: 'flex-start', gap: 16 },
  headerText: { flex: 1, gap: 6 },
  headerRight: { alignItems: 'flex-end' },
  subtitleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    flexWrap: 'wrap',
  },
  tagRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
    marginTop: 4,
  },
});
