import { useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { Avatar } from 'react-native-paper';
import { colorFromPhone, initialsFromName } from '../lib/avatar';

type Props = {
  phone: string;
  name?: string | null;
  avatarUrl?: string | null;
  size?: number;
  backgroundColor?: string;
};

export function ContactAvatar({ phone, name, avatarUrl, size = 48, backgroundColor }: Props) {
  const [imageFailed, setImageFailed] = useState(false);
  const bg = backgroundColor ?? colorFromPhone(phone);
  const initials = initialsFromName(name ?? '');

  // Prefer remote photo if provided AND it hasn't 404'd this session.
  if (avatarUrl && !imageFailed) {
    return (
      <View style={[styles.borderWrapper, { width: size, height: size, borderRadius: size / 2 }]}>
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
      <View style={[styles.borderWrapper, { width: size, height: size, borderRadius: size / 2 }]}>
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
    <View style={[styles.borderWrapper, { width: size, height: size, borderRadius: size / 2 }]}>
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
    borderWidth: 1,
    borderColor: 'rgba(0,0,0,0.08)',
    overflow: 'hidden',
  },
});
