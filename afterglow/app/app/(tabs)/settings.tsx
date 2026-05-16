import { router } from 'expo-router';
import { useState } from 'react';
import { Alert, Platform, ScrollView, StyleSheet, Text } from 'react-native';
import { Button } from '../../components/Button';
import { Card } from '../../components/Card';
import { api, ApiError, isDemoMode } from '../../lib/api';
import { colors, spacing } from '../../lib/theme';

const RESET_CONFIRM_TITLE = 'Reset demo?';
const RESET_CONFIRM_MESSAGE =
  'All calls, customers and templates created in this session will be permanently deleted. You will start fresh from the seed state.';

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
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleReset = async () => {
    const confirmed = await askConfirm();
    if (!confirmed) return;

    setError(null);
    setBusy(true);
    try {
      await api.resetDemo();
      // Hard refresh so every cached fetch (calls list, customers, active
      // template) re-runs from a clean slate and the bootstrap gate has a
      // chance to route the visitor to the Templates screen.
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

const styles = StyleSheet.create({
  scroll: { padding: spacing.lg, gap: spacing.md },
  heading: { color: colors.text, fontWeight: '700', fontSize: 15 },
  body: { color: colors.textMuted, fontSize: 13, lineHeight: 18 },
  error: { color: colors.danger, fontSize: 12, marginTop: spacing.sm },
});
