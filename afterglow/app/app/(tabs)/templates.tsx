import { useIsFocused } from '@react-navigation/native';
import { router, useFocusEffect, useNavigation } from 'expo-router';
import { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  Modal,
  Pressable,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { Badge } from '../../components/Badge';
import { Button } from '../../components/Button';
import { Card } from '../../components/Card';
import { api, ApiError, isDemoMode } from '../../lib/api';
import { colors, radius, spacing } from '../../lib/theme';
import type { TemplateView } from '../../lib/types';

export default function TemplatesScreen() {
  const [templates, setTemplates] = useState<TemplateView[]>([]);
  const [loading, setLoading] = useState(true);
  const [switching, setSwitching] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [warningVisible, setWarningVisible] = useState(false);
  const [pendingRoute, setPendingRoute] = useState<string | null>(null);

  const navigation = useNavigation();
  const isFocused = useIsFocused();
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
    }, [load])
  );

  // Soft-guard the tab bar: while on Templates with no active pick, prompt
  // the visitor before they switch to another tab. Production (bypass mode)
  // is exempt — the admin already set the template once and we do not want
  // to nag them.
  useEffect(() => {
    if (!isDemoMode()) return;
    const parent = navigation.getParent();
    if (!parent) return;
    const unsub = parent.addListener('tabPress' as never, ((e: {
      defaultPrevented: boolean;
      preventDefault: () => void;
      target?: string;
    }) => {
      if (!isFocused) return;
      if (hasActiveTemplate) return;
      e.preventDefault();
      const state = (parent as unknown as { getState: () => { routes: { key: string; name: string }[] } }).getState();
      const targetRoute = state.routes.find((r) => r.key === e.target);
      // Same tab tap (Templates → Templates) is a no-op; skip the modal.
      if (!targetRoute || targetRoute.name === 'templates') return;
      setPendingRoute(targetRoute.name);
      setWarningVisible(true);
    }) as never);
    return unsub;
  }, [navigation, isFocused, hasActiveTemplate]);

  const dismissWarning = () => {
    setWarningVisible(false);
    setPendingRoute(null);
  };

  const browseAnyway = () => {
    const target = pendingRoute;
    setWarningVisible(false);
    setPendingRoute(null);
    if (target) {
      (navigation as unknown as { navigate: (name: string) => void }).navigate(target);
    }
  };

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

  if (loading) {
    return <ActivityIndicator color={colors.brand} style={{ marginTop: 32 }} />;
  }
  if (error) {
    return <Text style={styles.error}>{error}</Text>;
  }

  return (
    <>
      <FlatList
        data={templates}
        keyExtractor={(t) => t.id}
        contentContainerStyle={styles.list}
        ItemSeparatorComponent={() => <View style={{ height: spacing.md }} />}
        ListHeaderComponent={
          <View style={{ gap: spacing.md, marginBottom: spacing.md }}>
            <Text style={styles.helpText}>
              Pick which preset drives the call analysis. Exactly one template can be active at a time.
            </Text>
            <Button
              title="+ New from prompt"
              variant="primary"
              onPress={() => router.push('/templates/wizard' as never)}
            />
          </View>
        }
        renderItem={({ item }) => (
          <Pressable onPress={() => router.push(`/templates/${item.id}` as never)}>
            <Card>
              <View style={styles.row}>
                <View style={{ flex: 1, gap: 4 }}>
                  <Text style={styles.name}>{item.name}</Text>
                  <Text style={styles.domain}>{item.domain_hint}</Text>
                </View>
                {item.is_active ? (
                  <Badge tone="brand">Active</Badge>
                ) : (
                  <Button
                    title="Activate"
                    variant="secondary"
                    onPress={() => activate(item.id)}
                    loading={switching === item.id}
                  />
                )}
              </View>
              {item.description ? <Text style={styles.desc}>{item.description}</Text> : null}
              <Text style={styles.meta}>
                {item.fields_schema.length} fields · {item.action_types.length} actions
                {item.is_seed ? ' · seed' : ''}
              </Text>
            </Card>
          </Pressable>
        )}
      />

      <Modal
        visible={warningVisible}
        transparent
        animationType="fade"
        onRequestClose={dismissWarning}
      >
        <View style={styles.modalScrim}>
          <View style={styles.modalCard}>
            <Text style={styles.modalTitle}>Pick a template first</Text>
            <Text style={styles.modalBody}>
              Afterglow needs an active template to analyze calls. Choose one of the presets to
              continue, or browse anyway — most features will be limited until a template is
              active.
            </Text>
            <View style={styles.modalActions}>
              <Button title="Choose template" variant="primary" onPress={dismissWarning} />
              <Button title="Browse anyway" variant="ghost" onPress={browseAnyway} />
            </View>
          </View>
        </View>
      </Modal>
    </>
  );
}

const styles = StyleSheet.create({
  list: { padding: spacing.lg },
  helpText: { color: colors.textMuted, marginBottom: spacing.md },
  row: { flexDirection: 'row', alignItems: 'center', gap: spacing.md },
  name: { color: colors.text, fontSize: 16, fontWeight: '700' },
  domain: { color: colors.textMuted, fontSize: 12, textTransform: 'uppercase', letterSpacing: 1 },
  desc: { color: colors.textMuted, fontSize: 13 },
  meta: { color: colors.textSubtle, fontSize: 12 },
  error: { color: colors.danger, padding: spacing.lg },
  modalScrim: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.55)',
    alignItems: 'center',
    justifyContent: 'center',
    padding: spacing.lg,
  },
  modalCard: {
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.lg,
    gap: spacing.md,
    maxWidth: 420,
    width: '100%',
  },
  modalTitle: { color: colors.text, fontSize: 17, fontWeight: '700' },
  modalBody: { color: colors.textMuted, fontSize: 14, lineHeight: 20 },
  modalActions: { gap: spacing.sm, marginTop: spacing.sm },
});
