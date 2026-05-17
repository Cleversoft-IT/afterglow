import { DrawerActions, useIsFocused } from '@react-navigation/native';
import { router, useFocusEffect, useNavigation } from 'expo-router';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { FlatList, StyleSheet, View } from 'react-native';
import {
  ActivityIndicator,
  Appbar,
  Avatar,
  Banner,
  Button,
  Card,
  Chip,
  Dialog,
  Portal,
  Text,
  useTheme,
} from 'react-native-paper';
import { api, ApiError, isDemoMode } from '../../lib/api';
import type { TemplateView } from '../../lib/types';

function domainIcon(domain: string | null | undefined): string {
  switch (domain) {
    case 'restaurant':
      return 'silverware-fork-knife';
    case 'dentist':
      return 'tooth-outline';
    case 'bodyshop':
      return 'car-wrench';
    default:
      return 'view-grid';
  }
}

export default function TemplatesScreen() {
  const theme = useTheme();
  const navigation = useNavigation();
  const isFocused = useIsFocused();
  const [templates, setTemplates] = useState<TemplateView[]>([]);
  const [loading, setLoading] = useState(true);
  const [switching, setSwitching] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [warningVisible, setWarningVisible] = useState(false);
  const [pendingRoute, setPendingRoute] = useState<string | null>(null);

  const hasActiveTemplate = templates.some((t) => t.is_active);

  const load = useCallback(async () => {
    try {
      setError(null);
      const data = await api.listTemplates();
      setTemplates(data);
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

  // Soft-guard: in demo mode warn if the user navigates away from Templates
  // without having picked an active one. The parent navigator is now the Drawer.
  useEffect(() => {
    if (!isDemoMode()) return;
    const parent = navigation.getParent();
    if (!parent) return;
    const unsub = parent.addListener('state' as never, ((e: {
      data?: { state?: { routes?: { name: string }[]; index?: number } };
    }) => {
      if (!isFocused) return;
      if (hasActiveTemplate) return;
      const routes = e.data?.state?.routes;
      const idx = e.data?.state?.index;
      if (!routes || idx == null) return;
      const current = routes[idx];
      if (!current || current.name === 'templates') return;
      setPendingRoute(current.name);
      setWarningVisible(true);
    }) as never);
    return unsub;
  }, [navigation, isFocused, hasActiveTemplate]);

  const activate = async (id: string) => {
    setSwitching(id);
    try {
      await api.setActiveTemplate(id);
      await load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setSwitching(null);
    }
  };

  const styles = useMemo(
    () =>
      StyleSheet.create({
        container: { flex: 1, backgroundColor: theme.colors.background },
        list: { padding: 16, paddingBottom: 48, gap: 12 },
        helpText: { color: theme.colors.onSurfaceVariant, marginBottom: 12 },
        sep: { height: 12 },
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
        <Appbar.Content title="Templates" />
      </Appbar.Header>

      {error ? (
        <Banner visible icon="alert-circle-outline" actions={[{ label: 'Retry', onPress: load }]}>
          {error}
        </Banner>
      ) : null}

      <FlatList
        data={templates}
        keyExtractor={(t) => t.id}
        contentContainerStyle={styles.list}
        ItemSeparatorComponent={() => <View style={styles.sep} />}
        ListHeaderComponent={
          <View style={{ marginBottom: 12, gap: 12 }}>
            <Text variant="bodyMedium" style={styles.helpText}>
              Pick which preset drives the call analysis. Exactly one template can be active at a time.
            </Text>
            <Button
              mode="contained-tonal"
              icon="plus"
              onPress={() => router.push('/templates/wizard' as never)}
            >
              New from prompt
            </Button>
          </View>
        }
        renderItem={({ item }) => (
          <Card mode="elevated" onPress={() => router.push(`/templates/${item.id}` as never)}>
            <Card.Title
              title={item.name}
              subtitle={`${item.domain_hint} · ${item.fields_schema.length} fields · ${item.action_types.length} actions${item.is_seed ? ' · seed' : ''}`}
              left={(p) => <Avatar.Icon {...p} icon={domainIcon(item.domain_hint)} />}
              right={() =>
                item.is_active ? (
                  <Chip selected mode="flat" icon="check" style={{ marginRight: 16 }}>
                    Active
                  </Chip>
                ) : (
                  <Button
                    mode="text"
                    loading={switching === item.id}
                    onPress={() => activate(item.id)}
                  >
                    Activate
                  </Button>
                )
              }
            />
            {item.description ? (
              <Card.Content>
                <Text variant="bodyMedium" style={{ color: theme.colors.onSurfaceVariant }}>
                  {item.description}
                </Text>
              </Card.Content>
            ) : null}
          </Card>
        )}
      />

      <Portal>
        <Dialog visible={warningVisible} onDismiss={() => setWarningVisible(false)}>
          <Dialog.Icon icon="alert-circle-outline" />
          <Dialog.Title>Pick a template first</Dialog.Title>
          <Dialog.Content>
            <Text variant="bodyMedium">
              Afterglow needs an active template to analyze calls. Choose one of the presets to
              continue, or browse anyway — most features will be limited until a template is active.
            </Text>
          </Dialog.Content>
          <Dialog.Actions>
            <Button onPress={() => setWarningVisible(false)}>Choose template</Button>
            <Button
              mode="text"
              onPress={() => {
                const target = pendingRoute;
                setWarningVisible(false);
                setPendingRoute(null);
                if (target) {
                  (navigation as unknown as { navigate: (name: string) => void }).navigate(target);
                }
              }}
            >
              Browse anyway
            </Button>
          </Dialog.Actions>
        </Dialog>
      </Portal>
    </View>
  );
}
