import { DrawerActions } from '@react-navigation/native';
import { router, useFocusEffect, useNavigation } from 'expo-router';
import { useCallback, useMemo, useState } from 'react';
import { FlatList, RefreshControl, StyleSheet, View } from 'react-native';
import {
  ActivityIndicator,
  Appbar,
  Avatar,
  Banner,
  Chip,
  List,
  Surface,
  Text,
  useTheme,
} from 'react-native-paper';
import { api, ApiError } from '../../lib/api';
import {
  friendlyAgentLabel,
  friendlyStepLabel,
  humanLabelFromPayload,
} from '../../lib/auditLabels';
import { formatTimeWithSeconds } from '../../lib/dateFormat';
import { useLocale } from '../../lib/LocaleContext';
import type { AppTheme } from '../../lib/paperTheme';
import type { AuditLogEntry } from '../../lib/types';

function statusVisuals(status: string, theme: AppTheme): { icon: string; bg: string; fg: string } {
  if (status === 'success') {
    return { icon: 'check', bg: theme.colors.successContainer, fg: theme.colors.onSuccessContainer };
  }
  if (status === 'error') {
    return { icon: 'alert-circle', bg: theme.colors.errorContainer, fg: theme.colors.onErrorContainer };
  }
  if (status === 'skipped' || status === 'degraded') {
    return { icon: 'skip-next-circle-outline', bg: theme.colors.secondaryContainer, fg: theme.colors.onSecondaryContainer };
  }
  return { icon: 'circle-outline', bg: theme.colors.surfaceVariant, fg: theme.colors.onSurfaceVariant };
}

type Totals = {
  rows: number;
  durationMs: number;
  inputTokens: number;
  outputTokens: number;
  callCount: number;
};

function aggregate(rows: AuditLogEntry[]): Totals {
  const callIds = new Set<string>();
  let durationMs = 0;
  let inputTokens = 0;
  let outputTokens = 0;
  for (const r of rows) {
    if (r.call_id) callIds.add(r.call_id);
    if (typeof r.duration_ms === 'number') durationMs += r.duration_ms;
    if (typeof r.input_tokens === 'number') inputTokens += r.input_tokens;
    if (typeof r.output_tokens === 'number') outputTokens += r.output_tokens;
  }
  return {
    rows: rows.length,
    durationMs,
    inputTokens,
    outputTokens,
    callCount: callIds.size,
  };
}

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  const seconds = ms / 1000;
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const minutes = Math.floor(seconds / 60);
  const remainder = Math.round(seconds - minutes * 60);
  return `${minutes}m ${remainder}s`;
}

function SummaryBanner({ totals, theme }: { totals: Totals; theme: AppTheme }) {
  const totalTokens = totals.inputTokens + totals.outputTokens;
  return (
    <Surface
      mode="flat"
      style={[styles.summary, { backgroundColor: theme.colors.surfaceVariant }]}
    >
      <View style={styles.summaryRow}>
        <SummaryCell label="Steps" value={String(totals.rows)} theme={theme} />
        <SummaryCell label="Calls" value={String(totals.callCount)} theme={theme} />
        <SummaryCell
          label="Duration"
          value={totals.durationMs > 0 ? formatDuration(totals.durationMs) : '—'}
          theme={theme}
        />
        <SummaryCell
          label="Tokens"
          value={
            totalTokens > 0
              ? `${totals.inputTokens.toLocaleString()} in · ${totals.outputTokens.toLocaleString()} out`
              : '—'
          }
          theme={theme}
        />
      </View>
    </Surface>
  );
}

function SummaryCell({
  label,
  value,
  theme,
}: {
  label: string;
  value: string;
  theme: AppTheme;
}) {
  return (
    <View style={styles.summaryCell}>
      <Text
        variant="labelSmall"
        style={{ color: theme.colors.onSurfaceVariant, textTransform: 'uppercase', letterSpacing: 0.8 }}
      >
        {label}
      </Text>
      <Text variant="titleMedium" style={{ color: theme.colors.onSurface, fontFamily: 'monospace' }}>
        {value}
      </Text>
    </View>
  );
}

