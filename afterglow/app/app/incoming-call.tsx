import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { useEffect, useMemo, useRef, useState } from 'react';
import { ActivityIndicator, Animated, Easing, Pressable, StyleSheet, Text, View } from 'react-native';
import { CallButton } from '../components/CallButton';
import { api, ApiError } from '../lib/api';
import type { AudioDomain } from '../lib/audio';
import { colors, spacing } from '../lib/theme';
import type { TemplateView } from '../lib/types';
import { usePhoneAudio } from '../lib/usePhoneAudio';

type CallerInfo = { name: string; phone: string };

const CALLERS: Record<AudioDomain, CallerInfo> = {
  restaurant: { name: 'Marco Bianchi', phone: '+39 333 111 2233' },
  dentist: { name: 'Giulia Rossi', phone: '+39 333 999 1122' },
  bodyshop: { name: 'Luca Verdi', phone: '+39 333 888 3344' },
};

const PHONE_E164: Record<AudioDomain, string> = {
  restaurant: '+393331112233',
  dentist: '+393339991122',
  bodyshop: '+393338883344',
};

const POLL_INTERVAL_MS = 1500;
const POLL_TIMEOUT_MS = 30000;

type Phase = 'loading' | 'ringing' | 'human' | 'talking' | 'analyzing' | 'error';

