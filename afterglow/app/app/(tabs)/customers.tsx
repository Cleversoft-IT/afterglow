import { useFocusEffect, useRouter } from 'expo-router';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ActivityIndicator, FlatList, RefreshControl, StyleSheet, Text, View } from 'react-native';
import { Badge } from '../../components/Badge';
import { Input } from '../../components/Input';
import { ListRow } from '../../components/ListRow';
import { api, ApiError } from '../../lib/api';
import { useTheme } from '../../lib/ThemeContext';
import { spacing } from '../../lib/theme';
import type { CustomerCard } from '../../lib/types';

function formatLastCall(iso?: string | null): string {
  if (!iso) return 'no calls yet';
  return new Date(iso).toLocaleString();
}

export default function CustomersScreen() {
  const { colors } = useTheme();
  const router = useRouter();
  const [customers, setCustomers] = useState<CustomerCard[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const debouncedQuery = useDebounced(query, 300);

  const load = useCallback(async (q: string) => {
    try {
      setError(null);
      const data = await api.listCustomers({ q: q || undefined, limit: 50 });
      setCustomers(data);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      load(debouncedQuery);
    }, [load, debouncedQuery])
  );

  useEffect(() => {
    load(debouncedQuery);
  }, [debouncedQuery, load]);

  const styles = useMemo(
    () =>
      StyleSheet.create({
        container: { flex: 1, backgroundColor: colors.bg },
        searchBox: { paddingHorizontal: spacing.lg, paddingTop: spacing.lg, paddingBottom: spacing.sm },
        list: { padding: spacing.lg, paddingTop: spacing.sm },
        empty: {
          color: colors.textMuted,
          textAlign: 'center',
          marginTop: spacing.xxxl,
          fontSize: 15,
          lineHeight: 22,
          paddingHorizontal: spacing.xl,
        },
        error: { color: colors.danger, padding: spacing.lg, fontSize: 14 },
      }),
    [colors],
  );

  return (
    <View style={styles.container}>
      <View style={styles.searchBox}>
        <Input
          value={query}
          onChangeText={setQuery}
          placeholder="Search phone or name"
          autoCapitalize="none"
          autoCorrect={false}
        />
      </View>
      {loading ? (
        <ActivityIndicator color={colors.brand} style={{ marginTop: 32 }} />
      ) : error ? (
        <Text style={styles.error}>{error}</Text>
      ) : (
        <FlatList
          data={customers}
          keyExtractor={(c) => c.id}
          contentContainerStyle={styles.list}
          refreshControl={
            <RefreshControl
              tintColor={colors.brand}
              refreshing={refreshing}
              onRefresh={() => {
                setRefreshing(true);
                load(debouncedQuery);
              }}
            />
          }
          ItemSeparatorComponent={() => <View style={{ height: spacing.sm }} />}
          ListEmptyComponent={
            <Text style={styles.empty}>
              {debouncedQuery
                ? 'No customers match that search.'
                : 'No customers yet. They appear once calls come in.'}
            </Text>
          }
          renderItem={({ item }) => (
            <ListRow
              title={item.display_name ?? item.phone_e164}
              subtitle={item.display_name ? item.phone_e164 : item.preferred_language ?? undefined}
              meta={formatLastCall(item.last_call_at)}
              onPress={() => router.push(`/customer/${item.id}`)}
              right={
                <Badge tone={item.total_calls > 0 ? 'brand' : 'neutral'}>
                  {`${item.total_calls} calls`}
                </Badge>
              }
            />
          )}
        />
      )}
    </View>
  );
}

function useDebounced<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => {
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => setDebounced(value), delayMs);
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, [value, delayMs]);
  return debounced;
}

