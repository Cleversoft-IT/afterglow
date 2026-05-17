import { DrawerContentScrollView, DrawerItem } from '@react-navigation/drawer';
import type { DrawerContentComponentProps } from '@react-navigation/drawer';
import { router } from 'expo-router';
import { Drawer } from 'expo-router/drawer';
import { Alert, Platform, View } from 'react-native';
import { Button, Dialog, Divider, Icon, Portal, Text, useTheme } from 'react-native-paper';
import { useState } from 'react';
import { api, ApiError, isDemoMode } from '../../lib/api';
import { callRed } from '../../lib/paperTheme';

type IconRenderProps = { focused: boolean; color: string; size: number };

function DrawerContent(props: DrawerContentComponentProps) {
  const theme = useTheme();
  const [busy, setBusy] = useState(false);
  const [resetDialogVisible, setResetDialogVisible] = useState(false);

  // Drawer passes `color` derived from active/inactive tint. We honor it
  // and fall back to onSurface if the navigator doesn't provide one yet
  // (first render flicker), so icons stay visible in dark mode.
  const iconColor = (focused: boolean, color: string | null | undefined) =>
    focused ? theme.colors.primary : color || theme.colors.onSurface;

  // Same flow as Settings → keep the two paths byte-identical so the
  // demo-reset UX never diverges. `window.confirm` was previously used
  // here but races with the drawer auto-close on press, leaving the
  // button stuck on "Resetting…" if the modal lost focus.
  const runReset = async () => {
    setResetDialogVisible(false);
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
      if (Platform.OS !== 'web') {
        Alert.alert('Reset failed', e instanceof ApiError ? e.message : String(e));
      }
    }
  };

  // Active state from the current route — we expose the (tabs) home as
  // a custom item because Drawer.Screen for (tabs) is hidden below.
  const activeRouteName = props.state.routes[props.state.index]?.name ?? '';
  const isOnCalls = activeRouteName === '(tabs)';

  return (
    <DrawerContentScrollView {...props} contentContainerStyle={{ paddingTop: 0 }}>
      <View style={{ paddingHorizontal: 24, paddingTop: 32, paddingBottom: 16, gap: 4 }}>
        {/* Wordmark replicates the demo site: bold "after" in onSurface,
            "glow" in primary — see afterglow/demo-site/src/App.tsx:129-130. */}
        <Text style={{ fontSize: 22, fontWeight: '800', letterSpacing: -0.3 }}>
          <Text style={{ color: theme.colors.onSurface }}>after</Text>
          <Text style={{ color: theme.colors.primary }}>glow</Text>
        </Text>
        <Text variant="bodyMedium" style={{ color: theme.colors.onSurfaceVariant }}>
          AI dialer
        </Text>
      </View>
      <Divider />
      <DrawerItem
        label="Calls"
        focused={isOnCalls}
        activeTintColor={theme.colors.primary}
        activeBackgroundColor={theme.colors.secondaryContainer}
        icon={({ color, size }: IconRenderProps) => (
          <Icon source="phone-outline" size={size} color={iconColor(isOnCalls, color)} />
        )}
        labelStyle={{ color: isOnCalls ? theme.colors.primary : theme.colors.onSurface, fontWeight: '500' }}
        onPress={() => router.navigate('/(drawer)/(tabs)' as never)}
      />
      <DrawerItem
        label="Contacts"
        icon={({ focused, color, size }: IconRenderProps) => (
          <Icon source="account-multiple-outline" size={size} color={iconColor(focused, color)} />
        )}
        labelStyle={{ color: theme.colors.onSurface, fontWeight: '500' }}
        onPress={() => router.push('/(drawer)/contacts' as never)}
      />
      <DrawerItem
        label="Templates"
        icon={({ focused, color, size }: IconRenderProps) => (
          <Icon source="view-grid-outline" size={size} color={iconColor(focused, color)} />
        )}
        labelStyle={{ color: theme.colors.onSurface, fontWeight: '500' }}
        onPress={() => router.push('/(drawer)/templates' as never)}
      />
      <DrawerItem
        label="Audit log"
        icon={({ focused, color, size }: IconRenderProps) => (
          <Icon source="text-box-search-outline" size={size} color={iconColor(focused, color)} />
        )}
        labelStyle={{ color: theme.colors.onSurface, fontWeight: '500' }}
        onPress={() => router.push('/(drawer)/audit' as never)}
      />
      <DrawerItem
        label="Test simulator"
        icon={({ focused, color, size }: IconRenderProps) => (
          <Icon source="phone-in-talk-outline" size={size} color={iconColor(focused, color)} />
        )}
        labelStyle={{ color: theme.colors.onSurface, fontWeight: '500' }}
        onPress={() => router.push('/simulator' as never)}
      />
      <Divider style={{ marginVertical: 8 }} />
      <DrawerItem
        label="Settings"
        icon={({ focused, color, size }: IconRenderProps) => (
          <Icon source="cog-outline" size={size} color={iconColor(focused, color)} />
        )}
        labelStyle={{ color: theme.colors.onSurface, fontWeight: '500' }}
        onPress={() => router.push('/(drawer)/settings' as never)}
      />
      {isDemoMode() && (
        <DrawerItem
          label={busy ? 'Resetting…' : 'Reset demo'}
          icon={({ size }: IconRenderProps) => <Icon source="restore" size={size} color={callRed} />}
          labelStyle={{ color: callRed }}
          onPress={() => setResetDialogVisible(true)}
        />
      )}

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
            <Button textColor={callRed} onPress={runReset}>
              Reset
            </Button>
          </Dialog.Actions>
        </Dialog>
      </Portal>
    </DrawerContentScrollView>
  );
}

export default function DrawerLayout() {
  const theme = useTheme();
  return (
    <Drawer
      drawerContent={DrawerContent}
      screenOptions={{
        headerShown: false,
        drawerType: 'front',
        drawerStyle: { backgroundColor: theme.colors.surface },
        drawerActiveTintColor: theme.colors.primary,
        drawerInactiveTintColor: theme.colors.onSurface,
        drawerActiveBackgroundColor: theme.colors.secondaryContainer,
        sceneStyle: { backgroundColor: theme.colors.background },
      }}
    >
      <Drawer.Screen name="(tabs)" options={{ drawerItemStyle: { display: 'none' } }} />
      <Drawer.Screen name="contacts" options={{ title: 'Contacts' }} />
      <Drawer.Screen name="templates" options={{ title: 'Templates' }} />
      <Drawer.Screen name="audit" options={{ title: 'Audit log' }} />
      <Drawer.Screen name="settings" options={{ title: 'Settings' }} />
    </Drawer>
  );
}
