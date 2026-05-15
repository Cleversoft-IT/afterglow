import { useFocusEffect, useRouter } from 'expo-router';
import { useCallback, useState } from 'react';
import { ActivityIndicator, FlatList, RefreshControl, StyleSheet, Text, View } from 'react-native';
import { Badge } from '../../components/Badge';
import { ListRow } from '../../components/ListRow';
import { Button } from '../../components/Button';
import { api, ApiError } from '../../lib/api';
import { colors, spacing } from '../../lib/theme';
import type { CallListItem } from '../../lib/types';

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

  const load = useCallback(async () => {
    try {
      setError(null);
      const data = await api.listCalls({ limit: 50 });
      setCalls(data);
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
    }, [load])
  );

  return (
    <View style={styles.container}>
      <View style={styles.cta}>
        <Button title="Simulate incoming call" onPress={() => router.push('/simulator')} />
      </View>
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
          renderItem={({ item }) => (
            <ListRow
              title={item.phone_e164}
              subtitle={item.detected_language ?? '—'}
              meta={new Date(item.created_at).toLocaleString()}
              onPress={() => router.push(`/call/${item.id}`)}
              right={<Badge tone={statusTone(item.status)}>{item.status}</Badge>}
            />
          )}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  cta: { padding: spacing.lg },
  list: { padding: spacing.lg, paddingTop: 0 },
  empty: { color: colors.textMuted, textAlign: 'center', marginTop: 32 },
  error: { color: colors.danger, padding: spacing.lg },
});
