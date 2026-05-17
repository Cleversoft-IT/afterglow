import { DrawerActions } from '@react-navigation/native';
import { useFocusEffect, useNavigation, useRouter } from 'expo-router';
import { useCallback, useMemo, useState } from 'react';
import { SectionList, StyleSheet, View } from 'react-native';
import {
  ActivityIndicator,
  Appbar,
  Banner,
  Chip,
  IconButton,
  List,
  Searchbar,
  Snackbar,
  Text,
  useTheme,
} from 'react-native-paper';
import { ContactAvatar } from '../../components/ContactAvatar';
import { api, ApiError } from '../../lib/api';
import { MOCK_CONTACTS } from '../../lib/mockContacts';
import type { CustomerCard } from '../../lib/types';

type ContactEntry = {
  kind: 'customer' | 'mock';
  id: string;
  display_name: string;
  phone_e164: string;
  label: string;
};

function normalisePhone(p: string): string {
  return p.replace(/\s+/g, '');
}

export default function ContactsScreen() {
  const theme = useTheme();
  const router = useRouter();
  const navigation = useNavigation();

  const [customers, setCustomers] = useState<CustomerCard[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [snackbar, setSnackbar] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setError(null);
      const data = await api.listCustomers({ limit: 50 });
      setCustomers(data);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load]),
  );

  const sections = useMemo(() => {
    // 1. customer entries with display_name resolution
    const customerEntries: ContactEntry[] = customers.map((c) => ({
      kind: 'customer',
      id: c.id,
      display_name: c.display_name ?? c.phone_e164,
      phone_e164: c.phone_e164,
      label: 'Client',
    }));

    // 2. mock entries
    const mockEntries: ContactEntry[] = MOCK_CONTACTS.map((m) => ({
      kind: 'mock',
      id: m.id,
      display_name: m.display_name,
      phone_e164: m.phone_e164,
      label: m.label,
    }));

    // 3. dedupe by phone — customer wins
    const seenPhones = new Set(customerEntries.map((c) => normalisePhone(c.phone_e164)));
    const merged: ContactEntry[] = [
      ...customerEntries,
      ...mockEntries.filter((m) => !seenPhones.has(normalisePhone(m.phone_e164))),
    ];

    // 4. filter by query
    const q = query.trim().toLowerCase();
    const filtered = q
      ? merged.filter(
          (e) =>
            e.display_name.toLowerCase().includes(q) ||
            e.phone_e164.replace(/\s/g, '').includes(q.replace(/\s/g, '')),
        )
      : merged;

    // 5. sort alphabetical, group by first letter
    const sorted = filtered.sort((a, b) => a.display_name.localeCompare(b.display_name));
    const map = new Map<string, ContactEntry[]>();
    for (const e of sorted) {
      const letter = (e.display_name[0] || '#').toUpperCase();
      const arr = map.get(letter);
      if (arr) arr.push(e);
      else map.set(letter, [e]);
    }
    return Array.from(map.entries()).map(([title, data]) => ({ title, data }));
  }, [customers, query]);

  const styles = useMemo(
    () =>
      StyleSheet.create({
        container: { flex: 1, backgroundColor: theme.colors.background },
        header: { paddingHorizontal: 16, paddingTop: 0, paddingBottom: 8 },
        sectionHeader: {
          paddingHorizontal: 16,
          paddingTop: 16,
          paddingBottom: 6,
          backgroundColor: theme.colors.background,
        },
        sectionTitle: { color: theme.colors.primary, fontWeight: '600' },
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
      <Appbar.Header mode="small" elevated={false} style={{ backgroundColor: theme.colors.background }}>
        <Appbar.Action icon="menu" onPress={() => navigation.dispatch(DrawerActions.openDrawer())} />
        <Appbar.Content title="Contacts" />
      </Appbar.Header>

      <View style={styles.header}>
        <Searchbar
          placeholder="Search contacts"
          value={query}
          onChangeText={setQuery}
          icon="magnify"
          traileringIcon={query ? 'close' : undefined}
          onTraileringIconPress={query ? () => setQuery('') : undefined}
          elevation={0}
        />
      </View>

      {error ? (
        <Banner visible icon="alert-circle-outline" actions={[{ label: 'Retry', onPress: load }]}>
          {error}
        </Banner>
      ) : null}

      <SectionList
        sections={sections}
        keyExtractor={(item) => `${item.kind}:${item.id}`}
        stickySectionHeadersEnabled
        renderSectionHeader={({ section }) => (
          <View style={styles.sectionHeader}>
            <Text variant="labelMedium" style={styles.sectionTitle}>
              {section.title}
            </Text>
          </View>
        )}
        renderItem={({ item }) => (
          <List.Item
            onPress={() => {
              if (item.kind === 'customer') {
                router.push(`/customer/${item.id}` as never);
              } else {
                setSnackbar(`${item.display_name} · ${item.phone_e164}`);
              }
            }}
            left={() => (
              <View style={{ paddingLeft: 8, justifyContent: 'center' }}>
                <ContactAvatar phone={item.phone_e164} name={item.display_name} size={48} />
              </View>
            )}
            title={item.display_name}
            description={item.phone_e164}
            right={() => (
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 4 }}>
                {item.kind === 'customer' && (
                  <Chip compact mode="flat" textStyle={{ fontSize: 11 }} icon="account-star-outline">
                    Client
                  </Chip>
                )}
                <IconButton
                  icon="phone-outline"
                  onPress={(e) => {
                    (e as unknown as { stopPropagation?: () => void })?.stopPropagation?.();
                    setSnackbar('Use the Simulator from the drawer to test the AI pipeline.');
                  }}
                />
              </View>
            )}
          />
        )}
        ListEmptyComponent={
          <View style={{ paddingTop: 64, alignItems: 'center' }}>
            <Text variant="bodyMedium" style={{ color: theme.colors.onSurfaceVariant }}>
              No contacts found.
            </Text>
          </View>
        }
      />

      <Snackbar visible={!!snackbar} onDismiss={() => setSnackbar(null)} duration={3500}>
        {snackbar ?? ''}
      </Snackbar>
    </View>
  );
}