export default function IncomingCallScreen() {
  const router = useRouter();
  const audio = usePhoneAudio();
  const [phase, setPhase] = useState<Phase>('loading');
  const [template, setTemplate] = useState<TemplateView | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const [progressLabel, setProgressLabel] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const pulse = useRef(new Animated.Value(1)).current;

  const domain = (template?.domain_hint as AudioDomain) ?? 'restaurant';
  const caller = CALLERS[domain] ?? CALLERS.restaurant;

  // Load template on mount, then transition to ringing.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const t = await api.getActiveTemplate();
        if (cancelled) return;
        setTemplate(t);
        // Prefetch ringtone + recording before showing the dialer, so the
        // click on Afterglow can call .play() synchronously and keep the
        // browser's user-activation token alive.
        await audio.prefetch(t.domain_hint as AudioDomain);
        if (cancelled) return;
        setPhase('ringing');
      } catch (e) {
        if (cancelled) return;
        setError(e instanceof ApiError ? e.message : String(e));
        setPhase('error');
      }
    })();
    return () => {
      cancelled = true;
    };
    // audio is stable across renders (refs only, no state) — omitting from
    // deps prevents the cleanup loop that swallows the first mount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Ringtone + pulse animation while ringing.
  useEffect(() => {
    if (phase !== 'ringing') return;
    audio.playRingtone();
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(pulse, {
          toValue: 1.15,
          duration: 700,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver: true,
        }),
        Animated.timing(pulse, {
          toValue: 1,
          duration: 700,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver: true,
        }),
      ]),
    );
    loop.start();
    return () => {
      loop.stop();
      pulse.setValue(1);
      audio.stopRinging();
    };
  }, [phase, audio, pulse]);

  // mm:ss timer for human and talking phases.
  useEffect(() => {
    if (phase !== 'human' && phase !== 'talking') return;
    setElapsed(0);
    const started = Date.now();
    const id = setInterval(() => setElapsed(Math.floor((Date.now() - started) / 1000)), 250);
    return () => clearInterval(id);
  }, [phase]);

  const hangUp = () => {
    audio.stopAll();
    router.back();
  };

  const acceptHuman = () => {
    audio.stopRinging();
    setPhase('human');
  };

  const runPipeline = async () => {
    setPhase('analyzing');
    setProgressLabel('Uploading call…');
    try {
      const blob = audio.getCallBlob();
      if (!blob) throw new Error('Missing call audio blob.');
      const submitted = await api.submitAudio(blob, PHONE_E164[domain], `${domain}.mp3`);
      const deadline = Date.now() + POLL_TIMEOUT_MS;
      while (Date.now() < deadline) {
        const detail = await api.getCall(submitted.call_id);
        setProgressLabel(`Pipeline ${detail.status}…`);
        if (detail.status === 'completed' || detail.status === 'failed') {
          router.replace(`/call/${detail.id}`);
          return;
        }
        await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS));
      }
      throw new Error('Pipeline timed out after 30s.');
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
      setPhase('error');
    }
  };

  const acceptAi = () => {
    if (!template) return;
    audio.stopRinging();
    setPhase('talking');
    audio.playCallAudio(
      domain,
      () => {
        runPipeline();
      },
      (err) => {
        setError(err.message);
        setPhase('error');
      },
    );
  };

  const subtitle = useMemo(() => {
    switch (phase) {
      case 'loading':
        return 'Connecting…';
      case 'ringing':
        return 'Incoming call';
      case 'human':
        return 'On call with operator';
      case 'talking':
        return 'On call';
      case 'analyzing':
        return 'Call ended';
      case 'error':
        return 'Something went wrong';
    }
  }, [phase]);

  return (
    <View style={styles.root}>
      <View style={styles.topBlock}>
        <Text style={styles.subtitle}>{subtitle}</Text>

        <Animated.View style={[styles.avatar, { transform: [{ scale: phase === 'ringing' ? pulse : 1 }] }]}>
          <Ionicons name="person" size={56} color={colors.text} />
        </Animated.View>

        <Text style={styles.caller}>{caller.name}</Text>
        <Text style={styles.phone}>{caller.phone}</Text>

        {(phase === 'human' || phase === 'talking') && (
          <Text style={styles.timer}>{formatTime(elapsed)}</Text>
        )}

        {phase === 'talking' && (
          <View style={styles.tag}>
            <Ionicons name="sparkles" size={12} color={colors.brand} />
            <Text style={styles.tagText}>Afterglow listening</Text>
          </View>
        )}

        {phase === 'analyzing' && (
          <View style={styles.analyzing}>
            <ActivityIndicator color={colors.brand} />
            <Text style={styles.analyzingText}>{progressLabel ?? 'Analyzing with Afterglow…'}</Text>
          </View>
        )}

        {phase === 'error' && (
          <Text style={styles.errorText}>{error}</Text>
        )}
      </View>

      <View style={styles.bottomBlock}>
        {phase === 'loading' && <ActivityIndicator color={colors.brand} />}

        {phase === 'ringing' && (
          <View style={styles.dialerRow}>
            <CallButton variant="decline" onPress={hangUp} />
            <CallButton variant="ai" onPress={acceptAi} />
            <CallButton variant="accept" onPress={acceptHuman} />
          </View>
        )}

        {(phase === 'human' || phase === 'talking') && (
          <View style={styles.singleRow}>
            <CallButton variant="decline" onPress={hangUp} />
          </View>
        )}

        {phase === 'error' && (
          <Pressable onPress={() => router.back()} style={styles.dismiss}>
            <Text style={styles.dismissText}>Dismiss</Text>
          </Pressable>
        )}
      </View>
    </View>
  );
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60).toString().padStart(2, '0');
  const s = (seconds % 60).toString().padStart(2, '0');
  return `${m}:${s}`;
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: colors.bg,
    paddingHorizontal: spacing.xl,
    paddingTop: spacing.xxl + spacing.xl,
    paddingBottom: spacing.xxl,
    justifyContent: 'space-between',
  },
  topBlock: { alignItems: 'center', gap: spacing.md },
  subtitle: {
    color: colors.textMuted,
    fontSize: 13,
    letterSpacing: 1.2,
    textTransform: 'uppercase',
    marginBottom: spacing.lg,
  },
  avatar: {
    width: 132,
    height: 132,
    borderRadius: 66,
    backgroundColor: colors.surfaceAlt,
    borderWidth: 2,
    borderColor: colors.border,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing.md,
  },
  caller: { color: colors.text, fontSize: 26, fontWeight: '700' },
  phone: { color: colors.textMuted, fontSize: 16, letterSpacing: 0.5 },
  timer: {
    color: colors.textMuted,
    fontSize: 18,
    fontVariant: ['tabular-nums'],
    marginTop: spacing.md,
  },
  tag: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 999,
    backgroundColor: 'rgba(59, 130, 246, 0.15)',
    marginTop: spacing.sm,
  },
  tagText: { color: colors.brand, fontSize: 11, fontWeight: '600', letterSpacing: 0.5 },
  analyzing: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm, marginTop: spacing.lg },
  analyzingText: { color: colors.textMuted, fontSize: 14 },
  errorText: { color: colors.danger, textAlign: 'center', marginTop: spacing.lg },
  bottomBlock: { alignItems: 'center', gap: spacing.lg },
  dialerRow: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    justifyContent: 'space-between',
    width: '100%',
    maxWidth: 360,
    paddingHorizontal: spacing.md,
  },
  singleRow: { alignItems: 'center' },
  dismiss: {
    paddingHorizontal: spacing.xl,
    paddingVertical: spacing.md,
    backgroundColor: colors.surface,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: colors.border,
  },
  dismissText: { color: colors.text, fontWeight: '600' },
});
