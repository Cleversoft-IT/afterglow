import { useEffect, useRef, useState } from 'react';
import { Animated, StyleSheet, View } from 'react-native';
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
  // When true, overlays an additional pulsing primary-colored ring that
  // breathes at ~1.4s cycles so the row reads as "analyzing in
  // progress" even at a glance. Driven by the pipeline status from the
  // calls list (`pending` / `transcribing` / `analyzing` are all
  // surfaced as `analyzing` here).
  analyzing?: boolean;
};

function useAnalyzingPulse(active: boolean) {
  const opacity = useRef(new Animated.Value(0.35)).current;

  useEffect(() => {
    if (!active) {
      opacity.setValue(0);
      return;
    }
    opacity.setValue(0.35);
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(opacity, {
          toValue: 1,
          duration: 700,
          // borderColor / opacity are NOT supported by the native driver
          // on the View transform path, and on react-native-web the
          // native driver is a no-op anyway. Keep it false so the same
          // code path works in Expo Web + native.
          useNativeDriver: false,
        }),
        Animated.timing(opacity, {
          toValue: 0.35,
          duration: 700,
          useNativeDriver: false,
        }),
      ]),
    );
    loop.start();
    return () => loop.stop();
  }, [active, opacity]);

  return opacity;
}

export function ContactAvatar({
  phone,
  name,
  avatarUrl,
  size = 48,
  backgroundColor,
  isCustomer = false,
  analyzing = false,
}: Props) {
  const theme = useTheme();
  const [imageFailed, setImageFailed] = useState(false);
  const bg = backgroundColor ?? colorFromPhone(phone);
  const initials = initialsFromName(name ?? '');
  const pulseOpacity = useAnalyzingPulse(analyzing);

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

  // Analyzing halo: sits OUTSIDE the tonal ring, never clipped, and only
  // costs an extra View when active. The 3px ring + 6px halo keep the row
  // height stable (parent layout reserves the avatar's `outerSize`).
  const haloSize = outerSize + 8;
  const haloStyle = {
    position: 'absolute' as const,
    top: -4,
    left: -4,
    width: haloSize,
    height: haloSize,
    borderRadius: haloSize / 2,
    borderWidth: 3,
    borderColor: theme.colors.primary,
    opacity: pulseOpacity,
  };

  // Prefer remote photo if provided AND it hasn't 404'd this session.
  let inner;
  if (avatarUrl && !imageFailed) {
    inner = (
      <Avatar.Image
        size={size}
        source={{ uri: avatarUrl }}
        onError={() => setImageFailed(true)}
      />
    );
  } else if (!initials) {
    inner = (
      <Avatar.Icon
        icon="account"
        size={size}
        color="#FFFFFF"
        style={{ backgroundColor: bg }}
      />
    );
  } else {
    inner = (
      <Avatar.Text
        size={size}
        label={initials}
        color="#FFFFFF"
        style={{ backgroundColor: bg }}
      />
    );
  }

  return (
    <View style={[styles.wrapper, wrapperStyle]}>
      {analyzing ? <Animated.View pointerEvents="none" style={haloStyle} /> : null}
      {inner}
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: {
    alignItems: 'center',
    justifyContent: 'center',
  },
});
