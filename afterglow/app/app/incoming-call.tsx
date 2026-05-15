import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { useEffect, useMemo, useRef, useState } from 'react';
import { ActivityIndicator, Animated, Easing, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { CallButton } from '../components/CallButton';
import { api, ApiError } from '../lib/api';
import type { AudioDomain } from '../lib/audio';
import { colors, radius, spacing } from '../lib/theme';
import type { CallListItem, CustomerCard, TemplateView } from '../lib/types';
import { usePhoneAudio } from '../lib/usePhoneAudio';

type CallerInfo = { name: string; phone: string };

// Fallback display when the phone number is unknown to the backend (new caller).
// When the customer row exists, its display_name wins.
const CALLERS: Record<AudioDomain, CallerInfo> = {
  restaurant: { name: 'Marco Rossi', phone: '+39 333 111 2233' },
  dentist: { name: 'Giulia Rossi', phone: '+39 333 999 1122' },
  bodyshop: { name: 'Luca Verdi', phone: '+39 333 888 3344' },
};

const PHONE_E164: Record<AudioDomain, string> = {
  restaurant: '+393331112233',
  dentist: '+393339991122',
  bodyshop: '+393338883344',
};

const POLL_INTERVAL_MS = 1500;
const POLL_TIMEOUT_MS = 120_000;
const POLL_SLOW_MS = 30_000;

type Phase = 'loading' | 'ringing' | 'human' | 'talking' | 'analyzing' | 'error';

export default function IncomingCallScreen() {
  const router = useRouter();
  const audio = usePhoneAudio();
  const [phase, setPhase] = useState<Phase>('loading');
  const [template, setTemplate] = useState<TemplateView | null>(null);
  const [customer, setCustomer] = useState<CustomerCard | null>(null);
  const [recentCalls, setRecentCalls] = useState<CallListItem[]>([]);
  const [elapsed, setElapsed] = useState(0);
  const [progressLabel, setProgressLabel] = useState<string | null>(null);
  const [analyzingElapsed, setAnalyzingElapsed] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const pulse = useRef(new Animated.Value(1)).current;

  const domain = (template?.domain_hint as AudioDomain) ?? 'restaurant';
  const fallbackCaller = CALLERS[domain] ?? CALLERS.restaurant;
  const phoneE164 = PHONE_E164[domain];
  const displayName = customer?.display_name ?? fallbackCaller.name;

  // Load template + customer in parallel on mount, then transition to ringing.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const t = await api.getActiveTemplate();
        if (cancelled) return;
        setTemplate(t);

        // Customer lookup runs in parallel with audio prefetch. /by-phone
        // returns null (not 404) for unknown numbers — both are valid states.
        const phone = PHONE_E164[t.domain_hint as AudioDomain] ?? PHONE_E164.restaurant;
        const customerPromise = api
          .getCustomerByPhone(phone)
          .then((c) => (cancelled ? null : c))
          .catch(() => null);

        await audio.prefetch(t.domain_hint as AudioDomain);
        const c = await customerPromise;
        if (cancelled) return;
        setCustomer(c);

        // Only fetch history if the customer exists. Demo seeds have
        // total_calls > 0 but no Call rows (session-scoped filter); empty
        // list is the expected state — handle it gracefully in the UI.
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

  // Elapsed counter for analyzing phase — drives the "still working…" message.
  useEffect(() => {
    if (phase !== 'analyzing') return;
    setAnalyzingElapsed(0);
    const started = Date.now();
    const id = setInterval(() => setAnalyzingElapsed(Date.now() - started), 500);
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
      const submitted = await api.submitAudio(blob, phoneE164, `${domain}.mp3`);
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
      throw new Error('Pipeline timed out after 2 minutes.');
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
        <Text style={styles.phone}>{fallbackCaller.phone}</Text>

        {phase === 'ringing' && <CallerContext customer={customer} recentCalls={recentCalls} />}

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
            {analyzingElapsed > POLL_SLOW_MS && (
              <Text style={styles.analyzingSlow}>Still working… (this can take up to 2 minutes)</Text>
            )}
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
};

function CallerContext({ customer, recentCalls }: CallerContextProps) {
  if (!customer) {
    return (
      <View style={styles.newCallerBadge}>
        <Ionicons name="sparkles-outline" size={12} color={colors.brand} />
        <Text style={styles.newCallerText}>New caller</Text>
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
            <Text style={styles.briefingTitle}>Briefing</Text>
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
  analyzing: { flexDirection: 'column', alignItems: 'center', gap: spacing.sm, marginTop: spacing.lg },
  analyzingText: { color: colors.textMuted, fontSize: 14 },
  analyzingSlow: { color: colors.textSubtle, fontSize: 12, textAlign: 'center', paddingHorizontal: spacing.lg },
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
