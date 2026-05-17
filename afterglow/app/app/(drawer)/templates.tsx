import { DrawerActions } from '@react-navigation/native';
import { router, useFocusEffect, useNavigation } from 'expo-router';
import { useCallback, useMemo, useState } from 'react';
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
import { api, ApiError } from '../../lib/api';
import { consumeFreshSession } from '../../lib/freshSession';
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
  const [templates, setTemplates] = useState<TemplateView[]>([]);
  const [loading, setLoading] = useState(true);
  const [switching, setSwitching] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  // After a fresh session bootstrap (or post-reset) we land on this screen.
  // When the user activates a template we offer to jump to the calls feed
  // so they're not stranded here. The flag is one-shot, set by RootLayout.
  const [goHomeDialogVisible, setGoHomeDialogVisible] = useState(false);

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

  const activate = async (id: string) => {
    setSwitching(id);
    try {
      await api.setActiveTemplate(id);
      await load();
      if (consumeFreshSession()) {
        setGoHomeDialogVisible(true);
      }
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
        <Dialog visible={goHomeDialogVisible} onDismiss={() => setGoHomeDialogVisible(false)}>
          <Dialog.Icon icon="phone-incoming" />
          <Dialog.Title>Template activated</Dialog.Title>
          <Dialog.Content>
            <Text variant="bodyMedium">
              The dialer is wired up. Head over to the calls feed to try the simulator, or stay here to keep tweaking templates.
            </Text>
          </Dialog.Content>
          <Dialog.Actions>
            <Button onPress={() => setGoHomeDialogVisible(false)}>Stay on Templates</Button>
            <Button
              mode="contained-tonal"
              onPress={() => {
                setGoHomeDialogVisible(false);
                router.navigate('/(drawer)/(tabs)' as never);
              }}
            >
              Go to Calls
            </Button>
          </Dialog.Actions>
        </Dialog>
      </Portal>
    </View>
  );
}
