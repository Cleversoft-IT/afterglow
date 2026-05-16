import { useFocusEffect } from 'expo-router';
import { useCallback, useMemo, useState } from 'react';
import { ActivityIndicator, FlatList, RefreshControl, StyleSheet, Text, View } from 'react-native';
import { Badge } from '../components/Badge';
import { Card } from '../components/Card';
import { api, ApiError } from '../lib/api';
import {
  friendlyAgentLabel,
  friendlyStepLabel,
  humanLabelFromPayload,
} from '../lib/auditLabels';
import { useTheme } from '../lib/ThemeContext';
import { spacing } from '../lib/theme';
import type { AuditLogEntry } from '../lib/types';

function toneFor(status: string): 'success' | 'warning' | 'danger' | 'neutral' {
  if (status === 'success') return 'success';
  if (status === 'error') return 'danger';
  if (status === 'skipped' || status === 'degraded') return 'warning';
  return 'neutral';
}

export default function AuditScreen() {
  const { colors } = useTheme();
  const [rows, setRows] = useState<AuditLogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setError(null);
      const data = await api.listAudit();
      setRows(data);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load]),
  );

  const styles = useMemo(
    () =>
      StyleSheet.create({
        headerRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
        agent: { color: colors.text, fontWeight: '600', fontSize: 15 },
        meta: { color: colors.textMuted, fontSize: 12, marginTop: 2 },
        note: { color: colors.text, fontSize: 12, marginTop: 4 },
        tokens: { color: colors.textSubtle, fontSize: 11, marginTop: 4 },
        empty: {
          color: colors.textMuted,
          textAlign: 'center',
          marginTop: spacing.xxxl,
          fontSize: 15,
          lineHeight: 22,
          paddingHorizontal: spacing.xl,
        },
        errorRow: { color: colors.danger, fontSize: 12, marginTop: 4 },
        error: { color: colors.danger, padding: spacing.lg },
      }),
    [colors],
  );

  if (loading) return <ActivityIndicator color={colors.brand} style={{ marginTop: 32 }} />;
  if (error) return <Text style={styles.error}>{error}</Text>;

  return (
    <FlatList
      data={rows}
      keyExtractor={(r) => r.id}
      contentContainerStyle={{ padding: spacing.lg }}
      refreshControl={
        <RefreshControl
          tintColor={colors.brand}
          refreshing={refreshing}
          onRefresh={() => {
            setRefreshing(true);
            load();
          }}
        />
      }
      ItemSeparatorComponent={() => <View style={{ height: spacing.sm }} />}
      ListEmptyComponent={<Text style={styles.empty}>No audit entries yet.</Text>}
      renderItem={({ item }) => {
        const humanLabel = humanLabelFromPayload(item.payload);
        return (
          <Card>
            <View style={styles.headerRow}>
              <Text style={styles.agent}>{friendlyAgentLabel(item.agent_name)}</Text>
              <Badge tone={toneFor(item.status)}>{item.status}</Badge>
            </View>
            <Text style={styles.meta}>
              {friendlyStepLabel(item.step_type)}
              {item.model ? ` · ${item.model}` : ''}
            </Text>
            {humanLabel ? <Text style={styles.note}>{humanLabel}</Text> : null}
            {item.duration_ms != null ? (
              <Text style={styles.meta}>{item.duration_ms} ms</Text>
            ) : null}
            {item.input_tokens != null || item.output_tokens != null ? (
              <Text style={styles.tokens}>
                {item.input_tokens ?? 0} in · {item.output_tokens ?? 0} out tokens
              </Text>
            ) : null}
            {item.error ? <Text style={styles.errorRow}>{item.error}</Text> : null}
          </Card>
        );
      }}
    />
  );
}
