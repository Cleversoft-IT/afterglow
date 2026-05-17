import { DrawerContentScrollView, DrawerItem } from '@react-navigation/drawer';
import type { DrawerContentComponentProps } from '@react-navigation/drawer';
import { router } from 'expo-router';
import { Drawer } from 'expo-router/drawer';
import { Alert, Platform, View } from 'react-native';
import { Divider, Icon, Text, useTheme } from 'react-native-paper';
import { useState } from 'react';
import { api, ApiError, isDemoMode } from '../../lib/api';
import { callRed } from '../../lib/paperTheme';

function DrawerContent(props: DrawerContentComponentProps) {
  const theme = useTheme();
  const [busy, setBusy] = useState(false);

  const handleReset = async () => {
    const confirmed =
      Platform.OS === 'web'
        ? typeof window !== 'undefined' && window.confirm('Reset demo? All session data will be wiped.')
        : await new Promise<boolean>((resolve) => {
            Alert.alert('Reset demo?', 'All session data will be wiped.', [
              { text: 'Cancel', style: 'cancel', onPress: () => resolve(false) },
              { text: 'Reset', style: 'destructive', onPress: () => resolve(true) },
            ]);
          });
    if (!confirmed) return;
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

  return (
    <DrawerContentScrollView {...props} contentContainerStyle={{ paddingTop: 0 }}>
      <View style={{ padding: 24, paddingTop: 32, gap: 4 }}>
        <Text variant="headlineSmall" style={{ color: theme.colors.onSurface }}>
          Afterglow
        </Text>
        <Text variant="bodyMedium" style={{ color: theme.colors.onSurfaceVariant }}>
          AI dialer
        </Text>
      </View>
      <Divider />
      <DrawerItem
        label="Contacts"
        icon={({ color, size }) => <Icon source="account-multiple-outline" size={size} color={color} />}
        onPress={() => router.push('/(drawer)/contacts' as never)}
      />
      <DrawerItem
        label="Templates"
        icon={({ color, size }) => <Icon source="view-grid-outline" size={size} color={color} />}
        onPress={() => router.push('/(drawer)/templates' as never)}
      />
      <DrawerItem
        label="Audit log"
        icon={({ color, size }) => <Icon source="text-box-search-outline" size={size} color={color} />}
        onPress={() => router.push('/(drawer)/audit' as never)}
      />
      <DrawerItem
        label="Test simulator"
        icon={({ color, size }) => <Icon source="phone-in-talk-outline" size={size} color={color} />}
        onPress={() => router.push('/simulator' as never)}
      />
      <Divider style={{ marginVertical: 8 }} />
      <DrawerItem
        label="Settings"
        icon={({ color, size }) => <Icon source="cog-outline" size={size} color={color} />}
        onPress={() => router.push('/(drawer)/settings' as never)}
      />
      {isDemoMode() && (
        <DrawerItem
          label={busy ? 'Resetting…' : 'Reset demo'}
          icon={({ size }) => <Icon source="restore" size={size} color={callRed} />}
          labelStyle={{ color: callRed }}
          onPress={handleReset}
        />
      )}
    </DrawerContentScrollView>
  );
}

export default function DrawerLayout() {
  return (
    <Drawer
      drawerContent={DrawerContent}
      screenOptions={{ headerShown: false, drawerType: 'front' }}
    >
      <Drawer.Screen name="(tabs)" options={{ drawerItemStyle: { display: 'none' } }} />
      <Drawer.Screen name="contacts" options={{ title: 'Contacts' }} />
      <Drawer.Screen name="templates" options={{ title: 'Templates' }} />
      <Drawer.Screen name="audit" options={{ title: 'Audit log' }} />
      <Drawer.Screen name="settings" options={{ title: 'Settings' }} />
    </Drawer>
  );
}
