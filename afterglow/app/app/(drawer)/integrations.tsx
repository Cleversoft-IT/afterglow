import { DrawerActions } from '@react-navigation/native';
import { useFocusEffect, useNavigation } from 'expo-router';
import { useCallback, useState } from 'react';
import { FlatList, RefreshControl, StyleSheet, View } from 'react-native';
import {
  ActivityIndicator,
  Appbar,
  Banner,
  Card,
  Chip,
  Icon,
  Text,
  useTheme,
} from 'react-native-paper';
import { api, ApiError } from '../../lib/api';
import type { AppTheme } from '../../lib/paperTheme';
import type { IntegrationSummary } from '../../lib/types';

const BUCKET_ICON: Record<string, string> = {
  booking: 'calendar-check',
  whatsapp: 'whatsapp',
  sms: 'message-text-outline',
  email: 'email-outline',
  crm: 'briefcase-outline',
  calendar: 'calendar-month',
  payment: 'credit-card-outline',
  review: 'star-outline',
  customer_profile: 'database-outline',
};

function bucketIcon(key: string): string {
  return BUCKET_ICON[key] ?? 'puzzle-outline';
}

export default function IntegrationsScreen() {
  const theme = useTheme<AppTheme>();
  const navigation = useNavigation();
  const [items, setItems] = useState<IntegrationSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setError(null);
      const data = await api.fetchIntegrations();
      setItems(data);
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

  if (loading) {
    return (
      <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center' }}>
        <ActivityIndicator />
      </View>
    );
  }

  return (
    <View style={{ flex: 1, backgroundColor: theme.colors.background }}>
      <Appbar.Header
        mode="small"
        elevated={false}
        style={{ backgroundColor: theme.colors.background }}
      >
        <Appbar.Action icon="menu" onPress={() => navigation.dispatch(DrawerActions.openDrawer())} />
        <Appbar.Content title="Integrations" />
      </Appbar.Header>

      <View style={styles.subtitleWrap}>
        <Text variant="bodyMedium" style={{ color: theme.colors.onSurfaceVariant }}>
          Channels the agent can act on after a call. Simulated integrations
          return realistic-looking mock data; live integrations write to
          Afterglow's own records.
        </Text>
      </View>

      {error ? (
        <Banner visible icon="alert-circle-outline" actions={[{ label: 'Retry', onPress: load }]}>
          {error}
        </Banner>
      ) : null}

      <FlatList
        data={items}
        keyExtractor={(b) => b.key}
        contentContainerStyle={styles.list}
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
        ListEmptyComponent={
          !error ? (
            <View style={{ padding: 24 }}>
              <Text style={{ color: theme.colors.onSurfaceVariant }}>
                No integrations registered.
              </Text>
            </View>
          ) : null
        }
        renderItem={({ item }) => {
          const isLive = item.kind === 'live';
          const chipBg = isLive ? theme.colors.successContainer : theme.colors.tertiaryContainer;
          const chipFg = isLive ? theme.colors.onSuccessContainer : theme.colors.onTertiaryContainer;
          return (
            <Card mode="contained" style={styles.card}>
              <Card.Title
                title={item.label}
                subtitle={`${item.action_count} action${item.action_count === 1 ? '' : 's'}`}
                left={(props) => <Icon source={bucketIcon(item.key)} size={props.size} />}
                right={() => (
                  <Chip
                    compact
                    mode="flat"
                    style={{ backgroundColor: chipBg, marginRight: 12 }}
                    textStyle={{ color: chipFg, fontSize: 11 }}
                  >
                    {isLive ? 'Live' : 'Simulated'}
                  </Chip>
                )}
              />
            </Card>
          );
        }}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  subtitleWrap: {
    paddingHorizontal: 20,
    paddingBottom: 12,
  },
  list: {
    paddingHorizontal: 16,
    paddingBottom: 24,
    gap: 8,
  },
  card: {
    marginBottom: 4,
  },
});
