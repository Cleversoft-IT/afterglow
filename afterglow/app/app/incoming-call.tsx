import { Ionicons } from '@expo/vector-icons';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useEffect, useMemo, useRef, useState } from 'react';
import { ActivityIndicator, Animated, Easing, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { CallButton } from '../components/CallButton';
import { api, ApiError } from '../lib/api';
import type { AudioDomain } from '../lib/audio';
import { setPipelineToast } from '../lib/pipelineToast';
import { colors, radius, spacing } from '../lib/theme';
import type { CallListItem, CustomerCard, TemplateView } from '../lib/types';
import { usePhoneAudio } from '../lib/usePhoneAudio';

type CallerInfo = { name: string; phone: string };
type CallerMode = 'existing' | 'new';

// Existing-customer numbers map to seeded customer rows (see backend seed.py).
// Names + voices align with the Speechmatics TTS demo MP3s under
// app/assets/audio/, so the recording matches the caller card.
const CALLERS: Record<AudioDomain, CallerInfo> = {
  restaurant: { name: 'Mark Ross', phone: '+1 (555) 111-2233' },
  dentist: { name: 'Laura Bennett', phone: '+1 (555) 999-1122' },
  bodyshop: { name: 'Andrew Green', phone: '+1 (555) 888-3344' },
};

const PHONE_E164: Record<AudioDomain, string> = {
  restaurant: '+15551112233',
  dentist: '+15559991122',
  bodyshop: '+15558883344',
};

function formatE164ToDisplay(e164: string): string {
  // Crude US-style pretty print: +15551234567 -> +1 (555) 123-4567.
  const digits = e164.replace(/^\+/, '');
  if (digits.length === 11 && digits.startsWith('1')) {
    return `+1 (${digits.slice(1, 4)}) ${digits.slice(4, 7)}-${digits.slice(7)}`;
  }
  return e164;
}

function generateNewCallerPhone(): { e164: string; pretty: string } {
  // Pick a random 7-digit number in the +1 555 0XX XXXX range so it never
  // collides with the seed numbers above and stays in the reserved test
  // block. Fresh on every press: every new-caller trigger creates a new
  // Customer row in the backend.
  const middle = String(Math.floor(Math.random() * 100)).padStart(2, '0');
  const tail = String(Math.floor(Math.random() * 10_000)).padStart(4, '0');
  const e164 = `+15550${middle}${tail}`;
  return { e164, pretty: formatE164ToDisplay(e164) };
}

type Phase = 'loading' | 'ringing' | 'human' | 'talking' | 'error';

export default function IncomingCallScreen() {
  const router = useRouter();
  const audio = usePhoneAudio();
  const params = useLocalSearchParams<{ caller?: string }>();
  const callerMode: CallerMode = params.caller === 'new' ? 'new' : 'existing';

  const [phase, setPhase] = useState<Phase>('loading');
  const [template, setTemplate] = useState<TemplateView | null>(null);
  const [customer, setCustomer] = useState<CustomerCard | null>(null);
  const [recentCalls, setRecentCalls] = useState<CallListItem[]>([]);
  const [elapsed, setElapsed] = useState(0);
  const [error, setError] = useState<string | null>(null);

  // The fresh-customer phone is pinned for the lifetime of THIS dialer
  // session so the ringing screen, the submit and the caller card all
  // agree on it. A new "Call from new customer" press from the simulator
  // generates a different one because this component unmounts and remounts.
  const newCallerPhone = useRef(callerMode === 'new' ? generateNewCallerPhone() : null);

  const pulse = useRef(new Animated.Value(1)).current;

  const domain = (template?.domain_hint as AudioDomain) ?? 'restaurant';
  const fallbackCaller = CALLERS[domain] ?? CALLERS.restaurant;
  const sim = template?.simulation_config;
  // New seeded templates expose `scenarios.{existing,new}`. Wizard-built
  // templates may still ship the legacy flat shape — read with a fallback
  // ladder so a custom template that hasn't been regenerated keeps working.
  const scenario = sim?.scenarios?.[callerMode] ?? null;
  const audioSource = scenario?.audio_source ?? sim?.audio_source ?? null;
  const useBundledAudio =
    (!sim || audioSource === 'bundled' || audioSource == null) &&
    (domain === 'restaurant' || domain === 'dentist' || domain === 'bodyshop');
  const audioKey = useBundledAudio
    ? `${domain}_${callerMode}`
    : `${template?.id ?? domain}_${callerMode}`;
  const scenarioPhone = scenario?.caller_phone_e164 ?? sim?.caller_phone_e164 ?? null;
  const scenarioName = scenario?.caller_name ?? sim?.caller_name ?? null;
  const phoneE164 =
    callerMode === 'new' && newCallerPhone.current
      ? newCallerPhone.current.e164
      : scenarioPhone ?? PHONE_E164[domain];
  const fallbackDisplayName =
    callerMode === 'new'
      ? 'Unknown caller'
      : scenarioName ?? fallbackCaller.name;
  const fallbackDisplayPhone =
    callerMode === 'new' && newCallerPhone.current
      ? newCallerPhone.current.pretty
      : scenarioPhone
        ? formatE164ToDisplay(scenarioPhone)
        : fallbackCaller.phone;
  const displayName = customer?.display_name ?? fallbackDisplayName;

  // Load template + customer in parallel on mount, then transition to ringing.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const t = await api.getActiveTemplate();
        if (cancelled) return;
        if (!t) {
          throw new Error('Pick a template first from the Templates tab.');
        }
        setTemplate(t);

        const sim = t.simulation_config;
        const scenarioForMode = sim?.scenarios?.[callerMode] ?? null;
        const sourceForMode = scenarioForMode?.audio_source ?? sim?.audio_source ?? null;
        const statusForMode = scenarioForMode?.audio_status ?? sim?.audio_status ?? null;
        const useBundled =
          (!sim || sourceForMode === 'bundled' || sourceForMode == null) &&
          (t.domain_hint === 'restaurant' ||
            t.domain_hint === 'dentist' ||
            t.domain_hint === 'bodyshop');

        const targetPhone =
          callerMode === 'new' && newCallerPhone.current
            ? newCallerPhone.current.e164
            : scenarioForMode?.caller_phone_e164 ??
              sim?.caller_phone_e164 ??
              PHONE_E164[t.domain_hint as AudioDomain] ??
              PHONE_E164.restaurant;

        // For "new caller" mode we deliberately skip the customer lookup —
        // the whole point of that path is to demonstrate the create-on-call
        // flow, and a stray match against a recycled seed phone would
        // poison the demo.
        const customerPromise =
          callerMode === 'new'
            ? Promise.resolve(null)
            : api
                .getCustomerByPhone(targetPhone)
                .then((c) => (cancelled ? null : c))
                .catch(() => null);

        if (useBundled) {
          await audio.prefetch(t.domain_hint as AudioDomain, callerMode);
        } else if (statusForMode === 'ready') {
          const customKey = `${t.id}_${callerMode}`;
          await audio.prefetchUrl(customKey, api.simulationAudioUrl(t.id, callerMode));
        } else {
          throw new Error(
            'This template has no demo audio yet. Generate or upload one in the Simulator screen.',
          );
        }
        const c = await customerPromise;
        if (cancelled) return;
        setCustomer(c);

        if (c) {
          api
            .listCalls({ customer_id: c.id, limit: 5 })
            .then((calls) => {
              if (!cancelled) setRecentCalls(calls);
            })
            .catch(() => {
              if (!cancelled) setRecentCalls([]);
            });
        }

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
  }, [callerMode]);

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

  const submitAndClose = async () => {
    try {
      const blob = audio.getCallBlob();
      if (!blob) throw new Error('Missing call audio blob.');
      const submitted = await api.submitAudio(
        blob,
        phoneE164,
        `${domain}_${callerMode}.mp3`,
      );
      // Park the banner so the Calls tab shows "Analysis in progress" on mount.
      setPipelineToast({
        callId: submitted.call_id,
        phoneE164,
        startedAt: Date.now(),
      });
      audio.stopAll();
      // Replace, not back: prevents the user from "going back" into a dialer
      // that has already shipped the audio.
      router.replace('/(tabs)' as never);
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
      audioKey,
      () => {
        // Natural hang-up beat: HTML5 'ended' fires a hair early on some MP3s
        // (Chrome rounds `currentTime` against an imprecise duration tag),
        // and even when it doesn't, a real call always has a short pause
        // between "goodbye" and "click". Holding for ~800ms lets the last
        // word breathe before the dialer chiude.
        setTimeout(() => {
          void submitAndClose();
        }, 800);
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
      case 'error':
        return 'Something went wrong';
    }
  }, [phase]);

  return (
    <View style={styles.root}>
      <ScrollView
        style={styles.scroll}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        <Text style={styles.subtitle}>{subtitle}</Text>

        <Animated.View style={[styles.avatar, { transform: [{ scale: phase === 'ringing' ? pulse : 1 }] }]}>
          <Ionicons name="person" size={56} color={colors.text} />
        </Animated.View>

        <Text style={styles.caller}>{displayName}</Text>
        <Text style={styles.phone}>{fallbackDisplayPhone}</Text>

        {phase === 'ringing' && (
          <CallerContext customer={customer} recentCalls={recentCalls} callerMode={callerMode} />
        )}

        {(phase === 'human' || phase === 'talking') && (
          <Text style={styles.timer}>{formatTime(elapsed)}</Text>
        )}

        {phase === 'talking' && (
          <View style={styles.tag}>
            <Ionicons name="sparkles" size={12} color={colors.brand} />
            <Text style={styles.tagText}>Afterglow listening</Text>
          </View>
        )}

        {phase === 'error' && (
          <Text style={styles.errorText}>{error}</Text>
        )}
      </ScrollView>

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

type CallerContextProps = {
  customer: CustomerCard | null;
  recentCalls: CallListItem[];
  callerMode: CallerMode;
};

function CallerContext({ customer, recentCalls, callerMode }: CallerContextProps) {
  if (!customer) {
    return (
      <View style={styles.newCallerBadge}>
        <Ionicons name="sparkles-outline" size={12} color={colors.brand} />
        <Text style={styles.newCallerText}>
          {callerMode === 'new' ? 'New customer · will be created on submit' : 'New caller'}
        </Text>
      </View>
    );
  }

  const lang = customer.preferred_language?.toUpperCase();
  const lastCall = customer.last_call_at ? relativeTime(customer.last_call_at) : null;
  const tags = (customer.tags ?? []).slice(0, 3);

  return (
    <View style={styles.contextBlock}>
      <View style={styles.metaRow}>
        <View style={styles.metaPill}>
          <Ionicons name="call-outline" size={12} color={colors.textMuted} />
          <Text style={styles.metaText}>
            {customer.total_calls} {customer.total_calls === 1 ? 'call' : 'calls'}
          </Text>
        </View>
        {lang && (
          <View style={styles.metaPill}>
            <Ionicons name="language-outline" size={12} color={colors.textMuted} />
            <Text style={styles.metaText}>{lang}</Text>
          </View>
        )}
        {lastCall && (
          <View style={styles.metaPill}>
            <Ionicons name="time-outline" size={12} color={colors.textMuted} />
            <Text style={styles.metaText}>last {lastCall}</Text>
          </View>
        )}
      </View>

      {tags.length > 0 && (
        <View style={styles.tagRow}>
          {tags.map((t) => (
            <View key={t} style={styles.chip}>
              <Text style={styles.chipText}>{t}</Text>
            </View>
          ))}
        </View>
      )}

      {customer.memory_summary && (
        <View style={styles.briefingCard}>
          <View style={styles.briefingHeader}>
            <Ionicons name="sparkles" size={14} color={colors.brand} />
            <Text style={styles.briefingTitle}>Next-call briefing</Text>
          </View>
          <Text style={styles.briefingText}>{customer.memory_summary}</Text>
        </View>
      )}

      {recentCalls.length > 0 && (
        <View style={styles.timelineBlock}>
          <Text style={styles.timelineTitle}>Recent calls</Text>
          {recentCalls.slice(0, 2).map((c) => (
            <View key={c.id} style={styles.timelineRow}>
              <View style={styles.timelineDot} />
              <Text style={styles.timelineText}>
                {relativeTime(c.created_at)} · {c.status}
              </Text>
            </View>
          ))}
        </View>
      )}
    </View>
  );
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60).toString().padStart(2, '0');
  const s = (seconds % 60).toString().padStart(2, '0');
  return `${m}:${s}`;
}

