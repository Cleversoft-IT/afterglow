import { useFocusEffect, useRouter } from 'expo-router';
import { useCallback, useMemo, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  RefreshControl,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { Badge } from '../../components/Badge';
import { ListRow } from '../../components/ListRow';
import { api, ApiError } from '../../lib/api';
import { useTheme } from '../../lib/ThemeContext';
import { spacing } from '../../lib/theme';
import type { BookingListItem } from '../../lib/types';

function formatWhen(iso: string): string {
  return new Date(iso).toLocaleString();
}

function bookingSubtitle(item: BookingListItem): string {
  const p = item.payload;
  const parts: string[] = [];
  const name =
    (typeof p.customer_name === 'string' && p.customer_name) ||
    item.customer_display_name;
  if (name) parts.push(name);
  if (p.booking_date) parts.push(String(p.booking_date));
  if (p.booking_time) parts.push(String(p.booking_time));
  if (p.party_size != null) parts.push(`party of ${p.party_size}`);
  if (parts.length) return parts.join(' · ');
  return item.summary ?? item.action_type;
}

function statusTone(status: string): 'success' | 'warning' | 'neutral' {
  if (status === 'executed') return 'success';
  if (status === 'undone' || status === 'pending') return 'warning';
  return 'neutral';
}

export default function BookingsScreen() {
  const { colors } = useTheme();
  const router = useRouter();
  const [rows, setRows] = useState<BookingListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setError(null);
      const data = await api.listBookings({ limit: 50 });
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
        container: { flex: 1, backgroundColor: colors.bg },
        list: { padding: spacing.lg },
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

  if (loading) {
    return <ActivityIndicator color={colors.brand} style={{ marginTop: 32 }} />;
  }

  if (error) {
    return <Text style={styles.error}>{error}</Text>;
  }

  return (
    <View style={styles.container}>
      <FlatList
        data={rows}
        keyExtractor={(r) => r.id}
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
          <Text style={styles.empty}>
            No bookings yet. They appear when the pipeline runs a booking action after a
            call.
          </Text>
        }
        renderItem={({ item }) => (
          <ListRow
            title={item.title}
            subtitle={bookingSubtitle(item)}
            meta={formatWhen(item.created_at)}
            onPress={() => router.push(`/call/${item.call_id}`)}
            right={
              <View style={{ alignItems: 'flex-end', gap: spacing.xs }}>
                <Badge tone={statusTone(item.status)}>{item.status}</Badge>
                {item.is_simulated ? <Badge tone="neutral">Simulated</Badge> : null}
              </View>
            }
          />
        )}
      />
    </View>
  );
}
