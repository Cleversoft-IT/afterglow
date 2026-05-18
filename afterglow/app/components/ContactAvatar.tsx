import { useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { Avatar, useTheme } from 'react-native-paper';
import { colorFromPhone, initialsFromName } from '../lib/avatar';

type Props = {
  phone: string;
  name?: string | null;
  avatarUrl?: string | null;
  size?: number;
  backgroundColor?: string;
  // When true, the avatar gets a 2dp primary-colored border to flag the
  // contact as a known customer (has a Customer row in the DB). Acts as
  // a visual legend together with the "Clients" filter chip, which
  // shares the same border treatment in the Home filter row.
  isCustomer?: boolean;
};

export function ContactAvatar({
  phone,
  name,
  avatarUrl,
  size = 48,
  backgroundColor,
  isCustomer = false,
}: Props) {
  const theme = useTheme();
  const [imageFailed, setImageFailed] = useState(false);
  const bg = backgroundColor ?? colorFromPhone(phone);
  const initials = initialsFromName(name ?? '');

  const borderStyle = {
    width: size,
    height: size,
    borderRadius: size / 2,
    borderWidth: isCustomer ? 2 : 1,
    borderColor: isCustomer ? theme.colors.primary : 'rgba(0,0,0,0.08)',
  };

  // Prefer remote photo if provided AND it hasn't 404'd this session.
  if (avatarUrl && !imageFailed) {
    return (
      <View style={[styles.borderWrapper, borderStyle]}>
        <Avatar.Image
          size={size}
          source={{ uri: avatarUrl }}
          onError={() => setImageFailed(true)}
        />
      </View>
    );
  }

  if (!initials) {
    return (
      <View style={[styles.borderWrapper, borderStyle]}>
        <Avatar.Icon
          icon="account"
          size={size}
          color="#FFFFFF"
          style={{ backgroundColor: bg }}
        />
      </View>
    );
  }

  return (
    <View style={[styles.borderWrapper, borderStyle]}>
      <Avatar.Text
        size={size}
        label={initials}
        color="#FFFFFF"
        style={{ backgroundColor: bg }}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  borderWrapper: {
    overflow: 'hidden',
  },
});
