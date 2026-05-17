import { Card as PaperCard } from 'react-native-paper';
import type { ReactNode } from 'react';
import type { StyleProp, ViewStyle } from 'react-native';

export function Card({
  children,
  style,
}: {
  children?: ReactNode;
  style?: StyleProp<ViewStyle>;
}) {
  return (
    <PaperCard mode="elevated" style={style}>
      <PaperCard.Content>{children}</PaperCard.Content>
    </PaperCard>
  );
}
