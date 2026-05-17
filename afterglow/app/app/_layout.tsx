import { Ionicons } from '@expo/vector-icons';
import { useFonts } from 'expo-font';
import { Stack, router } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { useEffect, useMemo, useState } from 'react';
import { ActivityIndicator, Platform, StyleSheet, View } from 'react-native';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { PaperProvider } from 'react-native-paper';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { LocaleProvider } from '../lib/LocaleContext';
import { ThemeProvider, useThemePreference } from '../lib/ThemeContext';
import { api, isDemoMode } from '../lib/api';
import { markFreshSession } from '../lib/freshSession';
import { paperDarkTheme, paperLightTheme, type AppTheme } from '../lib/paperTheme';
import { readStoredThemePreference } from '../lib/themeStorage';

// Module-level early color-scheme on web: runs at bundle parse, before the
// first React render. Eliminates the visible flash between the browser
// default white background and the resolved Afterglow theme. It does NOT
// run pre-paint on the initial HTML document (that would need a custom
// index.html template) — just earliest possible from JS.
if (Platform.OS === 'web' && typeof document !== 'undefined') {
  const pref = readStoredThemePreference();
  const sysDark =
    typeof window !== 'undefined' &&
    typeof window.matchMedia === 'function' &&
    window.matchMedia('(prefers-color-scheme: dark)').matches;
  const dark = pref === 'dark' || (pref !== 'light' && sysDark);
  const bg = dark ? paperDarkTheme.colors.background : paperLightTheme.colors.background;
  document.documentElement.style.colorScheme = dark ? 'dark' : 'light';
  document.documentElement.style.backgroundColor = bg;
  if (document.body) document.body.style.backgroundColor = bg;
}

export default function RootLayout() {
  return (
    <ThemeProvider>
      <LocaleProvider>
        <RootLayoutInner />
      </LocaleProvider>
    </ThemeProvider>
  );
}

function RootLayoutInner() {
  const { isDark } = useThemePreference();
  const paperTheme: AppTheme = isDark ? paperDarkTheme : paperLightTheme;
  const [fontsLoaded] = useFonts(Ionicons.font);
  const [gateChecked, setGateChecked] = useState(!isDemoMode());

  const styles = useMemo(
    () =>
      StyleSheet.create({
        splash: {
          flex: 1,
          backgroundColor: paperTheme.colors.background,
          alignItems: 'center',
          justifyContent: 'center',
        },
        splashOverlay: {
          ...StyleSheet.absoluteFillObject,
          backgroundColor: paperTheme.colors.background,
          alignItems: 'center',
          justifyContent: 'center',
        },
      }),
    [paperTheme],
  );

  // Re-sync document chrome whenever the theme flips at runtime (web only).
  useEffect(() => {
    if (Platform.OS !== 'web' || typeof document === 'undefined') return;
    const bg = paperTheme.colors.background;
    document.documentElement.style.colorScheme = isDark ? 'dark' : 'light';
    document.documentElement.style.backgroundColor = bg;
    if (document.body) document.body.style.backgroundColor = bg;
  }, [isDark, paperTheme]);

  useEffect(() => {
    if (!isDemoMode()) return;
    let cancelled = false;
    api
      .getActiveTemplate()
      .then((t) => {
        if (cancelled) return;
        if (t === null) {
          markFreshSession();
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
      <PaperProvider theme={paperTheme}>
        <View style={styles.splash}>
          <ActivityIndicator color={paperTheme.colors.primary} />
        </View>
      </PaperProvider>
    );
  }

  return (
    <PaperProvider theme={paperTheme}>
      <GestureHandlerRootView style={{ flex: 1 }}>
        <SafeAreaProvider>
          <StatusBar style={isDark ? 'light' : 'dark'} />
          <Stack
            screenOptions={{
              headerStyle: { backgroundColor: paperTheme.colors.background },
              headerTintColor: paperTheme.colors.onSurface,
              headerTitleStyle: { fontWeight: '600', fontSize: 17 },
              headerShadowVisible: false,
              contentStyle: { backgroundColor: paperTheme.colors.background },
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
              <ActivityIndicator color={paperTheme.colors.primary} />
            </View>
          )}
        </SafeAreaProvider>
      </GestureHandlerRootView>
    </PaperProvider>
  );
}
