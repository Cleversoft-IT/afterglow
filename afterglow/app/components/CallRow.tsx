import { View } from 'react-native';
import { Chip, List, Text, useTheme, type MD3Theme } from 'react-native-paper';
import { ContactAvatar } from './ContactAvatar';
import { resolveFromCallItem } from '../lib/callerResolver';
import { formatBookingSlot, formatRelativeTime } from '../lib/dateFormat';
import { useLocale } from '../lib/LocaleContext';
import type { BookingListItem, CallListItem } from '../lib/types';

export type CallFilterKey = 'all' | 'missed' | 'bookings' | 'clients' | 'saved' | 'unsaved';

type Props = {
  call: CallListItem;
  booking?: BookingListItem;
  mode: CallFilterKey;
  onPress?: () => void;
};

type StatusLabel = { text: string; color: string };

// Inbound-only demo: every non-failed call is an "incoming" one. We surface a
// semantic word rather than the phone icon (which previously misrendered on
// completed rows) so missed/processing states are unambiguous at a glance.
function statusLabel(call: CallListItem, theme: MD3Theme): StatusLabel {
  if (call.status === 'failed') {
    if (call.failure_kind === 'pipeline_error') {
      return { text: 'Pipeline error', color: theme.colors.error };
    }
    return { text: 'Missed', color: theme.colors.error };
  }
  if (call.status === 'transcribing' || call.status === 'analyzing') {
    return { text: 'Analyzing…', color: theme.colors.primary };
  }
  if (call.status === 'pending') {
    return { text: 'Pending', color: theme.colors.onSurfaceVariant };
  }
  return { text: 'Incoming', color: theme.colors.onSurfaceVariant };
}

function BookingBadge({ booking }: { booking: BookingListItem }) {
  const theme = useTheme();
  const { locale } = useLocale();
  const p = booking.payload as Record<string, unknown>;
  const date = typeof p.booking_date === 'string' ? p.booking_date : null;
  const time = typeof p.booking_time === 'string' ? p.booking_time : null;
  const partySize =
    typeof p.party_size === 'number' ? p.party_size : Number(p.party_size) || null;

  const slot = formatBookingSlot(date, time, locale);
  const label = partySize ? `${slot} · party ${partySize}` : slot || 'Booking';

  return (
    <Chip
      compact
      mode="flat"
      icon="calendar-blank-outline"
      style={{ backgroundColor: theme.colors.secondaryContainer }}
      textStyle={{ fontSize: 11, color: theme.colors.onSecondaryContainer }}
    >
      {label}
    </Chip>
  );
}

export function CallRow({ call, booking, mode, onPress }: Props) {
  const theme = useTheme();
  const { locale } = useLocale();
  const caller = resolveFromCallItem(call);
  const status = statusLabel(call, theme);
  const isBookingsMode = mode === 'bookings';

  return (
    <List.Item
      onPress={onPress}
      left={() => (
        <View style={{ paddingLeft: 8, justifyContent: 'center' }}>
          <ContactAvatar
            phone={call.phone_e164}
            name={caller.display_name}
            avatarUrl={caller.avatar_url}
            size={48}
            isCustomer={caller.is_customer}
          />
        </View>
      )}
      title={(props) => (
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
          <Text {...props} variant="bodyLarge" numberOfLines={1} style={{ flexShrink: 1 }}>
            {caller.display_name}
          </Text>
        </View>
      )}
      description={(() => {
        if (isBookingsMode) {
          // In bookings mode show the customer's tags (if any) as the
          // description. The right-side BookingBadge already carries the
          // slot info; tags give context that's actually useful to the
          // operator (e.g. "repeat · gluten_free"). When the customer
          // has no tags we return `undefined` so List.Item skips the
          // description slot entirely instead of leaving an empty line.
          const tags = call.customer_tags ?? [];
          if (tags.length === 0) return undefined;
          const text = tags.slice(0, 3).join(' · ');
          return () => (
            <Text
              variant="bodySmall"
              numberOfLines={1}
              style={{ color: theme.colors.onSurfaceVariant }}
            >
              {text}
            </Text>
          );
        }
        return () => (
          <Text variant="bodySmall" style={{ color: status.color }}>
            {status.text} · {formatRelativeTime(call.created_at, locale)}
          </Text>
        );
      })()}
      right={
        booking
          ? () => (
              <View style={{ justifyContent: 'center', paddingRight: 12 }}>
                <BookingBadge booking={booking} />
              </View>
            )
          : undefined
      }
      style={{ paddingRight: 0 }}
    />
  );
}
