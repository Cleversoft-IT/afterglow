import { Pressable, View } from 'react-native';
import {
  Chip,
  Icon,
  IconButton,
  List,
  Text,
  useTheme,
  type MD3Theme,
} from 'react-native-paper';
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
  onRidial?: (phone: string) => void;
};

type StatusIconInfo = { icon: string; color: string };

// Pixel-dialer style: every row reports its status as a directional arrow,
// not a text label. The companion "ridial" phone-outline icon lives in the
// trailing area for every row, regardless of status.
function statusIconInfo(call: CallListItem, theme: MD3Theme): StatusIconInfo {
  if (call.status === 'failed') {
    if (call.failure_kind === 'pipeline_error') {
      return { icon: 'alert-circle-outline', color: theme.colors.error };
    }
    return { icon: 'arrow-bottom-left', color: theme.colors.error };
  }
  if (call.status === 'transcribing' || call.status === 'analyzing') {
    return { icon: 'progress-clock', color: theme.colors.primary };
  }
  if (call.status === 'pending') {
    return { icon: 'clock-outline', color: theme.colors.onSurfaceVariant };
  }
  return { icon: 'arrow-bottom-left', color: theme.colors.onSurfaceVariant };
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

// Compact icon-only marker used in non-bookings filters to signal that the
// row has a booking attached, without the full slot text. Tap is decorative
// — propagates to the List.Item onPress (open detail).
function BookingMarker() {
  const theme = useTheme();
  return (
    <View
      style={{
        width: 28,
        height: 28,
        borderRadius: 14,
        backgroundColor: theme.colors.secondaryContainer,
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <Icon
        source="calendar-blank-outline"
        size={16}
        color={theme.colors.onSecondaryContainer}
      />
    </View>
  );
}

// Trailing phone-outline button (Pixel system-dialer pattern). Pressing it
// must NOT trigger the row's onPress (call detail navigation). Paper's
// IconButton already stops native propagation; the surrounding Pressable
// is a safety net on react-native-web where event bubbling differs.
function RidialButton({
  phone,
  onRidial,
}: {
  phone: string;
  onRidial?: (phone: string) => void;
}) {
  const theme = useTheme();
  if (!onRidial) return null;
  return (
    <Pressable
      onPress={(e) => {
        e.stopPropagation?.();
        onRidial(phone);
      }}
      accessibilityRole="button"
      accessibilityLabel={`Call ${phone}`}
    >
      <IconButton
        icon="phone-outline"
        size={22}
        iconColor={theme.colors.onSurfaceVariant}
        onPress={() => onRidial(phone)}
        accessibilityLabel={`Call ${phone}`}
      />
    </Pressable>
  );
}

export function CallRow({ call, booking, mode, onPress, onRidial }: Props) {
  const theme = useTheme();
  const { locale } = useLocale();
  const caller = resolveFromCallItem(call);
  const status = statusIconInfo(call, theme);
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
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
            <Icon source={status.icon} size={14} color={status.color} />
            <Text variant="bodySmall" style={{ color: status.color }}>
              {formatRelativeTime(call.created_at, locale)}
            </Text>
          </View>
        );
      })()}
      right={() => (
        <View
          style={{
            flexDirection: 'row',
            alignItems: 'center',
            gap: 4,
            paddingRight: 4,
          }}
        >
          {isBookingsMode && booking ? (
            <BookingBadge booking={booking} />
          ) : booking ? (
            <BookingMarker />
          ) : null}
          <RidialButton phone={call.phone_e164} onRidial={onRidial} />
        </View>
      )}
      style={{ paddingRight: 0 }}
    />
  );
}
