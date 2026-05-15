import { useFocusEffect } from 'expo-router';
import { useCallback, useState } from 'react';
import { ActivityIndicator, FlatList, StyleSheet, Text, View } from 'react-native';
import { Badge } from '../../components/Badge';
import { Card } from '../../components/Card';
import { api, ApiError } from '../../lib/api';
import { colors, spacing } from '../../lib/theme';
import type { AuditLogEntry } from '../../lib/types';

export default function AuditScreen() {
  const [rows, setRows] = useState<AuditLogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setError(null);
      const data = await api.listAudit();
      setRows(data);
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

  if (loading) return <ActivityIndicator color={colors.brand} style={{ marginTop: 32 }} />;
  if (error) return <Text style={styles.error}>{error}</Text>;

  return (
    <FlatList
      data={rows}
      keyExtractor={(r) => r.id}
      contentContainerStyle={{ padding: spacing.lg }}
      ItemSeparatorComponent={() => <View style={{ height: spacing.sm }} />}
      ListEmptyComponent={<Text style={styles.empty}>No audit entries yet.</Text>}
      renderItem={({ item }) => (
        <Card>
          <View style={styles.headerRow}>
            <Text style={styles.agent}>{item.agent_name}</Text>
            <Badge tone={item.status === 'success' ? 'success' : 'danger'}>{item.status}</Badge>
          </View>
          <Text style={styles.meta}>{item.step_type}{item.model ? ` · ${item.model}` : ''}</Text>
          {item.duration_ms != null ? (
            <Text style={styles.meta}>{item.duration_ms} ms</Text>
          ) : null}
          {item.error ? <Text style={styles.error}>{item.error}</Text> : null}
        </Card>
      )}
    />
  );
}

const styles = StyleSheet.create({
  headerRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  agent: { color: colors.text, fontWeight: '700' },
  meta: { color: colors.textMuted, fontSize: 12 },
  empty: { color: colors.textMuted, textAlign: 'center', marginTop: 32 },
  error: { color: colors.danger, padding: spacing.lg },
});
