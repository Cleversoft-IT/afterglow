import { router } from 'expo-router';
import { useMemo, useState } from 'react';
import { Alert, Platform, ScrollView, StyleSheet, Text } from 'react-native';
import { Button } from '../../components/Button';
import { Card } from '../../components/Card';
import { Select } from '../../components/Select';
import { useTheme } from '../../lib/ThemeContext';
import { api, ApiError, isDemoMode } from '../../lib/api';
import { spacing, type ThemeMode } from '../../lib/theme';

const RESET_CONFIRM_TITLE = 'Reset demo?';
const RESET_CONFIRM_MESSAGE =
  'All calls, customers and templates created in this session will be permanently deleted. You will start fresh from the seed state.';

const THEME_OPTIONS = [
  { label: 'Light', value: 'light' },
  { label: 'Dark', value: 'dark' },
] as const;

function askConfirm(): Promise<boolean> {
  if (Platform.OS === 'web') {
    return Promise.resolve(
      typeof window !== 'undefined'
        ? window.confirm(`${RESET_CONFIRM_TITLE}\n\n${RESET_CONFIRM_MESSAGE}`)
        : false,
    );
  }
  return new Promise((resolve) => {
    Alert.alert(RESET_CONFIRM_TITLE, RESET_CONFIRM_MESSAGE, [
      { text: 'Cancel', style: 'cancel', onPress: () => resolve(false) },
      { text: 'Reset', style: 'destructive', onPress: () => resolve(true) },
    ]);
  });
}

export default function SettingsScreen() {
  const { colors, mode, setMode } = useTheme();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const styles = useMemo(
    () =>
      StyleSheet.create({
        scroll: { padding: spacing.lg, gap: spacing.lg, paddingBottom: spacing.xxxl },
        heading: { color: colors.text, fontWeight: '600', fontSize: 16 },
        body: { color: colors.textMuted, fontSize: 14, lineHeight: 21 },
        error: { color: colors.danger, fontSize: 13, marginTop: spacing.sm },
      }),
    [colors],
  );

  const handleReset = async () => {
    const confirmed = await askConfirm();
    if (!confirmed) return;

    setError(null);
    setBusy(true);
    try {
      await api.resetDemo();
      if (Platform.OS === 'web' && typeof window !== 'undefined') {
        window.location.reload();
      } else {
        router.replace('/');
      }
    } catch (e) {
      setBusy(false);
      const msg = e instanceof ApiError ? e.message : String(e);
      setError(msg);
      if (Platform.OS !== 'web') {
        Alert.alert('Reset failed', msg);
      }
    }
  };

  return (
    <ScrollView contentContainerStyle={styles.scroll}>
      <Card>
        <Text style={styles.heading}>Appearance</Text>
        <Text style={styles.body}>
          Choose how Afterglow looks on this device. Your preference is saved locally.
        </Text>
        <Select
          value={mode}
          options={[...THEME_OPTIONS]}
          onChange={(next) => setMode(next as ThemeMode)}
        />
      </Card>

      <Card>
        <Text style={styles.heading}>About</Text>
        <Text style={styles.body}>
          Afterglow turns the seconds after a phone call into structured data, customer memory,
          and autonomously executed actions. The operator handles the call; the AI runs once the
          call ends.
        </Text>
      </Card>

      {isDemoMode() ? (
        <Card>
          <Text style={styles.heading}>Demo controls</Text>
          <Text style={styles.body}>
            Wipes all calls, customers and templates created in this demo session and clears the
            active template. You will be returned to the initial seed state.
          </Text>
          <Button
            title={busy ? 'Resetting…' : 'Reset demo'}
            variant="danger"
            onPress={handleReset}
            loading={busy}
            disabled={busy}
          />
          {error ? <Text style={styles.error}>{error}</Text> : null}
        </Card>
      ) : null}
    </ScrollView>
  );
}
