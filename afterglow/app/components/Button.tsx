import { Button as PaperButton } from 'react-native-paper';
import { callRed } from '../lib/paperTheme';
import type { StyleProp, ViewStyle } from 'react-native';

type Variant = 'primary' | 'secondary' | 'danger' | 'ghost';

const MODE_BY_VARIANT: Record<Variant, 'contained' | 'outlined' | 'text'> = {
  primary: 'contained',
  secondary: 'outlined',
  danger: 'contained',
  ghost: 'text',
};

export function Button({
  title,
  onPress,
  disabled,
  loading,
  variant = 'primary',
  style,
  icon,
}: {
  title: string;
  onPress?: () => void;
  disabled?: boolean;
  loading?: boolean;
  variant?: Variant;
  style?: StyleProp<ViewStyle>;
  icon?: string;
}) {
  const mode = MODE_BY_VARIANT[variant];
  const buttonColor = variant === 'danger' ? callRed : undefined;
  const textColor = variant === 'danger' ? '#FFFFFF' : undefined;
  return (
    <PaperButton
      mode={mode}
      onPress={onPress}
      disabled={disabled}
      loading={loading}
      icon={icon}
      buttonColor={buttonColor}
      textColor={textColor}
      style={style}
      compact={false}
    >
      {title}
    </PaperButton>
  );
}
