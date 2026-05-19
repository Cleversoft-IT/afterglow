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

  // Active state from the current route — the drawer navigator only knows
  // about its own children (tabs / contacts / templates / audit / simulator /
  // settings). We derive a per-item flag and apply the same focused styling
  // pattern that used to be hardcoded only for Calls, so every drawer item
  // gets the blue-on-secondaryContainer highlight when its screen is open.
  const activeRouteName = props.state.routes[props.state.index]?.name ?? '';
  const isOnCalls = activeRouteName === '(tabs)';
  const isOnTemplates = activeRouteName === 'templates';
  const isOnAudit = activeRouteName === 'audit';
  const isOnIntegrations = activeRouteName === 'integrations';
  const isOnSimulator = activeRouteName === 'simulator';
  const isOnSettings = activeRouteName === 'settings';

  const itemLabelStyle = (focused: boolean) => ({
    color: focused ? theme.colors.primary : theme.colors.onSurface,
    fontWeight: '500' as const,
  });

  return (
    <DrawerContentScrollView {...props} contentContainerStyle={{ paddingTop: 8 }}>
      <DrawerItem
        label="Calls"
        focused={isOnCalls}
        activeTintColor={theme.colors.primary}
        activeBackgroundColor={theme.colors.secondaryContainer}
        icon={({ color, size }: IconRenderProps) => (
          <Icon source="phone-outline" size={size} color={iconColor(isOnCalls, color)} />
        )}
        labelStyle={itemLabelStyle(isOnCalls)}
        onPress={() => router.navigate('/(drawer)/(tabs)' as never)}
      />
      <DrawerItem
        label="Templates"
        focused={isOnTemplates}
        activeTintColor={theme.colors.primary}
        activeBackgroundColor={theme.colors.secondaryContainer}
        icon={({ color, size }: IconRenderProps) => (
          <Icon source="view-grid-outline" size={size} color={iconColor(isOnTemplates, color)} />
        )}
        labelStyle={itemLabelStyle(isOnTemplates)}
        onPress={() => router.push('/(drawer)/templates' as never)}
      />
      <DrawerItem
        label="Audit log"
        focused={isOnAudit}
        activeTintColor={theme.colors.primary}
        activeBackgroundColor={theme.colors.secondaryContainer}
        icon={({ color, size }: IconRenderProps) => (
          <Icon source="text-box-search-outline" size={size} color={iconColor(isOnAudit, color)} />
        )}
        labelStyle={itemLabelStyle(isOnAudit)}
        onPress={() => router.push('/(drawer)/audit' as never)}
      />
      <DrawerItem
        label="Integrations"
        focused={isOnIntegrations}
        activeTintColor={theme.colors.primary}
        activeBackgroundColor={theme.colors.secondaryContainer}
        icon={({ color, size }: IconRenderProps) => (
          <Icon source="puzzle-outline" size={size} color={iconColor(isOnIntegrations, color)} />
        )}
        labelStyle={itemLabelStyle(isOnIntegrations)}
        onPress={() => router.push('/(drawer)/integrations' as never)}
      />
      <Divider style={{ marginVertical: 8 }} />
      <DrawerItem
        label="Test simulator"
        focused={isOnSimulator}
        activeTintColor={theme.colors.primary}
        activeBackgroundColor={theme.colors.secondaryContainer}
        icon={({ color, size }: IconRenderProps) => (
          <Icon source="phone-in-talk-outline" size={size} color={iconColor(isOnSimulator, color)} />
        )}
        labelStyle={itemLabelStyle(isOnSimulator)}
        onPress={() => router.push('/(drawer)/simulator' as never)}
      />
      <Divider style={{ marginVertical: 8 }} />
      <DrawerItem
        label="Settings"
        focused={isOnSettings}
        activeTintColor={theme.colors.primary}
        activeBackgroundColor={theme.colors.secondaryContainer}
        icon={({ color, size }: IconRenderProps) => (
          <Icon source="cog-outline" size={size} color={iconColor(isOnSettings, color)} />
        )}
        labelStyle={itemLabelStyle(isOnSettings)}
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
      <Drawer.Screen name="integrations" options={{ title: 'Integrations' }} />
      {/* Simulator is rendered as a custom DrawerItem above; the Drawer.Screen
          entry registers the route with the navigator so `activeRouteName`
          flips to "simulator" when the user opens it, enabling the active
          highlight. `drawerItemStyle: display: none` keeps the duplicate
          auto-generated item out of the list. */}
      <Drawer.Screen
        name="simulator"
        options={{ title: 'Test simulator', drawerItemStyle: { display: 'none' } }}
      />
      <Drawer.Screen name="settings" options={{ title: 'Settings' }} />
    </Drawer>
  );
}
