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
  // When true, the avatar gets a 2dp primary-colored ring (tonal ring
  // pattern: outer View backgroundColor = ring color, padding = ring
  // width, child Avatar at its natural `size`). Acts as a visual legend
  // together with the "Clients" filter chip, which shares the same
  // primary border treatment in Home + Contacts.
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

  // Tonal ring: the wrapper is `outerSize` (= size + ringWidth*2) with
  // `backgroundColor` = ring color and `padding` = ringWidth. The inner
  // Avatar renders at its natural `size`. No clipping, no white gap
  // between ring and avatar, perfect concentric circles. Standard
  // Material / iOS pattern for tonal rings on avatars.
  const ringWidth = isCustomer ? 2 : 1;
  const outerSize = size + ringWidth * 2;
  const wrapperStyle = {
    width: outerSize,
    height: outerSize,
    borderRadius: outerSize / 2,
    padding: ringWidth,
    backgroundColor: isCustomer ? theme.colors.primary : 'rgba(0,0,0,0.08)',
  };

  // Prefer remote photo if provided AND it hasn't 404'd this session.
  if (avatarUrl && !imageFailed) {
    return (
      <View style={[styles.wrapper, wrapperStyle]}>
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
      <View style={[styles.wrapper, wrapperStyle]}>
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
    <View style={[styles.wrapper, wrapperStyle]}>
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
  wrapper: {
    alignItems: 'center',
    justifyContent: 'center',
  },
});
