import { useLocalSearchParams, useRouter } from 'expo-router';
import { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, ScrollView, StyleSheet, Text, View } from 'react-native';
import { Badge } from '../../components/Badge';
import { Card } from '../../components/Card';
import { ListRow } from '../../components/ListRow';
import { api, ApiError } from '../../lib/api';
import { colors, spacing } from '../../lib/theme';
import type { CallListItem, CustomerCard } from '../../lib/types';

function callStatusTone(
  status: string
): 'neutral' | 'success' | 'warning' | 'danger' | 'brand' {
  if (status === 'completed') return 'success';
  if (status === 'failed') return 'danger';
  if (status === 'pending') return 'warning';
  if (status === 'transcribing' || status === 'analyzing') return 'brand';
  return 'neutral';
}

export default function CustomerDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const [customer, setCustomer] = useState<CustomerCard | null>(null);
  const [calls, setCalls] = useState<CallListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!id) return;
    try {
      setError(null);
      const [c, cs] = await Promise.all([
        api.getCustomer(id),
        api.listCalls({ customer_id: id, limit: 20 }),
      ]);
      setCustomer(c);
      setCalls(cs);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) {
    return <ActivityIndicator color={colors.brand} style={{ marginTop: 32 }} />;
  }
  if (error || !customer) {
    return <Text style={styles.error}>{error ?? 'Customer not found.'}</Text>;
  }

  return (
    <ScrollView contentContainerStyle={styles.scroll}>
      <Card>
        <View style={styles.headerRow}>
          <Text style={styles.heading}>{customer.display_name ?? customer.phone_e164}</Text>
          {customer.preferred_language ? (
            <Badge tone="brand">{customer.preferred_language}</Badge>
          ) : null}
        </View>
        <Text style={styles.meta}>
          {customer.display_name ? `${customer.phone_e164} · ` : ''}
          {customer.total_calls} calls
          {customer.last_call_at
            ? ` · last ${new Date(customer.last_call_at).toLocaleString()}`
            : ''}
        </Text>
      </Card>

      {customer.tags.length > 0 ? (
        <Card>
          <Text style={styles.section}>Tags</Text>
          <View style={styles.tagsRow}>
            {customer.tags.map((t) => (
              <Badge key={t}>{t}</Badge>
            ))}
          </View>
        </Card>
      ) : null}

      {customer.profile_facts && Object.keys(customer.profile_facts).length > 0 ? (
        <Card>
          <Text style={styles.section}>Known facts</Text>
          {Object.entries(customer.profile_facts).map(([k, v]) => (
            <View key={k} style={styles.factRow}>
              <Text style={styles.factKey}>{k.replace(/_/g, ' ')}</Text>
              <Text style={styles.factValue}>
                {Array.isArray(v) ? v.join(', ') : typeof v === 'object' ? JSON.stringify(v) : String(v)}
              </Text>
            </View>
          ))}
        </Card>
      ) : null}

      <Card>
        <Text style={styles.section}>Next-call briefing</Text>
        {customer.memory_summary ? (
          <Text style={styles.memory}>{customer.memory_summary}</Text>
        ) : (
          <Text style={styles.placeholder}>
            No briefing yet — Afterglow writes one after each call.
          </Text>
        )}
      </Card>

      <Card>
        <Text style={styles.section}>Calls ({calls.length})</Text>
        {calls.length === 0 ? (
          <Text style={styles.placeholder}>No calls yet for this customer.</Text>
        ) : (
          <View style={{ gap: spacing.sm }}>
            {calls.map((c) => (
              <ListRow
                key={c.id}
                title={new Date(c.created_at).toLocaleString()}
                subtitle={c.detected_language ?? undefined}
                onPress={() => router.push(`/call/${c.id}`)}
                right={<Badge tone={callStatusTone(c.status)}>{c.status}</Badge>}
              />
            ))}
          </View>
        )}
      </Card>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  scroll: { padding: spacing.lg, gap: spacing.md },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: spacing.md,
  },
  heading: { color: colors.text, fontSize: 18, fontWeight: '700', flexShrink: 1 },
  meta: { color: colors.textMuted, fontSize: 13, marginTop: spacing.xs },
  section: { color: colors.text, fontWeight: '700', fontSize: 15, marginBottom: spacing.sm },
  tagsRow: { flexDirection: 'row', gap: 6, flexWrap: 'wrap' },
  factRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: spacing.md,
    paddingVertical: 6,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.border,
  },
  factKey: {
    color: colors.textMuted,
    fontSize: 12,
    textTransform: 'capitalize',
  },
  factValue: { color: colors.text, fontSize: 13, flex: 1, textAlign: 'right' },
  memory: { color: colors.text, fontSize: 14, lineHeight: 20 },
  placeholder: { color: colors.textMuted, fontSize: 13, fontStyle: 'italic' },
  error: { color: colors.danger, padding: spacing.lg },
});
