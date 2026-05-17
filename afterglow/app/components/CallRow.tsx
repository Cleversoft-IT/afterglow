import { View } from 'react-native';
import { Chip, Icon, List, Text, useTheme } from 'react-native-paper';
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
  onPress: () => void;
};

function directionIcon(status: string): string {
  if (status === 'failed') return 'phone-missed';
  return 'phone-incoming';
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
  const isMissed = call.status === 'failed';
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
      description={() => {
        if (isBookingsMode && booking) {
          // In bookings mode the whole row is about the booking; show title
          // (or summary) as the description and let the badge carry the slot.
          const p = booking.payload as Record<string, unknown>;
          const titleText =
            booking.title ||
            (typeof p.booking_title === 'string' ? p.booking_title : null) ||
            booking.summary ||
            null;
          return (
            <Text
              variant="bodySmall"
              numberOfLines={1}
              style={{ color: theme.colors.onSurfaceVariant }}
            >
              {titleText ?? ''}
            </Text>
          );
        }
        return (
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
            <Icon
              source={directionIcon(call.status)}
              size={14}
              color={isMissed ? theme.colors.error : theme.colors.onSurfaceVariant}
            />
            <Text
              variant="bodySmall"
              style={{ color: isMissed ? theme.colors.error : theme.colors.onSurfaceVariant }}
            >
              {caller.label} · {formatRelativeTime(call.created_at, locale)}
            </Text>
          </View>
        );
      }}
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
