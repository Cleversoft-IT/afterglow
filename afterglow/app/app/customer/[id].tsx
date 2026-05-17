import { useLocalSearchParams, useRouter } from 'expo-router';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';
import {
  ActivityIndicator,
  Avatar,
  Banner,
  Card,
  Chip,
  List,
  Text,
  useTheme,
} from 'react-native-paper';
import { api, ApiError } from '../../lib/api';
import { ContactAvatar } from '../../components/ContactAvatar';
import { formatDateTime, formatRelativeTime } from '../../lib/dateFormat';
import { flagFromE164 } from '../../lib/flagFromE164';
import { useLocale } from '../../lib/LocaleContext';
import { findMockContact } from '../../lib/mockContacts';
import type { AppTheme } from '../../lib/paperTheme';
import type { CallListItem, CustomerCard } from '../../lib/types';

type CallStatusLabel = { label: string; bg: string; fg: string };

function statusChipForCall(call: CallListItem, theme: AppTheme): CallStatusLabel {
  if (call.status === 'completed') {
    return {
      label: 'Completed',
      bg: theme.colors.successContainer,
      fg: theme.colors.onSuccessContainer,
    };
  }
  if (call.status === 'failed') {
    if (call.failure_kind === 'pipeline_error') {
      return {
        label: 'Pipeline error',
        bg: theme.colors.errorContainer,
        fg: theme.colors.onErrorContainer,
      };
    }
    return {
      label: 'Missed',
      bg: theme.colors.secondaryContainer,
      fg: theme.colors.onSecondaryContainer,
    };
  }
  if (call.status === 'transcribing' || call.status === 'analyzing') {
    return {
      label: 'Analyzing…',
      bg: theme.colors.secondaryContainer,
      fg: theme.colors.onSecondaryContainer,
    };
  }
  const label = call.status
    ? call.status[0].toUpperCase() + call.status.slice(1)
    : '';
  return {
    label,
    bg: theme.colors.secondaryContainer,
    fg: theme.colors.onSecondaryContainer,
  };
}

export default function CustomerDetailScreen() {
  const theme = useTheme<AppTheme>();
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const { locale } = useLocale();
  const [customer, setCustomer] = useState<CustomerCard | null>(null);
  const [calls, setCalls] = useState<CallListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!id) return;
    try {
      setError(null);
      const [c, cs] = await Promise.all([
        api.getCustomer(id),
        api.listCalls({ customer_id: id, limit: 20 }),
      ]);
      setCustomer(c);
      setCalls(cs);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  const display = customer?.display_name ?? customer?.phone_e164 ?? '';
  const facts = useMemo(
    () => Object.entries(customer?.profile_facts ?? {}),
    [customer],
  );

  if (loading) {
    return (
      <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center' }}>
        <ActivityIndicator />
      </View>
    );
  }
  if (error || !customer) {
    return (
      <Banner visible icon="alert-circle-outline" actions={[{ label: 'Retry', onPress: load }]}>
        {error ?? 'Contact not found.'}
      </Banner>
    );
  }

  const flag = flagFromE164(customer.phone_e164);
  const mockAvatarUrl = findMockContact(customer.phone_e164)?.avatar_url ?? null;

  return (
    <ScrollView contentContainerStyle={styles.scroll}>
      <Card mode="elevated">
        <Card.Title
          title={display}
          subtitle={
            <View style={styles.subtitleRow}>
              <Text style={{ fontSize: 18 }}>{flag}</Text>
              <Text variant="bodyMedium" style={{ color: theme.colors.onSurfaceVariant }}>
                {customer.phone_e164}
              </Text>
              <Text variant="bodySmall" style={{ color: theme.colors.onSurfaceVariant }}>
                · {customer.total_calls} calls
              </Text>
            </View>
          }
          left={() => (
            <ContactAvatar
              phone={customer.phone_e164}
              name={display}
              avatarUrl={mockAvatarUrl}
              size={56}
            />
          )}
          leftStyle={{ marginRight: 16 }}
          right={() =>
            customer.preferred_language ? (
              <Chip mode="flat" compact style={{ marginRight: 12 }}>
                {customer.preferred_language}
              </Chip>
            ) : null
          }
        />
        {customer.last_call_at ? (
          <Card.Content>
            <Text variant="bodySmall" style={{ color: theme.colors.onSurfaceVariant }}>
              Last call {formatDateTime(customer.last_call_at, locale)}
            </Text>
          </Card.Content>
        ) : null}
      </Card>

      {customer.tags.length > 0 ? (
        <Card mode="elevated">
          <Card.Title title="Tags" />
          <Card.Content>
            <View style={styles.chipRow}>
              {customer.tags.map((t) => (
                <Chip key={t} mode="outlined" compact>
                  {t}
                </Chip>
              ))}
            </View>
          </Card.Content>
        </Card>
      ) : null}

      {facts.length > 0 ? (
        <Card mode="elevated">
          <Card.Title title="Known facts" />
          <Card.Content>
            {facts.map(([k, v]) => (
              <List.Item
                key={k}
                title={k.replace(/_/g, ' ')}
                titleStyle={{ textTransform: 'capitalize' }}
                description={Array.isArray(v) ? v.join(', ') : typeof v === 'object' ? JSON.stringify(v) : String(v)}
                style={{ paddingHorizontal: 0 }}
              />
            ))}
          </Card.Content>
        </Card>
      ) : null}

      <Card mode="elevated" style={{ backgroundColor: theme.colors.elevation.level2 }}>
        <Card.Title
          title="Next-call briefing"
          left={(p) => <Avatar.Icon {...p} icon="lightbulb-on-outline" />}
        />
        <Card.Content>
          {customer.memory_summary ? (
            <Text variant="bodyMedium" style={{ lineHeight: 20 }}>
              {customer.memory_summary}
            </Text>
          ) : (
            <Text variant="bodyMedium" style={{ color: theme.colors.onSurfaceVariant, fontStyle: 'italic' }}>
              No briefing yet — Afterglow writes one after each call.
            </Text>
          )}
        </Card.Content>
      </Card>

      <Card mode="elevated">
        <Card.Title title={`Calls (${calls.length})`} />
        <Card.Content style={{ paddingHorizontal: 0 }}>
          {calls.length === 0 ? (
            <Text
              variant="bodyMedium"
              style={{ color: theme.colors.onSurfaceVariant, fontStyle: 'italic', paddingHorizontal: 16 }}
            >
              No calls yet for this contact.
            </Text>
          ) : (
            calls.map((c) => {
              const sc = statusChipForCall(c, theme);
              return (
                <List.Item
                  key={c.id}
                  title={formatDateTime(c.created_at, locale)}
                  description={`${c.detected_language ?? '—'} · ${formatRelativeTime(c.created_at, locale)}`}
                  left={() => <List.Icon icon="phone-incoming" />}
                  right={() => (
                    <Chip mode="flat" compact style={[{ marginRight: 8 }, { backgroundColor: sc.bg }]} textStyle={{ color: sc.fg }}>
                      {sc.label}
                    </Chip>
                  )}
                  onPress={() => router.push(`/call/${c.id}` as never)}
                />
              );
            })
          )}
        </Card.Content>
      </Card>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  scroll: { padding: 16, gap: 16, paddingBottom: 48 },
  chipRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6 },
  subtitleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    flexWrap: 'wrap',
    marginTop: 2,
  },
});
