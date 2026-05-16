import { Ionicons } from '@expo/vector-icons';
import { useFonts } from 'expo-font';
import { Stack, router } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { useEffect, useMemo, useState } from 'react';
import { ActivityIndicator, StyleSheet, View } from 'react-native';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { ThemeProvider, useTheme } from '../lib/ThemeContext';
import { api, isDemoMode } from '../lib/api';
import { spacing } from '../lib/theme';

export default function RootLayout() {
  return (
    <ThemeProvider>
      <RootLayoutInner />
    </ThemeProvider>
  );
}

function RootLayoutInner() {
  const { colors, isDark } = useTheme();
  const [fontsLoaded] = useFonts(Ionicons.font);
  const [gateChecked, setGateChecked] = useState(!isDemoMode());

  const styles = useMemo(
    () =>
      StyleSheet.create({
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
      }),
    [colors],
  );

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
        /* network blip */
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
      <StatusBar style={isDark ? 'light' : 'dark'} />
      <Stack
        screenOptions={{
          headerStyle: { backgroundColor: colors.bg },
          headerTintColor: colors.text,
          headerTitleStyle: { fontWeight: '600', fontSize: 17 },
          headerShadowVisible: false,
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
