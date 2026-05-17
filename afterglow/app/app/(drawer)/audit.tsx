import { DrawerActions } from '@react-navigation/native';
import { useFocusEffect, useNavigation } from 'expo-router';
import { useCallback, useState } from 'react';
import { FlatList, RefreshControl, StyleSheet, View } from 'react-native';
import {
  ActivityIndicator,
  Appbar,
  Avatar,
  Banner,
  Chip,
  List,
  type MD3Theme,
  Text,
  useTheme,
} from 'react-native-paper';
import { api, ApiError } from '../../lib/api';
import {
  friendlyAgentLabel,
  friendlyStepLabel,
  humanLabelFromPayload,
} from '../../lib/auditLabels';
import type { AuditLogEntry } from '../../lib/types';

function statusVisuals(status: string, theme: MD3Theme): { icon: string; bg: string; fg: string } {
  if (status === 'success') {
    return { icon: 'check', bg: theme.colors.tertiaryContainer, fg: theme.colors.onTertiaryContainer };
  }
  if (status === 'error') {
    return { icon: 'alert-circle', bg: theme.colors.errorContainer, fg: theme.colors.onErrorContainer };
  }
  if (status === 'skipped' || status === 'degraded') {
    return { icon: 'skip-next-circle-outline', bg: theme.colors.secondaryContainer, fg: theme.colors.onSecondaryContainer };
  }
  return { icon: 'circle-outline', bg: theme.colors.surfaceVariant, fg: theme.colors.onSurfaceVariant };
}

export default function AuditScreen() {
  const theme = useTheme();
  const navigation = useNavigation();
  const [rows, setRows] = useState<AuditLogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
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
      <Appbar.Header mode="small" elevated={false} style={{ backgroundColor: theme.colors.background }}>
        <Appbar.Action icon="menu" onPress={() => navigation.dispatch(DrawerActions.openDrawer())} />
        <Appbar.Content title="Audit log" />
      </Appbar.Header>

      {error ? (
        <Banner visible icon="alert-circle-outline" actions={[{ label: 'Retry', onPress: load }]}>
          {error}
        </Banner>
      ) : null}

      <FlatList
        data={rows}
        keyExtractor={(r) => r.id}
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
        renderItem={({ item }) => {
          const v = statusVisuals(item.status, theme);
          const humanLabel = humanLabelFromPayload(item.payload);
          return (
            <List.Item
              title={friendlyAgentLabel(item.agent_name)}
              description={() => (
                <View style={{ gap: 4, marginTop: 2 }}>
                  <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 4, alignItems: 'center' }}>
                    <Chip
                      compact
                      mode="flat"
                      style={{ backgroundColor: v.bg }}
                      textStyle={{ color: v.fg, fontSize: 11 }}
                    >
                      {item.status}
                    </Chip>
                    <Chip compact mode="outlined" textStyle={{ fontSize: 11 }}>
                      {friendlyStepLabel(item.step_type)}
                    </Chip>
                    {item.model ? (
                      <Chip compact mode="outlined" textStyle={{ fontSize: 11 }}>
                        {item.model}
                      </Chip>
                    ) : null}
                    {item.duration_ms != null ? (
                      <Text
                        variant="labelSmall"
                        style={{ color: theme.colors.onSurfaceVariant, fontFamily: 'monospace' }}
                      >
                        {item.duration_ms}ms
                      </Text>
                    ) : null}
                  </View>
                  {humanLabel ? (
                    <Text variant="bodySmall">{humanLabel}</Text>
                  ) : null}
                  {item.input_tokens != null || item.output_tokens != null ? (
                    <Text
                      variant="labelSmall"
                      style={{ color: theme.colors.onSurfaceVariant, fontFamily: 'monospace' }}
                    >
                      {item.input_tokens ?? 0} in · {item.output_tokens ?? 0} out tokens
                    </Text>
                  ) : null}
                  {item.error ? (
                    <Text variant="bodySmall" style={{ color: theme.colors.error }}>
                      {item.error}
                    </Text>
                  ) : null}
                </View>
              )}
              left={(p) => (
                <Avatar.Icon
                  {...p}
                  icon={v.icon}
                  size={40}
                  color={v.fg}
                  style={[{ backgroundColor: v.bg }, p.style]}
                />
              )}
            />
          );
        }}
        ListEmptyComponent={
          <View style={{ paddingTop: 64, alignItems: 'center' }}>
            <Text variant="bodyMedium" style={{ color: theme.colors.onSurfaceVariant }}>
              No audit entries yet.
            </Text>
          </View>
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({});
