import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { useEffect } from 'react';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { api } from '../lib/api';
import { colors } from '../lib/theme';

export default function RootLayout() {
  // Prime the demo sandbox session. The first /templates GET round-trips the
  // freshly-minted `X-Demo-Session` uuid which the api layer persists to
  // localStorage. All subsequent fetches are already isolated.
  useEffect(() => {
    api.listTemplates().catch(() => {
      /* best-effort: errors will surface on the real screens */
    });
  }, []);

  return (
    <SafeAreaProvider>
      <StatusBar style="light" />
      <Stack
        screenOptions={{
          headerStyle: { backgroundColor: colors.bg },
          headerTintColor: colors.text,
          headerTitleStyle: { fontWeight: '700' },
          contentStyle: { backgroundColor: colors.bg },
        }}
      >
        <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
        <Stack.Screen name="simulator" options={{ title: 'Incoming call' }} />
        <Stack.Screen name="call/[id]" options={{ title: 'Call detail' }} />
      </Stack>
    </SafeAreaProvider>
  );
}
