import { Avatar, useTheme } from 'react-native-paper';
import { StyleSheet, View } from 'react-native';
import { colorFromPhone, initialsFromName } from '../lib/avatar';

type Props = {
  phone: string;
  name?: string | null;
  size?: number;
  backgroundColor?: string;
};

export function ContactAvatar({ phone, name, size = 48, backgroundColor }: Props) {
  const theme = useTheme();
  const bg = backgroundColor ?? colorFromPhone(phone);
  const initials = initialsFromName(name ?? '');

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
