import { useFocusEffect, useRouter } from 'expo-router';
import { useCallback, useEffect, useRef, useState } from 'react';
import { ActivityIndicator, FlatList, RefreshControl, StyleSheet, Text, View } from 'react-native';
import { Badge } from '../../components/Badge';
import { Button } from '../../components/Button';
import { ListRow } from '../../components/ListRow';
import { api, ApiError } from '../../lib/api';
import {
  setPipelineToast,
  subscribePipelineToast,
  type PipelineToast,
} from '../../lib/pipelineToast';
import { colors, radius, spacing } from '../../lib/theme';
import type { CallListItem } from '../../lib/types';

const NON_TERMINAL_STATUSES = new Set(['pending', 'transcribing', 'analyzing']);
const POLL_INTERVAL_MS = 2000;

function statusTone(status: string): 'neutral' | 'success' | 'warning' | 'danger' | 'brand' {
  if (status === 'completed') return 'success';
  if (status === 'failed') return 'danger';
  if (status === 'pending') return 'warning';
  if (status === 'transcribing' || status === 'analyzing') return 'brand';
  return 'neutral';
}

export default function CallsScreen() {
  const router = useRouter();
  const [calls, setCalls] = useState<CallListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<PipelineToast | null>(null);
  const focusedRef = useRef(false);

  const load = useCallback(async () => {
    try {
      setError(null);
      const data = await api.listCalls({ limit: 50 });
      setCalls(data);
      // Clear the toast as soon as the toast's call has reached a terminal
      // state — otherwise the banner would linger forever.
      const t = toast;
      if (t?.callId) {
        const row = data.find((c) => c.id === t.callId);
        if (row && !NON_TERMINAL_STATUSES.has(row.status)) {
          setPipelineToast(null);
        }
      }
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [toast]);

  useFocusEffect(
    useCallback(() => {
      focusedRef.current = true;
      load();
      return () => {
        focusedRef.current = false;
      };
    }, [load])
  );

  // Subscribe once to the pipeline toast (kept across re-renders).
  useEffect(() => subscribePipelineToast(setToast), []);

  // Poll every POLL_INTERVAL_MS while at least one call is non-terminal AND
  // the tab is focused. The polling stops on its own once all calls settle.
  useEffect(() => {
    const hasInFlight = calls.some((c) => NON_TERMINAL_STATUSES.has(c.status));
    if (!hasInFlight) return;
    const id = setInterval(() => {
      if (focusedRef.current) load();
    }, POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, [calls, load]);

  return (
    <View style={styles.container}>
      <View style={styles.cta}>
        <Button title="Simulate incoming call" onPress={() => router.push('/simulator')} />
      </View>

      {toast ? <PipelineBanner toast={toast} /> : null}

      {loading ? (
        <ActivityIndicator color={colors.brand} style={{ marginTop: 32 }} />
      ) : error ? (
        <Text style={styles.error}>{error}</Text>
      ) : (
        <FlatList
          data={calls}
          keyExtractor={(c) => c.id}
          contentContainerStyle={styles.list}
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
          ListEmptyComponent={
            <Text style={styles.empty}>No calls yet. Tap the blue button to simulate one.</Text>
          }
          renderItem={({ item }) => {
            const inFlight = NON_TERMINAL_STATUSES.has(item.status);
            const hasName = !!item.customer_display_name;
            return (
              <ListRow
                title={item.customer_display_name ?? item.phone_e164}
                subtitle={
                  hasName
                    ? item.phone_e164
                    : item.detected_language ?? '—'
                }
                meta={new Date(item.created_at).toLocaleString()}
                onPress={() => router.push(`/call/${item.id}`)}
                right={
                  <View style={styles.rightCell}>
                    {inFlight ? <ActivityIndicator color={colors.brand} size="small" /> : null}
                    <Badge tone={statusTone(item.status)}>{item.status}</Badge>
                  </View>
                }
              />
            );
          }}
        />
      )}
    </View>
  );
}

function PipelineBanner({ toast }: { toast: PipelineToast }) {
  const [elapsed, setElapsed] = useState(0);
  useEffect(() => {
    setElapsed(Math.floor((Date.now() - toast.startedAt) / 1000));
    const id = setInterval(
      () => setElapsed(Math.floor((Date.now() - toast.startedAt) / 1000)),
      1000,
    );
    return () => clearInterval(id);
  }, [toast.startedAt]);
  return (
    <View style={styles.banner}>
      <ActivityIndicator color={colors.brand} size="small" />
      <View style={{ flex: 1 }}>
        <Text style={styles.bannerTitle}>Analysis in progress</Text>
        <Text style={styles.bannerSub}>
          {toast.phoneE164} · {elapsed}s · the row below updates automatically
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  cta: { padding: spacing.lg },
  list: { padding: spacing.lg, paddingTop: 0 },
  empty: { color: colors.textMuted, textAlign: 'center', marginTop: 32 },
  error: { color: colors.danger, padding: spacing.lg },
  rightCell: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm },
  banner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    marginHorizontal: spacing.lg,
    marginBottom: spacing.md,
    padding: spacing.md,
    borderRadius: radius.md,
    backgroundColor: 'rgba(59, 130, 246, 0.12)',
    borderWidth: 1,
    borderColor: 'rgba(59, 130, 246, 0.3)',
  },
  bannerTitle: { color: colors.brand, fontWeight: '700', fontSize: 13 },
  bannerSub: { color: colors.textMuted, fontSize: 12, marginTop: 2 },
});
