import { DrawerActions } from '@react-navigation/native';
import { useFocusEffect, useNavigation, useRouter } from 'expo-router';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  RefreshControl,
  ScrollView,
  SectionList,
  StyleSheet,
  View,
} from 'react-native';
import {
  ActivityIndicator,
  Banner,
  Chip,
  Searchbar,
  Snackbar,
  Surface,
  Text,
  useTheme,
} from 'react-native-paper';
import { CallRow } from '../../../components/CallRow';
import { api, ApiError } from '../../../lib/api';
import { findMockContact } from '../../../lib/mockContacts';
import { resolveFromCallItem } from '../../../lib/callerResolver';
import { groupByDay } from '../../../lib/dateGrouping';
import {
  setPipelineToast,
  subscribePipelineToast,
  type PipelineToast,
} from '../../../lib/pipelineToast';
import type { BookingListItem, CallListItem } from '../../../lib/types';

const NON_TERMINAL_STATUSES = new Set(['pending', 'transcribing', 'analyzing']);
const POLL_INTERVAL_MS = 2000;

type FilterKey = 'all' | 'missed' | 'bookings' | 'saved' | 'unsaved';

const FILTER_LABEL: Record<FilterKey, string> = {
  all: 'All',
  missed: 'Missed',
  bookings: 'Bookings',
  saved: 'Saved',
  unsaved: 'Unsaved',
};

const FILTERS: FilterKey[] = ['all', 'missed', 'bookings', 'saved', 'unsaved'];

