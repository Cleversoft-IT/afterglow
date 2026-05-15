import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { colors } from '../lib/theme';

export default function RootLayout() {
  // No demo-session priming needed here: the api layer serializes the first
  // mint internally (see lib/api.ts ensureSession), so whichever screen makes
  // the first fetch transparently triggers the handshake and every parallel
  // fetch waits on the same promise.
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
