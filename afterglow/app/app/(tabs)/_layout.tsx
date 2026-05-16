import { Ionicons } from '@expo/vector-icons';
import { Tabs } from 'expo-router';
import { Platform } from 'react-native';
import { useTheme } from '../../lib/ThemeContext';
import { spacing } from '../../lib/theme';

type IoniconName = React.ComponentProps<typeof Ionicons>['name'];

const tabIcon =
  (name: IoniconName) =>
  ({ color, size }: { color: string; size: number }) =>
    <Ionicons name={name} color={color} size={size} />;

export default function TabsLayout() {
  const { colors } = useTheme();

  return (
    <Tabs
      screenOptions={{
        headerStyle: { backgroundColor: colors.bg },
        headerTintColor: colors.text,
        headerTitleStyle: { fontWeight: '600', fontSize: 17 },
        headerShadowVisible: false,
        tabBarStyle: {
          backgroundColor: colors.surface,
          borderTopColor: colors.border,
          borderTopWidth: 1,
          height: Platform.OS === 'web' ? 60 : undefined,
          paddingTop: spacing.xs,
        },
        tabBarActiveTintColor: colors.brand,
        tabBarInactiveTintColor: colors.textMuted,
        tabBarLabelStyle: {
          fontSize: 11,
          fontWeight: '500',
          marginBottom: Platform.OS === 'ios' ? 0 : spacing.xs,
        },
        sceneStyle: { backgroundColor: colors.bg },
      }}
    >
      <Tabs.Screen
        name="index"
        options={{ title: 'Calls', tabBarLabel: 'Calls', tabBarIcon: tabIcon('call-outline') }}
      />
      <Tabs.Screen
        name="customers"
        options={{ title: 'Customers', tabBarLabel: 'Customers', tabBarIcon: tabIcon('people-outline') }}
      />
      <Tabs.Screen
        name="templates"
        options={{ title: 'Templates', tabBarLabel: 'Templates', tabBarIcon: tabIcon('albums-outline') }}
      />
      <Tabs.Screen
        name="audit"
        options={{ title: 'Audit', tabBarLabel: 'Audit', tabBarIcon: tabIcon('shield-checkmark-outline') }}
      />
      <Tabs.Screen
        name="settings"
        options={{ title: 'Settings', tabBarLabel: 'Settings', tabBarIcon: tabIcon('settings-outline') }}
      />
    </Tabs>
  );
}
