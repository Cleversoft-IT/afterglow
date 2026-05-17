import { Ionicons } from '@expo/vector-icons';
import { useFonts } from 'expo-font';
import { Stack, router } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { useEffect, useMemo, useState } from 'react';
import { ActivityIndicator, StyleSheet, View } from 'react-native';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { PaperProvider } from 'react-native-paper';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { ThemeProvider, useTheme } from '../lib/ThemeContext';
import { api, isDemoMode } from '../lib/api';
import { paperDarkTheme, paperLightTheme } from '../lib/paperTheme';
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
  const paperTheme = isDark ? paperDarkTheme : paperLightTheme;
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
          router.replace('/(drawer)/templates' as never);
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
    <PaperProvider theme={paperTheme}>
      <GestureHandlerRootView style={{ flex: 1 }}>
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
            <Stack.Screen name="(drawer)" options={{ headerShown: false }} />
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
      </GestureHandlerRootView>
    </PaperProvider>
  );
}