export default function HomeScreen() {
  const theme = useTheme();
  const router = useRouter();
  const navigation = useNavigation();

  const [calls, setCalls] = useState<CallListItem[]>([]);
  const [bookings, setBookings] = useState<BookingListItem[]>([]);
  const [filter, setFilter] = useState<FilterKey>('all');
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<PipelineToast | null>(null);
  const [snackbar, setSnackbar] = useState<string | null>(null);
  const focusedRef = useRef(false);

  const load = useCallback(async () => {
    try {
      setError(null);
      const [callsRes, bookingsRes] = await Promise.all([
        api.listCalls({ limit: 50 }),
        api.listBookings({ limit: 100 }).catch(() => [] as BookingListItem[]),
      ]);
      setCalls(callsRes);
      setBookings(bookingsRes);

      // Clear pipeline banner once its call settles.
      setToast((current) => {
        if (!current?.callId) return current;
        const row = callsRes.find((c) => c.id === current.callId);
        if (row && !NON_TERMINAL_STATUSES.has(row.status)) {
          setPipelineToast(null);
          return null;
        }
        return current;
      });
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      focusedRef.current = true;
      load();
      return () => {
        focusedRef.current = false;
      };
    }, [load]),
  );

  useEffect(() => subscribePipelineToast(setToast), []);

  useEffect(() => {
    const hasInFlight = calls.some((c) => NON_TERMINAL_STATUSES.has(c.status));
    if (!hasInFlight) return;
    const id = setInterval(() => {
      if (focusedRef.current) load();
    }, POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, [calls, load]);

  const bookingByCallId = useMemo(() => {
    const m = new Map<string, BookingListItem>();
    for (const b of bookings) m.set(b.call_id, b);
    return m;
  }, [bookings]);

  const sections = useMemo(() => {
    const q = query.trim().toLowerCase();
    const filtered = calls.filter((c) => {
      const caller = resolveFromCallItem(c);
      const booking = bookingByCallId.get(c.id);
      const mock = findMockContact(c.phone_e164);
      // Chip filter
      if (filter === 'missed' && c.status !== 'failed') return false;
      if (filter === 'bookings' && !booking) return false;
      if (filter === 'saved' && !(caller.is_customer || mock)) return false;
      if (filter === 'unsaved' && (caller.is_customer || mock)) return false;
      // Search query
      if (!q) return true;
      const haystack = [
        caller.display_name,
        c.phone_e164,
        booking?.title,
        typeof booking?.payload === 'object' && booking?.payload !== null
          ? (booking.payload as Record<string, unknown>).customer_name
          : null,
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase();
      return haystack.includes(q);
    });
    return groupByDay(filtered);
  }, [calls, bookingByCallId, filter, query]);

  const styles = useMemo(
    () =>
      StyleSheet.create({
        container: { flex: 1, backgroundColor: theme.colors.background },
        header: {
          paddingHorizontal: 16,
          paddingTop: 12,
          paddingBottom: 8,
          backgroundColor: theme.colors.background,
        },
        searchbar: { backgroundColor: theme.colors.surfaceVariant },
        chipsScroll: { flexGrow: 0, flexShrink: 0, backgroundColor: theme.colors.background },
        chipsRow: {
          paddingHorizontal: 16,
          paddingVertical: 8,
          gap: 8,
          alignItems: 'center',
        },
        sectionHeader: {
          paddingHorizontal: 16,
          paddingTop: 16,
          paddingBottom: 6,
          backgroundColor: theme.colors.background,
        },
        sectionTitle: { color: theme.colors.primary, fontWeight: '600' },
        empty: {
          paddingTop: 64,
          alignItems: 'center',
          gap: 8,
        },
      }),
    [theme],
  );

  if (loading) {
    return (
      <View style={[styles.container, { alignItems: 'center', justifyContent: 'center' }]}>
        <ActivityIndicator />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Searchbar
          placeholder="Search contacts and calls"
          value={query}
          onChangeText={setQuery}
          icon="menu"
          onIconPress={() => navigation.dispatch(DrawerActions.openDrawer())}
          traileringIcon={query ? 'close' : 'microphone'}
          onTraileringIconPress={query ? () => setQuery('') : undefined}
          elevation={0}
          style={styles.searchbar}
        />
      </View>

      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        style={styles.chipsScroll}
        contentContainerStyle={styles.chipsRow}
      >
        {FILTERS.map((k) => (
          <Chip
            key={k}
            mode="flat"
            compact
            selected={filter === k}
            onPress={() => setFilter(k)}
            showSelectedCheck={false}
            selectedColor={filter === k ? theme.colors.onSecondaryContainer : undefined}
            style={
              filter === k
                ? { backgroundColor: theme.colors.secondaryContainer }
                : { backgroundColor: theme.colors.surfaceVariant }
            }
          >
            {FILTER_LABEL[k]}
          </Chip>
        ))}
      </ScrollView>

      {toast ? (
        <Banner
          visible
          icon="clock-outline"
          actions={[{ label: 'Dismiss', onPress: () => setPipelineToast(null) }]}
        >
          {`Analysis in progress · ${toast.phoneE164}`}
        </Banner>
      ) : null}

      {error ? (
        <Banner visible icon="alert-circle-outline" actions={[{ label: 'Retry', onPress: load }]}>
          {error}
        </Banner>
      ) : null}

      <SectionList
        sections={sections}
        keyExtractor={(item) => item.id}
        stickySectionHeadersEnabled
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
        renderSectionHeader={({ section }) => (
          <View style={styles.sectionHeader}>
            <Text variant="labelMedium" style={styles.sectionTitle}>
              {section.title}
            </Text>
          </View>
        )}
        renderItem={({ item }) => (
          <CallRow
            call={item}
            booking={bookingByCallId.get(item.id)}
            mode={filter}
            onPress={() => router.push(`/call/${item.id}` as never)}
            onCallIconPress={() =>
              setSnackbar('Use the Simulator from the drawer to test the AI pipeline.')
            }
          />
        )}
        ListEmptyComponent={
          <Surface mode="flat" style={styles.empty}>
            <Text variant="titleMedium">No calls yet</Text>
            <Text variant="bodyMedium" style={{ color: theme.colors.onSurfaceVariant }}>
              Open the drawer → Test simulator to make your first call.
            </Text>
          </Surface>
        }
      />

      <Snackbar
        visible={!!snackbar}
        onDismiss={() => setSnackbar(null)}
        duration={3500}
      >
        {snackbar ?? ''}
      </Snackbar>
    </View>
  );
}
