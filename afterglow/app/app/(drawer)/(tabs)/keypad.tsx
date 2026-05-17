import { DrawerActions } from '@react-navigation/native';
import { useNavigation } from 'expo-router';
import { useMemo, useState } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import {
  Appbar,
  FAB,
  IconButton,
  Snackbar,
  Text,
  useTheme,
} from 'react-native-paper';
import { callGreen } from '../../../lib/paperTheme';

type Key = { digit: string; letters: string };

const KEYS: Key[] = [
  { digit: '1', letters: '' },
  { digit: '2', letters: 'ABC' },
  { digit: '3', letters: 'DEF' },
  { digit: '4', letters: 'GHI' },
  { digit: '5', letters: 'JKL' },
  { digit: '6', letters: 'MNO' },
  { digit: '7', letters: 'PQRS' },
  { digit: '8', letters: 'TUV' },
  { digit: '9', letters: 'WXYZ' },
  { digit: '*', letters: '' },
  { digit: '0', letters: '+' },
  { digit: '#', letters: '' },
];

export default function KeypadScreen() {
  const theme = useTheme();
  const navigation = useNavigation();
  const [digits, setDigits] = useState('');
  const [snackbar, setSnackbar] = useState<string | null>(null);

  const append = (d: string) => setDigits((s) => s + d);
  const backspace = () => setDigits((s) => s.slice(0, -1));

  const styles = useMemo(
    () =>
      StyleSheet.create({
        container: { flex: 1, backgroundColor: theme.colors.background },
        display: {
          alignItems: 'center',
          justifyContent: 'center',
          paddingVertical: 24,
          paddingHorizontal: 24,
          minHeight: 96,
        },
        displayText: {
          color: theme.colors.onSurface,
          fontVariant: ['tabular-nums'],
          letterSpacing: 1,
        },
        backspaceWrap: {
          position: 'absolute',
          right: 8,
          top: '50%',
          marginTop: -22,
        },
        grid: {
          flex: 1,
          paddingHorizontal: 32,
          justifyContent: 'center',
          gap: 16,
        },
        row: { flexDirection: 'row', justifyContent: 'space-between', gap: 16 },
        key: {
          flex: 1,
          aspectRatio: 1.5,
          borderRadius: 16,
          alignItems: 'center',
          justifyContent: 'center',
        },
        keyPressed: { backgroundColor: theme.colors.surfaceVariant },
        keyText: { color: theme.colors.onSurface, fontWeight: '500' },
        keyLetters: {
          color: theme.colors.onSurfaceVariant,
          fontSize: 11,
          letterSpacing: 1,
          marginTop: -2,
        },
        callBar: { paddingVertical: 24, alignItems: 'center' },
      }),
    [theme],
  );

  const rows: Key[][] = [];
  for (let i = 0; i < KEYS.length; i += 3) rows.push(KEYS.slice(i, i + 3));

  return (
    <View style={styles.container}>
      <Appbar.Header mode="small" elevated={false} style={{ backgroundColor: theme.colors.background }}>
        <Appbar.Action icon="menu" onPress={() => navigation.dispatch(DrawerActions.openDrawer())} />
        <Appbar.Content title="" />
      </Appbar.Header>

      <View style={styles.display}>
        <Text variant="displaySmall" style={styles.displayText} numberOfLines={1}>
          {digits || ' '}
        </Text>
        {digits.length > 0 && (
          <View style={styles.backspaceWrap}>
            <IconButton icon="backspace-outline" onPress={backspace} />
          </View>
        )}
      </View>

      <View style={styles.grid}>
        {rows.map((row, ri) => (
          <View key={ri} style={styles.row}>
            {row.map((k) => (
              <Pressable
                key={k.digit}
                onPress={() => append(k.digit)}
                style={({ pressed }) => [styles.key, pressed && styles.keyPressed]}
              >
                <Text variant="headlineMedium" style={styles.keyText}>
                  {k.digit}
                </Text>
                {k.letters ? <Text style={styles.keyLetters}>{k.letters}</Text> : null}
              </Pressable>
            ))}
          </View>
        ))}
      </View>

      <View style={styles.callBar}>
        <FAB
          icon="phone"
          color="#FFFFFF"
          style={{ backgroundColor: callGreen, borderRadius: 36 }}
          size="medium"
          onPress={() =>
            setSnackbar(
              digits
                ? 'Demo: use the Simulator from the drawer to test the AI pipeline.'
                : 'Type a number first, then tap Call.',
            )
          }
        />
      </View>

      <Snackbar visible={!!snackbar} onDismiss={() => setSnackbar(null)} duration={3500}>
        {snackbar ?? ''}
      </Snackbar>
    </View>
  );
}
