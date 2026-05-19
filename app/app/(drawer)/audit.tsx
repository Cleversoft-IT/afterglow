import { DrawerActions } from '@react-navigation/native';
import { router, useFocusEffect, useNavigation } from 'expo-router';
import { useCallback, useMemo, useState } from 'react';
import { Pressable, RefreshControl, ScrollView, StyleSheet, View } from 'react-native';
import {
  ActivityIndicator,
  Appbar,
  Avatar,
  Banner,
  Chip,
  IconButton,
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

// Status priority: error > degraded > skipped > success > other. The call
// card header uses this to surface the worst step's color even when the
// other steps under it were fine.
const STATUS_RANK: Record<string, number> = {
  error: 4,
  degraded: 3,
  skipped: 2,
  success: 1,
};

function worstStatus(entries: AuditLogEntry[]): string {
  let best = 'success';
  let bestRank = -1;
  for (const e of entries) {
    const rank = STATUS_RANK[e.status] ?? 0;
    if (rank > bestRank) {
      bestRank = rank;
      best = e.status;
    }
  }
  return best;
}

function statusVisuals(
  status: string,
  theme: AppTheme,
): { icon: string; bg: string; fg: string } {
  if (status === 'success') {
    return { icon: 'check', bg: theme.colors.successContainer, fg: theme.colors.onSuccessContainer };
  }
  if (status === 'error') {
    return { icon: 'alert-circle', bg: theme.colors.errorContainer, fg: theme.colors.onErrorContainer };
  }
  if (status === 'skipped' || status === 'degraded') {
    return {
      icon: 'skip-next-circle-outline',
      bg: theme.colors.secondaryContainer,
      fg: theme.colors.onSecondaryContainer,
    };
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
    <Surface mode="flat" style={[styles.summary, { backgroundColor: theme.colors.surfaceVariant }]}>
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

function SummaryCell({ label, value, theme }: { label: string; value: string; theme: AppTheme }) {
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

type CallGroup = {
  callId: string;
  displayName: string;
  phoneE164: string | null;
  callStatus: string | null;
  worstStatus: string;
  totalDurationMs: number;
  totalTokens: number;
  stepCount: number;
  // entries grouped by agent_name, then sorted chronologically (asc) within agent.
  byAgent: { agentName: string; entries: AuditLogEntry[] }[];
  createdAt: string; // earliest createdAt in the group; used for the header timestamp.
};

function groupByCall(rows: AuditLogEntry[]): {
  groups: CallGroup[];
  orphans: AuditLogEntry[];
} {
  const map = new Map<string, AuditLogEntry[]>();
  const orphans: AuditLogEntry[] = [];

  for (const r of rows) {
    if (!r.call_id) {
      orphans.push(r);
      continue;
    }
    const list = map.get(r.call_id) ?? [];
    list.push(r);
    map.set(r.call_id, list);
  }

  const groups: CallGroup[] = [];
  for (const [callId, entries] of map.entries()) {
    // Group by agent_name (preserving the first-seen order, which mirrors
    // the pipeline order because the orchestrator emits chronologically).
    const agentOrder: string[] = [];
    const byAgent: Record<string, AuditLogEntry[]> = {};
    for (const e of entries) {
      if (!byAgent[e.agent_name]) {
        byAgent[e.agent_name] = [];
        agentOrder.push(e.agent_name);
      }
      byAgent[e.agent_name].push(e);
    }
    // Sort each agent's steps by created_at asc so the leaf list reads
    // top-to-bottom in pipeline order.
    for (const k of agentOrder) {
      byAgent[k].sort((a, b) =>
        a.created_at < b.created_at ? -1 : a.created_at > b.created_at ? 1 : 0,
      );
    }

    let totalDurationMs = 0;
    let totalTokens = 0;
    for (const e of entries) {
      if (typeof e.duration_ms === 'number') totalDurationMs += e.duration_ms;
      if (typeof e.input_tokens === 'number') totalTokens += e.input_tokens;
      if (typeof e.output_tokens === 'number') totalTokens += e.output_tokens;
    }

    const first = entries.reduce((a, b) => (a.created_at < b.created_at ? a : b));

    groups.push({
      callId,
      displayName: first.call_display_name ?? first.call_phone_e164 ?? callId.slice(0, 8),
      phoneE164: first.call_phone_e164 ?? null,
      callStatus: first.call_status ?? null,
      worstStatus: worstStatus(entries),
      totalDurationMs,
      totalTokens,
      stepCount: entries.length,
      byAgent: agentOrder.map((name) => ({ agentName: name, entries: byAgent[name] })),
      createdAt: first.created_at,
    });
  }

  // Newest call group first — matches the DESC ordering of the raw list.
  groups.sort((a, b) => (a.createdAt < b.createdAt ? 1 : -1));
  return { groups, orphans };
}

function StepLeaf({
  entry,
  theme,
  locale,
  expanded,
  onTogglePayload,
}: {
  entry: AuditLogEntry;
  theme: AppTheme;
  locale: 'it' | 'en';
  expanded: boolean;
  onTogglePayload: () => void;
}) {
  const v = statusVisuals(entry.status, theme);
  const humanLabel = humanLabelFromPayload(entry.payload ?? undefined);
  const time = formatTimeWithSeconds(entry.created_at, locale);
  const hasPayload = entry.payload && Object.keys(entry.payload).length > 0;

  return (
    <View style={styles.leafContainer}>
      <View style={styles.leafHeader}>
        <Avatar.Icon
          icon={v.icon}
          size={28}
          color={v.fg}
          style={{ backgroundColor: v.bg }}
        />
        <View style={{ flex: 1, gap: 4 }}>
          <View style={styles.leafChips}>
            <Chip compact mode="flat" style={{ backgroundColor: v.bg }} textStyle={{ color: v.fg, fontSize: 11 }}>
              {entry.status}
            </Chip>
            <Chip compact mode="outlined" textStyle={{ fontSize: 11 }}>
              {friendlyStepLabel(entry.step_type)}
            </Chip>
            {entry.model ? (
              <Chip compact mode="outlined" textStyle={{ fontSize: 11 }}>
                {entry.model}
              </Chip>
            ) : null}
            <Text
              variant="labelSmall"
              style={{ color: theme.colors.onSurfaceVariant, fontFamily: 'monospace' }}
            >
              {time}
            </Text>
            {entry.duration_ms != null ? (
              <Text
                variant="labelSmall"
                style={{ color: theme.colors.onSurfaceVariant, fontFamily: 'monospace' }}
              >
                · {entry.duration_ms}ms
              </Text>
            ) : null}
          </View>
          {humanLabel ? <Text variant="bodySmall">{humanLabel}</Text> : null}
          {entry.input_tokens != null || entry.output_tokens != null ? (
            <Text
              variant="labelSmall"
              style={{ color: theme.colors.onSurfaceVariant, fontFamily: 'monospace' }}
            >
              {entry.input_tokens ?? 0} in · {entry.output_tokens ?? 0} out tokens
            </Text>
          ) : null}
          {entry.error ? (
            <Text variant="bodySmall" style={{ color: theme.colors.error }}>
              {entry.error}
            </Text>
          ) : null}
        </View>
      </View>
      <Pressable
        onPress={hasPayload ? onTogglePayload : undefined}
        disabled={!hasPayload}
        style={{ opacity: hasPayload ? 1 : 0.4, alignSelf: 'flex-start' }}
      >
        <Text
          variant="labelSmall"
          style={{ color: theme.colors.primary, marginLeft: 36, marginTop: 4 }}
        >
          {!hasPayload ? '(no payload)' : expanded ? '▾ Hide payload' : '▸ Show payload'}
        </Text>
      </Pressable>
      {hasPayload && expanded ? (
        <Surface mode="flat" style={[styles.payloadSurface, { backgroundColor: theme.colors.surfaceVariant }]}>
          <Text variant="bodySmall" style={styles.payloadText} selectable>
            {JSON.stringify(entry.payload, null, 2)}
          </Text>
        </Surface>
      ) : null}
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
  const [expandedPayloads, setExpandedPayloads] = useState<Set<string>>(() => new Set());

  const load = useCallback(async () => {
    try {
      setError(null);
      const data = await api.listAudit({ limit: 500 });
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
  const { groups, orphans } = useMemo(() => groupByCall(rows), [rows]);

  const togglePayload = useCallback((id: string) => {
    setExpandedPayloads((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

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

      <ScrollView
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
      >
        {rows.length > 0 ? <SummaryBanner totals={totals} theme={theme} /> : null}

        {groups.length === 0 && orphans.length === 0 ? (
          <View style={{ paddingTop: 64, alignItems: 'center' }}>
            <Text variant="bodyMedium" style={{ color: theme.colors.onSurfaceVariant }}>
              No audit entries yet.
            </Text>
          </View>
        ) : null}

        {groups.map((group) => {
          const v = statusVisuals(group.worstStatus, theme);
          const tokensLabel =
            group.totalTokens > 0 ? `· ${group.totalTokens.toLocaleString()} tokens` : '';
          const durationLabel =
            group.totalDurationMs > 0 ? `· ${formatDuration(group.totalDurationMs)}` : '';
          const description = `${group.stepCount} step${group.stepCount === 1 ? '' : 's'} ${durationLabel} ${tokensLabel}`.trim();
          return (
            <List.Accordion
              key={group.callId}
              title={group.displayName}
              description={description}
              left={() => (
                <Avatar.Icon
                  icon={v.icon}
                  size={40}
                  color={v.fg}
                  style={{ backgroundColor: v.bg, marginLeft: 8 }}
                />
              )}
              right={(props) => (
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 4 }}>
                  {group.callStatus ? (
                    <Chip compact mode="outlined" textStyle={{ fontSize: 11 }}>
                      {group.callStatus}
                    </Chip>
                  ) : null}
                  <IconButton
                    {...props}
                    icon="open-in-new"
                    size={18}
                    onPress={() => router.push(`/call/${group.callId}`)}
                  />
                </View>
              )}
              style={styles.callAccordion}
            >
              {group.byAgent.map((agentGroup) => (
                <List.Accordion
                  key={`${group.callId}:${agentGroup.agentName}`}
                  title={friendlyAgentLabel(agentGroup.agentName)}
                  description={agentGroup.entries.map((e) => friendlyStepLabel(e.step_type)).join(' · ')}
                  style={styles.agentAccordion}
                >
                  {agentGroup.entries.map((entry) => (
                    <StepLeaf
                      key={entry.id}
                      entry={entry}
                      theme={theme}
                      locale={locale}
                      expanded={expandedPayloads.has(entry.id)}
                      onTogglePayload={() => togglePayload(entry.id)}
                    />
                  ))}
                </List.Accordion>
              ))}
            </List.Accordion>
          );
        })}

        {orphans.length > 0 ? (
          <List.Accordion
            title={`System events (${orphans.length})`}
            left={(props) => <List.Icon {...props} icon="cog-outline" />}
            style={styles.callAccordion}
          >
            {orphans.map((entry) => (
              <StepLeaf
                key={entry.id}
                entry={entry}
                theme={theme}
                locale={locale}
                expanded={expandedPayloads.has(entry.id)}
                onTogglePayload={() => togglePayload(entry.id)}
              />
            ))}
          </List.Accordion>
        ) : null}

        <View style={{ height: 32 }} />
      </ScrollView>
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
  callAccordion: {
    marginHorizontal: 8,
  },
  agentAccordion: {
    marginLeft: 24,
  },
  leafContainer: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    marginLeft: 24,
    gap: 4,
  },
  leafHeader: {
    flexDirection: 'row',
    gap: 8,
    alignItems: 'flex-start',
  },
  leafChips: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 4,
    alignItems: 'center',
  },
  payloadSurface: {
    marginLeft: 36,
    marginTop: 4,
    borderRadius: 8,
    padding: 10,
  },
  payloadText: {
    fontFamily: 'monospace',
  },
});
