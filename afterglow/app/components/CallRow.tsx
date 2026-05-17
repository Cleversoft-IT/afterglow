import { View } from 'react-native';
import { Chip, IconButton, List, Text, useTheme } from 'react-native-paper';
import { ContactAvatar } from './ContactAvatar';
import { resolveFromCallItem } from '../lib/callerResolver';
import { formatRelativeTime } from '../lib/dateGrouping';
import type { BookingListItem, CallListItem } from '../lib/types';

type FilterKey = 'all' | 'missed' | 'bookings' | 'saved' | 'unsaved';

type Props = {
  call: CallListItem;
  booking?: BookingListItem;
  mode: FilterKey;
  onPress: () => void;
  onCallIconPress: () => void;
};

function directionIcon(status: string): string {
  if (status === 'failed') return 'phone-missed';
  return 'phone-incoming';
}

export function CallRow({ call, booking, mode, onPress, onCallIconPress }: Props) {
  const theme = useTheme();
  const caller = resolveFromCallItem(call);
  const isMissed = call.status === 'failed';
  const isBookingsMode = mode === 'bookings';

  return (
    <List.Item
      onPress={onPress}
      left={() => (
        <View style={{ paddingLeft: 8, justifyContent: 'center' }}>
          <ContactAvatar phone={call.phone_e164} name={caller.display_name} size={48} />
        </View>
      )}
      title={(props) => (
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
          <Text {...props} variant="bodyLarge" numberOfLines={1} style={{ flexShrink: 1 }}>
            {caller.display_name}
          </Text>
          {booking && (
            <Chip compact mode="flat" icon="calendar-clock" textStyle={{ fontSize: 11 }}>
              Booking
            </Chip>
          )}
        </View>
      )}
      description={() => {
        if (isBookingsMode && booking) {
          const p = booking.payload as Record<string, unknown>;
          const parts: string[] = [];
          const title = booking.title || (typeof p.booking_title === 'string' ? p.booking_title : null);
          if (title) parts.push(title);
          if (typeof p.booking_date === 'string') parts.push(p.booking_date);
          if (typeof p.booking_time === 'string') parts.push(p.booking_time);
          if (p.party_size != null) parts.push(`party of ${p.party_size}`);
          if (!parts.length && booking.summary) parts.push(booking.summary);
          return (
            <Text variant="bodySmall" style={{ color: theme.colors.onSurfaceVariant }}>
              {parts.join(' · ')}
            </Text>
          );
        }
        return (
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
            <IconButton
              icon={directionIcon(call.status)}
              size={14}
              iconColor={isMissed ? theme.colors.error : theme.colors.onSurfaceVariant}
              style={{ margin: 0, padding: 0, width: 14, height: 14 }}
            />
            <Text
              variant="bodySmall"
              style={{ color: isMissed ? theme.colors.error : theme.colors.onSurfaceVariant }}
            >
              {caller.label} · {formatRelativeTime(call.created_at)}
            </Text>
          </View>
        );
      }}
      right={() => (
        <IconButton
          icon="phone-outline"
          onPress={(e) => {
            // Stop the row onPress from firing.
            (e as unknown as { stopPropagation?: () => void })?.stopPropagation?.();
            onCallIconPress();
          }}
        />
      )}
      style={{ paddingRight: 0 }}
    />
  );
}
