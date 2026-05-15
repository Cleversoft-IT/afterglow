import { useFocusEffect } from 'expo-router';
import { useCallback, useState } from 'react';
import { ActivityIndicator, FlatList, StyleSheet, Text, View } from 'react-native';
import { Badge } from '../../components/Badge';
import { Button } from '../../components/Button';
import { Card } from '../../components/Card';
import { api, ApiError } from '../../lib/api';
import { colors, spacing } from '../../lib/theme';
import type { TemplateView } from '../../lib/types';

export default function TemplatesScreen() {
  const [templates, setTemplates] = useState<TemplateView[]>([]);
  const [loading, setLoading] = useState(true);
  const [switching, setSwitching] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

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
    <FlatList
      data={templates}
      keyExtractor={(t) => t.id}
      contentContainerStyle={styles.list}
      ItemSeparatorComponent={() => <View style={{ height: spacing.md }} />}
      ListHeaderComponent={
        <Text style={styles.helpText}>
          Pick which preset drives the call analysis. Exactly one template can be active at a time.
        </Text>
      }
      renderItem={({ item }) => (
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
          </Text>
        </Card>
      )}
    />
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
});