export default function AuditScreen() {
  const theme = useTheme<AppTheme>();
  const navigation = useNavigation();
  const { locale } = useLocale();
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

  const totals = useMemo(() => aggregate(rows), [rows]);

  if (loading) {
    return (
      <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center' }}>
        <ActivityIndicator />
      </View>
    );
  }

  return (
    <View style={{ flex: 1, backgroundColor: theme.colors.background }}>
      <Appbar.Header mode="small" elevated={false} style={{ backgroundColor: theme.colors.background }}>
        <Appbar.Action icon="menu" onPress={() => navigation.dispatch(DrawerActions.openDrawer())} />
        <Appbar.Content title="Audit log" />
      </Appbar.Header>

      {error ? (
        <Banner visible icon="alert-circle-outline" actions={[{ label: 'Retry', onPress: load }]}>
          {error}
        </Banner>
      ) : null}

      <FlatList
        data={rows}
        keyExtractor={(r) => r.id}
        ListHeaderComponent={rows.length > 0 ? <SummaryBanner totals={totals} theme={theme} /> : null}
        refreshControl={
          <RefreshControl
            tintColor={theme.colors.primary}
            colors={[theme.colors.primary]}
            refreshing={refreshing}
            onRefresh={() => {
              setRefreshing(true);
              load();
            }}
          />
        }
        renderItem={({ item }) => {
          const v = statusVisuals(item.status, theme);
          const humanLabel = humanLabelFromPayload(item.payload);
          const time = formatTimeWithSeconds(item.created_at, locale);
          const callShort = item.call_id ? item.call_id.slice(0, 8) : null;
          return (
            <List.Item
              title={friendlyAgentLabel(item.agent_name)}
              description={() => (
                <View style={{ gap: 4, marginTop: 2 }}>
                  <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 4, alignItems: 'center' }}>
                    <Chip
                      compact
                      mode="flat"
                      style={{ backgroundColor: v.bg }}
                      textStyle={{ color: v.fg, fontSize: 11 }}
                    >
                      {item.status}
                    </Chip>
                    <Chip compact mode="outlined" textStyle={{ fontSize: 11 }}>
                      {friendlyStepLabel(item.step_type)}
                    </Chip>
                    {item.model ? (
                      <Chip compact mode="outlined" textStyle={{ fontSize: 11 }}>
                        {item.model}
                      </Chip>
                    ) : null}
                    {callShort ? (
                      <Chip
                        compact
                        mode="outlined"
                        icon="phone"
                        textStyle={{ fontSize: 11, fontFamily: 'monospace' }}
                        onPress={() => router.push(`/call/${item.call_id}`)}
                      >
                        {callShort}
                      </Chip>
                    ) : null}
                    <Text
                      variant="labelSmall"
                      style={{ color: theme.colors.onSurfaceVariant, fontFamily: 'monospace' }}
                    >
                      {time}
                    </Text>
                    {item.duration_ms != null ? (
                      <Text
                        variant="labelSmall"
                        style={{ color: theme.colors.onSurfaceVariant, fontFamily: 'monospace' }}
                      >
                        · {item.duration_ms}ms
                      </Text>
                    ) : null}
                  </View>
                  {humanLabel ? (
                    <Text variant="bodySmall">{humanLabel}</Text>
                  ) : null}
                  {item.input_tokens != null || item.output_tokens != null ? (
                    <Text
                      variant="labelSmall"
                      style={{ color: theme.colors.onSurfaceVariant, fontFamily: 'monospace' }}
                    >
                      {item.input_tokens ?? 0} in · {item.output_tokens ?? 0} out tokens
                    </Text>
                  ) : null}
                  {item.error ? (
                    <Text variant="bodySmall" style={{ color: theme.colors.error }}>
                      {item.error}
                    </Text>
                  ) : null}
                </View>
              )}
              left={(p) => (
                <Avatar.Icon
                  {...p}
                  icon={v.icon}
                  size={40}
                  color={v.fg}
                  style={[{ backgroundColor: v.bg }, p.style]}
                />
              )}
            />
          );
        }}
        ListEmptyComponent={
          <View style={{ paddingTop: 64, alignItems: 'center' }}>
            <Text variant="bodyMedium" style={{ color: theme.colors.onSurfaceVariant }}>
              No audit entries yet.
            </Text>
          </View>
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  summary: {
    marginHorizontal: 16,
    marginTop: 8,
    marginBottom: 4,
    borderRadius: 16,
    paddingVertical: 12,
    paddingHorizontal: 16,
  },
  summaryRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    columnGap: 24,
    rowGap: 8,
  },
  summaryCell: {
    minWidth: 80,
    gap: 2,
  },
});
