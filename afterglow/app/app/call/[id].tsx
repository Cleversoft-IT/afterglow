import { useLocalSearchParams, useRouter } from 'expo-router';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';
import {
  ActivityIndicator,
  Avatar,
  Banner,
  Button,
  Card,
  Chip,
  Divider,
  IconButton,
  type MD3Theme,
  Text,
  useTheme,
} from 'react-native-paper';
import { api, ApiError } from '../../lib/api';
import { ContactAvatar } from '../../components/ContactAvatar';
import type { CallDetailView, FieldDefinitionLite } from '../../lib/types';

function statusChip(status: string, theme: MD3Theme): {
  label: string;
  style: { backgroundColor: string };
  textColor: string;
} {
  if (status === 'completed') {
    return {
      label: status,
      style: { backgroundColor: theme.colors.tertiaryContainer },
      textColor: theme.colors.onTertiaryContainer,
    };
  }
  if (status === 'failed') {
    return {
      label: status,
      style: { backgroundColor: theme.colors.errorContainer },
      textColor: theme.colors.onErrorContainer,
    };
  }
  return {
    label: status,
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
  const theme = useTheme();
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

  const callerDisplay = call.customer?.display_name ?? call.phone_e164;
  const sc = statusChip(call.status, theme);
  const extracted = call.extracted;

  return (
    <ScrollView contentContainerStyle={styles.scroll}>
      <Card mode="elevated">
        <Card.Title
          title={callerDisplay}
          subtitle={`${call.phone_e164}${call.detected_language ? ` · ${call.detected_language}` : ''}`}
          left={() => <ContactAvatar phone={call.phone_e164} name={callerDisplay} size={48} />}
          right={() => (
            <Chip mode="flat" compact style={[{ marginRight: 12 }, sc.style]} textStyle={{ color: sc.textColor }}>
              {sc.label}
            </Chip>
          )}
        />
        <Card.Content>
          <Text variant="bodySmall" style={{ color: theme.colors.onSurfaceVariant }}>
            {new Date(call.created_at).toLocaleString()}
          </Text>
          {call.error ? (
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
                      <Text variant="labelSmall" style={{ fontFamily: 'monospace', color: theme.colors.onSurfaceVariant }}>
                        {k}
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
              const isSimulated = a.is_simulated ?? a.result?.mock === true;
              const canUndo = a.can_undo ?? false;
              return (
                <View key={a.id}>
                  {i > 0 ? <Divider style={{ marginVertical: 8 }} /> : null}
                  <View style={styles.actionRow}>
                    <View style={{ flex: 1, gap: 4 }}>
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
                      <Text
                        variant="labelSmall"
                        style={{ fontFamily: 'monospace', color: theme.colors.onSurfaceVariant }}
                      >
                        {a.action_type}
                      </Text>
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

      {call.raw_transcript?.text ? (
        <Card mode="elevated">
          <Card.Title title="Transcript" />
          <Card.Content>
            <Text variant="bodyMedium" style={{ color: theme.colors.onSurfaceVariant, lineHeight: 20 }}>
              {call.raw_transcript.text}
            </Text>
          </Card.Content>
        </Card>
      ) : null}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  scroll: { padding: 16, gap: 16, paddingBottom: 48 },
  chipRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginBottom: 12 },
  fieldRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: 12,
    paddingVertical: 8,
  },
  actionRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  actionHeader: { flexDirection: 'row', alignItems: 'center', gap: 8, flexWrap: 'wrap' },
});
