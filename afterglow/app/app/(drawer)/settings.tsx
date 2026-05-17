import { DrawerActions } from '@react-navigation/native';
import { router, useNavigation } from 'expo-router';
import { useState } from 'react';
import { Alert, Platform, ScrollView, StyleSheet, View } from 'react-native';
import {
  Appbar,
  Button,
  Dialog,
  List,
  Portal,
  SegmentedButtons,
  Text,
  useTheme,
} from 'react-native-paper';
import { api, ApiError, isDemoMode } from '../../lib/api';
import type { Locale } from '../../lib/dateFormat';
import { useLocale } from '../../lib/LocaleContext';
import { callRed } from '../../lib/paperTheme';
import { useTheme as useAppTheme } from '../../lib/ThemeContext';
import type { ThemePreference } from '../../lib/theme';

export default function SettingsScreen() {
  const theme = useTheme();
  const navigation = useNavigation();
  const { mode, setMode } = useAppTheme();
  const { locale, setLocale } = useLocale();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resetDialogVisible, setResetDialogVisible] = useState(false);

  const handleReset = async () => {
    setResetDialogVisible(false);
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
    <View style={{ flex: 1, backgroundColor: theme.colors.background }}>
      <Appbar.Header mode="small" elevated={false} style={{ backgroundColor: theme.colors.background }}>
        <Appbar.Action icon="menu" onPress={() => navigation.dispatch(DrawerActions.openDrawer())} />
        <Appbar.Content title="Settings" />
      </Appbar.Header>

      <ScrollView contentContainerStyle={styles.scroll}>
        <List.Section>
          <List.Subheader>Appearance</List.Subheader>
          <View style={{ paddingHorizontal: 16, paddingBottom: 16 }}>
            <Text variant="bodyMedium" style={{ color: theme.colors.onSurfaceVariant, marginBottom: 12 }}>
              Choose how Afterglow looks on this device. Your preference is saved locally.
            </Text>
            <SegmentedButtons
              value={mode}
              onValueChange={(next) => setMode(next as ThemePreference)}
              buttons={[
                { value: 'auto', label: 'Auto', icon: 'theme-light-dark' },
                { value: 'light', label: 'Light', icon: 'white-balance-sunny' },
                { value: 'dark', label: 'Dark', icon: 'weather-night' },
              ]}
            />
          </View>
        </List.Section>

        <List.Section>
          <List.Subheader>Format</List.Subheader>
          <View style={{ paddingHorizontal: 16, paddingBottom: 16 }}>
            <Text variant="bodyMedium" style={{ color: theme.colors.onSurfaceVariant, marginBottom: 12 }}>
              Pick how dates and times are formatted across the app. Italian uses 24-hour and DD/MM/YYYY; English uses 12-hour and MM/DD/YYYY.
            </Text>
            <SegmentedButtons
              value={locale}
              onValueChange={(next) => setLocale(next as Locale)}
              buttons={[
                { value: 'it', label: 'Italian', icon: 'translate' },
                { value: 'en', label: 'English', icon: 'translate' },
              ]}
            />
          </View>
        </List.Section>

        <List.Section>
          <List.Subheader>About</List.Subheader>
          <List.Item
            title="What is Afterglow"
            description="Afterglow turns the seconds after a phone call into structured data, customer memory, and autonomously executed actions."
            descriptionNumberOfLines={4}
            left={(p) => <List.Icon {...p} icon="information-outline" />}
          />
        </List.Section>

        <List.Section>
          <List.Subheader>Diagnostics</List.Subheader>
          <List.Item
            title="Audit log"
            description="Full trace of every pipeline step — agents, tokens, errors."
            left={(p) => <List.Icon {...p} icon="text-box-search-outline" />}
            right={(p) => <List.Icon {...p} icon="chevron-right" />}
            onPress={() => router.push('/(drawer)/audit' as never)}
          />
        </List.Section>

        {isDemoMode() ? (
          <List.Section>
            <List.Subheader>Demo controls</List.Subheader>
            <List.Item
              title={busy ? 'Resetting…' : 'Reset demo session'}
              titleStyle={{ color: callRed }}
              description="Wipes all calls, customers and templates for this session and clears the active template."
              descriptionNumberOfLines={3}
              left={(p) => <List.Icon {...p} icon="restore" color={callRed} />}
              onPress={() => setResetDialogVisible(true)}
              disabled={busy}
            />
            {error ? (
              <Text style={{ color: theme.colors.error, paddingHorizontal: 16, paddingTop: 4 }}>
                {error}
              </Text>
            ) : null}
          </List.Section>
        ) : null}
      </ScrollView>

      <Portal>
        <Dialog visible={resetDialogVisible} onDismiss={() => setResetDialogVisible(false)}>
          <Dialog.Icon icon="restore" />
          <Dialog.Title>Reset demo?</Dialog.Title>
          <Dialog.Content>
            <Text variant="bodyMedium">
              All calls, customers and templates created in this session will be permanently
              deleted. You will start fresh from the seed state.
            </Text>
          </Dialog.Content>
          <Dialog.Actions>
            <Button onPress={() => setResetDialogVisible(false)}>Cancel</Button>
            <Button textColor={callRed} onPress={handleReset}>
              Reset
            </Button>
          </Dialog.Actions>
        </Dialog>
      </Portal>
    </View>
  );
}

const styles = StyleSheet.create({
  scroll: { paddingBottom: 48 },
});
