import { Ionicons } from '@expo/vector-icons';
import { useFonts } from 'expo-font';
import { Stack, router } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { useEffect, useState } from 'react';
import { ActivityIndicator, StyleSheet, View } from 'react-native';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { api, isDemoMode } from '../lib/api';
import { colors } from '../lib/theme';

export default function RootLayout() {
  // No demo-session priming needed here: the api layer serializes the first
  // mint internally (see lib/api.ts ensureSession), so whichever screen makes
  // the first fetch transparently triggers the handshake and every parallel
  // fetch waits on the same promise.
  const [fontsLoaded] = useFonts(Ionicons.font);
  // Demo bootstrap gate: fresh visitors and post-reset sessions land on the
  // Templates screen so they pick a preset before touching anything else.
  // Production (`?bypass=…`) skips the gate entirely. The overlay covers the
  // brief flash of the default `(tabs)/index` (Calls) while the redirect
  // resolves; once the gate has run we just render the Stack normally.
  const [gateChecked, setGateChecked] = useState(!isDemoMode());

  useEffect(() => {
    if (!isDemoMode()) return;
    let cancelled = false;
    api
      .getActiveTemplate()
      .then((t) => {
        if (cancelled) return;
        if (t === null) {
          router.replace('/(tabs)/templates');
        }
      })
      .catch(() => {
        /* network blip — let the user land wherever; nothing is broken,
           the Templates tab is still one tap away. */
      })
      .finally(() => {
        if (!cancelled) setGateChecked(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (!fontsLoaded) {
    return (
      <View style={styles.splash}>
        <ActivityIndicator color={colors.brand} />
      </View>
    );
  }

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
        <Stack.Screen name="incoming-call" options={{ headerShown: false }} />
        <Stack.Screen name="call/[id]" options={{ title: 'Call detail' }} />
        <Stack.Screen name="customer/[id]" options={{ title: 'Customer detail' }} />
      </Stack>
      {gateChecked ? null : (
        <View style={styles.splashOverlay} pointerEvents="auto">
          <ActivityIndicator color={colors.brand} />
        </View>
      )}
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  splash: {
    flex: 1,
    backgroundColor: colors.bg,
    alignItems: 'center',
    justifyContent: 'center',
  },
  splashOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: colors.bg,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