function relativeTime(iso: string): string {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return iso;
  const diff = Date.now() - then;
  const sec = Math.round(diff / 1000);
  if (sec < 60) return `${sec}s ago`;
  const min = Math.round(sec / 60);
  if (min < 60) return `${min}m ago`;
  const hr = Math.round(min / 60);
  if (hr < 24) return `${hr}h ago`;
  const days = Math.round(hr / 24);
  if (days < 30) return `${days}d ago`;
  const months = Math.round(days / 30);
  if (months < 12) return `${months}mo ago`;
  const years = Math.round(months / 12);
  return `${years}y ago`;
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: colors.bg,
    paddingHorizontal: spacing.xl,
    paddingTop: spacing.xxl + spacing.xl,
    paddingBottom: spacing.xxl,
  },
  scroll: { flex: 1 },
  scrollContent: { alignItems: 'center', gap: spacing.md, paddingBottom: spacing.xl },
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
    borderRadius: radius.pill,
    backgroundColor: 'rgba(59, 130, 246, 0.15)',
    marginTop: spacing.sm,
  },
  tagText: { color: colors.brand, fontSize: 11, fontWeight: '600', letterSpacing: 0.5 },
  errorText: { color: colors.danger, textAlign: 'center', marginTop: spacing.lg },
  bottomBlock: { alignItems: 'center', gap: spacing.lg, paddingTop: spacing.lg },
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
    borderRadius: radius.pill,
    borderWidth: 1,
    borderColor: colors.border,
  },
  dismissText: { color: colors.text, fontWeight: '600' },
  // Caller-context block (shown while ringing).
  contextBlock: {
    width: '100%',
    maxWidth: 360,
    gap: spacing.sm,
    marginTop: spacing.md,
  },
  metaRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'center',
    gap: spacing.sm,
  },
  metaPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: radius.pill,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
  },
  metaText: { color: colors.textMuted, fontSize: 12, fontWeight: '500' },
  tagRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'center',
    gap: 6,
  },
  chip: {
    paddingHorizontal: 10,
    paddingVertical: 3,
    borderRadius: radius.pill,
    backgroundColor: 'rgba(59, 130, 246, 0.12)',
    borderWidth: 1,
    borderColor: 'rgba(59, 130, 246, 0.3)',
  },
  chipText: { color: colors.brand, fontSize: 11, fontWeight: '600' },
  briefingCard: {
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.md,
    gap: spacing.xs,
  },
  briefingHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  briefingTitle: {
    color: colors.brand,
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 0.8,
    textTransform: 'uppercase',
  },
  briefingText: { color: colors.text, fontSize: 13, lineHeight: 18 },
  timelineBlock: { gap: 4, paddingTop: spacing.xs },
  timelineTitle: {
    color: colors.textSubtle,
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 0.8,
    textTransform: 'uppercase',
  },
  timelineRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  timelineDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: colors.brand,
  },
  timelineText: { color: colors.textMuted, fontSize: 12 },
  newCallerBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: radius.pill,
    backgroundColor: colors.surfaceAlt,
    borderWidth: 1,
    borderColor: colors.border,
    marginTop: spacing.sm,
  },
  newCallerText: { color: colors.brand, fontSize: 11, fontWeight: '600', letterSpacing: 0.5 },
});
