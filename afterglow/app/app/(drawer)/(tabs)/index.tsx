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
  IconButton,
  Searchbar,
  Surface,
  Text,
  useTheme,
} from 'react-native-paper';
import { CallRow, type CallFilterKey } from '../../../components/CallRow';
import { api, ApiError } from '../../../lib/api';
import { findMockContact } from '../../../lib/mockContacts';
import { resolveFromCallItem } from '../../../lib/callerResolver';
import { groupByDay } from '../../../lib/dateGrouping';
import { useLocale } from '../../../lib/LocaleContext';
import {
  setPipelineToast,
  subscribePipelineToast,
  type PipelineToast,
} from '../../../lib/pipelineToast';
import type { BookingListItem, CallListItem } from '../../../lib/types';

const NON_TERMINAL_STATUSES = new Set(['pending', 'transcribing', 'analyzing']);
const POLL_INTERVAL_MS = 2000;

const FILTER_LABEL: Record<CallFilterKey, string> = {
  all: 'All',
  missed: 'Missed',
  bookings: 'Bookings',
  clients: 'Clients',
  saved: 'Saved',
  unsaved: 'Unsaved',
};

const FILTERS: CallFilterKey[] = ['all', 'missed', 'bookings', 'clients', 'saved', 'unsaved'];

export default function HomeScreen() {
  const theme = useTheme();
  const router = useRouter();
  const navigation = useNavigation();
  const { locale } = useLocale();

  const [calls, setCalls] = useState<CallListItem[]>([]);
  const [bookings, setBookings] = useState<BookingListItem[]>([]);
  const [filter, setFilter] = useState<CallFilterKey>('all');
  const [bookingsSortMode, setBookingsSortMode] = useState<'call_date' | 'booking_date'>(
    'call_date',
  );
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<PipelineToast | null>(null);
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
      if (filter === 'clients' && !caller.is_customer) return false;
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

    if (filter === 'bookings' && bookingsSortMode === 'booking_date') {
      // Sort by the actual booking slot (date+time from payload), not the
      // call timestamp. Upcoming slots come first; past bookings sink
      // toward the end. Calls whose payload lacks a valid date land last.
      const now = Date.now();
      const slotMs = (c: CallListItem): number => {
        const b = bookingByCallId.get(c.id);
        if (!b) return Infinity;
        const p = b.payload as Record<string, unknown>;
        const date = typeof p.booking_date === 'string' ? p.booking_date : null;
        const time = typeof p.booking_time === 'string' ? p.booking_time : '00:00';
        if (!date) return Infinity;
        const ms = Date.parse(`${date}T${time}`);
        return Number.isNaN(ms) ? Infinity : ms;
      };
      const sorted = [...filtered].sort((a, b) => {
        const aMs = slotMs(a);
        const bMs = slotMs(b);
        // Future slots ascending (next first); past slots after future.
        const aFuture = aMs >= now;
        const bFuture = bMs >= now;
        if (aFuture !== bFuture) return aFuture ? -1 : 1;
        return aFuture ? aMs - bMs : bMs - aMs;
      });
      return groupByDay(sorted, locale);
    }

    return groupByDay(filtered, locale);
  }, [calls, bookingByCallId, filter, bookingsSortMode, query, locale]);

  const styles = useMemo(
    () =>
      StyleSheet.create({
        container: { flex: 1, backgroundColor: theme.colors.background },
        header: {
          paddingHorizontal: 8,
          paddingTop: 8,
          paddingBottom: 8,
          backgroundColor: theme.colors.background,
          flexDirection: 'row',
          alignItems: 'center',
          gap: 4,
        },
        searchbar: { backgroundColor: theme.colors.surfaceVariant, flex: 1 },
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
        <IconButton
          icon="menu"
          accessibilityLabel="Open menu"
          onPress={() => navigation.dispatch(DrawerActions.openDrawer())}
        />
        <Searchbar
          placeholder="Search contacts and calls"
          value={query}
          onChangeText={setQuery}
          icon="magnify"
          traileringIcon={query ? 'close' : undefined}
          onTraileringIconPress={query ? () => setQuery('') : undefined}
          elevation={0}
          style={styles.searchbar}
        />
        <IconButton
          icon="account-multiple-outline"
          accessibilityLabel="Open contacts"
          onPress={() => router.push('/(drawer)/contacts' as never)}
        />
      </View>

      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        style={styles.chipsScroll}
        contentContainerStyle={styles.chipsRow}
      >
        {FILTERS.map((k) => {
          const isSelected = filter === k;
          // "Clients" is the legend for the customer-border treatment on
          // avatars: it always carries a subtle primary border, even when
          // unselected. Every other chip uses the standard Material flat
          // treatment with primaryContainer when selected for stronger
          // contrast than secondaryContainer in light mode.
          const isClients = k === 'clients';
          const baseStyle = isSelected
            ? { backgroundColor: theme.colors.primaryContainer }
            : { backgroundColor: theme.colors.surfaceVariant };
          const clientsBorder = isClients
            ? {
                borderWidth: 1,
                borderColor: theme.colors.primary,
                backgroundColor: isSelected
                  ? theme.colors.primaryContainer
                  : 'transparent',
              }
            : null;
          return (
            <Chip
              key={k}
              mode="flat"
              compact
              selected={isSelected}
              onPress={() => setFilter(k)}
              showSelectedCheck={false}
              selectedColor={isSelected ? theme.colors.onPrimaryContainer : undefined}
              style={[baseStyle, clientsBorder]}
            >
              {FILTER_LABEL[k]}
            </Chip>
          );
        })}
      </ScrollView>

      {filter === 'bookings' ? (
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          style={styles.chipsScroll}
          contentContainerStyle={[styles.chipsRow, { paddingTop: 0 }]}
        >
          <Text variant="labelSmall" style={{ color: theme.colors.onSurfaceVariant, marginRight: 4 }}>
            Sort by:
          </Text>
          {(['call_date', 'booking_date'] as const).map((mode) => (
            <Chip
              key={mode}
              mode="outlined"
              compact
              selected={bookingsSortMode === mode}
              onPress={() => setBookingsSortMode(mode)}
              showSelectedCheck={false}
              selectedColor={
                bookingsSortMode === mode ? theme.colors.onSecondaryContainer : undefined
              }
              style={
                bookingsSortMode === mode
                  ? { backgroundColor: theme.colors.secondaryContainer }
                  : undefined
              }
            >
              {mode === 'call_date' ? 'By call date' : 'By booking date'}
            </Chip>
          ))}
        </ScrollView>
      ) : null}

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
        renderItem={({ item }) => {
          // Calls without a customer row don't navigate anywhere — the
          // detail screen is only meaningful for client calls (extracted
          // fields, executed actions, memory). For unsaved callers the
          // row becomes inert; Paper's TouchableRipple gracefully skips
          // the ripple when onPress is undefined.
          const onPress = item.customer_id
            ? () => router.push(`/call/${item.id}` as never)
            : undefined;
          return (
            <CallRow
              call={item}
              booking={bookingByCallId.get(item.id)}
              mode={filter}
              onPress={onPress}
            />
          );
        }}
        ListEmptyComponent={
          <Surface mode="flat" style={styles.empty}>
            <Text variant="titleMedium">No calls yet</Text>
            <Text variant="bodyMedium" style={{ color: theme.colors.onSurfaceVariant }}>
              Open the drawer → Test simulator to make your first call.
            </Text>
          </Surface>
        }
      />
    </View>
  );
}
