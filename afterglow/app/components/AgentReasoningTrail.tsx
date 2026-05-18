/**
 * AgentReasoningTrail — visualizes the multi-turn agentic post-call loop.
 *
 * Fetches the audit log for this call filtered to `agent_name=call_agent` and
 * `agent_name=action_executor`, then renders the timeline:
 *
 *  - `agent_loop_start` row → header chip with tool surface count.
 *  - `agent_turn` row → numbered entry with tool name, args summary,
 *    result summary, token usage (when present).
 *  - matching `action_exec` row (action_executor, same `payload.agent_turn`)
 *    is nested under the turn that triggered it.
 *  - `agent_loop_end` row → footer with completion_reason + total tokens.
 *
 * Empty state: nothing rendered (the call may pre-date the agentic pipeline).
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { ActivityIndicator, Card, Chip, Text, useTheme } from 'react-native-paper';
import { api, ApiError } from '../lib/api';
import type { AppTheme } from '../lib/paperTheme';
import type { AuditLogEntry } from '../lib/types';

type Props = {
  callId: string;
};

type Turn = {
  turn: number;
  tool: string;
  args_summary?: string;
  result_summary?: string;
  input_tokens?: number | null;
  output_tokens?: number | null;
  action_status?: string | null; // action_executor.payload.reason or executor step_type for nested action rows
  action_exec?: AuditLogEntry | null;
};

function _payloadNumber(payload: Record<string, unknown> | null | undefined, key: string): number | null {
  if (!payload) return null;
  const v = payload[key];
  if (typeof v === 'number') return v;
  if (typeof v === 'string') {
    const n = Number(v);
    return Number.isFinite(n) ? n : null;
  }
  return null;
}

function _payloadString(payload: Record<string, unknown> | null | undefined, key: string): string | null {
  if (!payload) return null;
  const v = payload[key];
  return typeof v === 'string' ? v : null;
}

export function AgentReasoningTrail({ callId }: Props) {
  const theme = useTheme<AppTheme>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [rows, setRows] = useState<AuditLogEntry[]>([]);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      // Two fetches in parallel: the agent trail + the action_executor sub-steps.
      const [agentRows, execRows] = await Promise.all([
        api.listAudit({ call_id: callId, agent_name: 'call_agent', limit: 500 }),
        api.listAudit({ call_id: callId, agent_name: 'action_executor', limit: 500 }),
      ]);
      // Merge, sort ASC by created_at (the endpoint returns DESC).
      const all = [...agentRows, ...execRows].sort(
        (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
      );
      setRows(all);
    } catch (e) {
      const message = e instanceof ApiError ? e.message : 'Could not load agent trail.';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [callId]);

  useEffect(() => {
    void load();
  }, [load]);

  const { loopStart, loopEnd, turns } = useMemo(() => {
    // Two-pass: action_exec audit rows are written DURING the loop, while
    // agent_turn rows are emitted AFTER run_call_agent returns. Sorted by
    // created_at ASC, action_exec arrives BEFORE its matching agent_turn,
    // so a single-pass map.has(t) check classifies them as orphans. Collect
    // agent_turn first, then attach action_executor rows by payload.agent_turn.
    let start: AuditLogEntry | null = null;
    let end: AuditLogEntry | null = null;
    const byTurn = new Map<number, Turn>();
    const execRows: AuditLogEntry[] = [];

    for (const r of rows) {
      if (r.agent_name === 'call_agent' && r.step_type === 'agent_loop_start') {
        start = r;
        continue;
      }
      if (r.agent_name === 'call_agent' && r.step_type === 'agent_loop_end') {
        end = r;
        continue;
      }
      if (r.agent_name === 'call_agent' && r.step_type === 'agent_turn') {
        const turn = _payloadNumber(r.payload, 'turn') ?? 0;
        byTurn.set(turn, {
          turn,
          tool: _payloadString(r.payload, 'tool') ?? '(unknown)',
          args_summary: _payloadString(r.payload, 'args_summary') ?? undefined,
          result_summary: _payloadString(r.payload, 'result_summary') ?? undefined,
          input_tokens: r.input_tokens ?? null,
          output_tokens: r.output_tokens ?? null,
        });
        continue;
      }
      if (r.agent_name === 'action_executor') {
        execRows.push(r);
      }
    }

    // Pass 2: attach action_executor rows to their agent_turn now that all
    // turns have been collected.
    const orphanExec: AuditLogEntry[] = [];
    for (const r of execRows) {
      const t = _payloadNumber(r.payload, 'agent_turn');
      if (t !== null && byTurn.has(t)) {
        const existing = byTurn.get(t)!;
        existing.action_exec = r;
        existing.action_status =
          _payloadString(r.payload, 'reason') ?? r.step_type ?? null;
      } else {
        orphanExec.push(r);
      }
    }

    // Append orphan exec rows as pseudo-turns at the end so the operator
    // still sees them. Rare — only when the agent_turn payload key is missing
    // (legacy seed data) or when an action_executor row predates the agentic
    // pipeline.
    let next = byTurn.size + 1;
    for (const r of orphanExec) {
      byTurn.set(next, {
        turn: next,
        tool: _payloadString(r.payload, 'action_type') ?? '(action_exec)',
        result_summary: r.step_type,
        action_exec: r,
        action_status: r.step_type,
      });
      next += 1;
    }

    const turnsSorted = [...byTurn.values()].sort((a, b) => a.turn - b.turn);
    return { loopStart: start, loopEnd: end, turns: turnsSorted };
  }, [rows]);

  if (loading) {
    return (
      <Card mode="elevated">
        <Card.Content style={styles.loading}>
          <ActivityIndicator />
        </Card.Content>
      </Card>
    );
  }

  if (error) {
    return (
      <Card mode="elevated">
        <Card.Content>
          <Text style={{ color: theme.colors.error }}>{error}</Text>
        </Card.Content>
      </Card>
    );
  }

  if (!loopStart && turns.length === 0 && !loopEnd) {
    // No agent rows at all — pre-agentic call or pipeline never started.
    return null;
  }

  const completionReason = loopEnd ? _payloadString(loopEnd.payload, 'completion_reason') : null;
  const turnCount = loopEnd ? _payloadNumber(loopEnd.payload, 'turn_count') ?? turns.length : turns.length;

  return (
    <Card mode="elevated">
      <Card.Title title="Agent reasoning" subtitle={`${turnCount} turn${turnCount === 1 ? '' : 's'}`} />
      <Card.Content style={styles.body}>
        {loopStart ? (
          <View style={styles.headerRow}>
            <Chip mode="flat" compact icon="robot-outline">
              {loopStart.model ?? 'agent'}
            </Chip>
          </View>
        ) : null}
        {turns.map((t) => (
          <View key={t.turn} style={styles.turn}>
            <View style={styles.turnHeader}>
              <Chip mode="flat" compact style={styles.turnChip}>
                {`#${t.turn}`}
              </Chip>
              <Text variant="bodyMedium" style={styles.toolName}>
                {t.tool}
              </Text>
              {t.action_status ? (
                <Chip
                  mode="flat"
                  compact
                  style={{
                    backgroundColor:
                      t.action_status === 'action_exec'
                        ? theme.colors.successContainer
                        : theme.colors.errorContainer,
                  }}
                  textStyle={{ fontSize: 11 }}
                >
                  {t.action_status}
                </Chip>
              ) : null}
            </View>
            {t.args_summary ? (
              <Text variant="bodySmall" numberOfLines={2} style={styles.argsLine}>
                {t.args_summary}
              </Text>
            ) : null}
            {t.result_summary ? (
              <Text variant="bodySmall" numberOfLines={2} style={styles.resultLine}>
                {`→ ${t.result_summary}`}
              </Text>
            ) : null}
            {t.input_tokens || t.output_tokens ? (
              <Text variant="bodySmall" style={styles.tokenLine}>
                {`tokens · in ${t.input_tokens ?? 0} · out ${t.output_tokens ?? 0}`}
              </Text>
            ) : null}
          </View>
        ))}
        {loopEnd ? (
          <View style={styles.footerRow}>
            <Chip
              mode="flat"
              compact
              icon={completionReason === 'finalize' ? 'check-circle-outline' : 'alert-circle-outline'}
              style={{
                backgroundColor:
                  completionReason === 'finalize'
                    ? theme.colors.successContainer
                    : theme.colors.tertiaryContainer,
              }}
            >
              {completionReason ?? loopEnd.status}
            </Chip>
            <Text variant="bodySmall" style={{ color: theme.colors.onSurfaceVariant }}>
              {`tokens · in ${loopEnd.input_tokens ?? 0} · out ${loopEnd.output_tokens ?? 0}`}
            </Text>
          </View>
        ) : null}
      </Card.Content>
    </Card>
  );
}

const styles = StyleSheet.create({
  body: { gap: 10 },
  loading: { alignItems: 'center' },
  headerRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6 },
  turn: { gap: 2 },
  turnHeader: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  turnChip: { minWidth: 38, alignItems: 'center' },
  toolName: { fontWeight: '600', flex: 1 },
  argsLine: { opacity: 0.7, marginLeft: 44 },
  resultLine: { opacity: 0.85, marginLeft: 44 },
  tokenLine: { opacity: 0.55, marginLeft: 44, fontSize: 11 },
  footerRow: { flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 4 },
});
