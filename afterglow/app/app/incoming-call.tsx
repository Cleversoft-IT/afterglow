import { useLocalSearchParams, useRouter } from 'expo-router';
import { useEffect, useMemo, useRef, useState } from 'react';
import { Animated, Easing, StyleSheet, View } from 'react-native';
import {
  ActivityIndicator,
  Avatar,
  Banner,
  Button,
  Card,
  Chip,
  FAB,
  IconButton,
  Surface,
  Text,
  useTheme,
} from 'react-native-paper';
import { api, ApiError } from '../lib/api';
import { initialsFromName } from '../lib/avatar';
import type { AudioDomain } from '../lib/audio';
import { callGreen, callRed } from '../lib/paperTheme';
import { setPipelineToast } from '../lib/pipelineToast';
import type { CallListItem, CustomerCard, TemplateView } from '../lib/types';
import { usePhoneAudio } from '../lib/usePhoneAudio';

type CallerInfo = { name: string; phone: string };
type CallerMode = 'existing' | 'new';

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
  const digits = e164.replace(/^\+/, '');
  if (digits.length === 11 && digits.startsWith('1')) {
    return `+1 (${digits.slice(1, 4)}) ${digits.slice(4, 7)}-${digits.slice(7)}`;
  }
  return e164;
}

function generateNewCallerPhone(): { e164: string; pretty: string } {
  const middle = String(Math.floor(Math.random() * 100)).padStart(2, '0');
  const tail = String(Math.floor(Math.random() * 10_000)).padStart(4, '0');
  const e164 = `+15550${middle}${tail}`;
  return { e164, pretty: formatE164ToDisplay(e164) };
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

type Phase = 'loading' | 'ringing' | 'human' | 'talking' | 'error';

export default function IncomingCallScreen() {
  const theme = useTheme();
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

  const newCallerPhone = useRef(callerMode === 'new' ? generateNewCallerPhone() : null);
  const pulse = useRef(new Animated.Value(1)).current;

  const domain = (template?.domain_hint as AudioDomain) ?? 'restaurant';
  const fallbackCaller = CALLERS[domain] ?? CALLERS.restaurant;
  const sim = template?.simulation_config;
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [callerMode]);

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

  useEffect(() => {
    if (phase !== 'human' && phase !== 'talking') return;
    setElapsed(0);
    const started = Date.now();
    const id = setInterval(() => setElapsed(Math.floor((Date.now() - started) / 1000)), 250);
    return () => clearInterval(id);
  }, [phase]);

  const hangUp = () => {
    audio.stopAll();
    // router.back() leaves a black screen when there's no back-history (e.g.
    // direct deep link to /incoming-call). Always land somewhere safe.
    if (router.canGoBack()) {
      router.back();
    } else {
      router.replace('/(drawer)/(tabs)' as never);
    }
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
      setPipelineToast({
        callId: submitted.call_id,
        phoneE164,
        startedAt: Date.now(),
      });
      audio.stopAll();
      router.replace('/(drawer)/(tabs)' as never);
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

  const initials = initialsFromName(displayName);

  if (phase === 'loading') {
    return (
      <View style={[styles.root, { backgroundColor: theme.colors.background }]}>
        <View style={styles.center}>
          <ActivityIndicator size="large" />
          <Text variant="bodyMedium" style={{ color: theme.colors.onSurfaceVariant, marginTop: 12 }}>
            {subtitle}
          </Text>
        </View>
      </View>
    );
  }

  if (phase === 'error') {
    return (
      <View style={[styles.root, { backgroundColor: theme.colors.background }]}>
        <Banner visible icon="alert-circle-outline">
          {error ?? 'Something went wrong.'}
        </Banner>
        <View style={styles.center}>
          <Button mode="outlined" icon="close" onPress={() => router.back()}>
            Dismiss
          </Button>
        </View>
      </View>
    );
  }

  return (
    <View style={[styles.root, { backgroundColor: theme.colors.background }]}>
      {/* Header zone */}
      <View style={styles.header}>
        <Text variant="bodySmall" style={{ color: theme.colors.onSurfaceVariant, letterSpacing: 0.4 }}>
          {subtitle}
        </Text>
        {(phase === 'human' || phase === 'talking') && (
          <Text
            variant="titleLarge"
            style={{ fontVariant: ['tabular-nums'], fontWeight: '700', marginTop: 4 }}
          >
            {formatTime(elapsed)}
          </Text>
        )}
        <Text variant="headlineLarge" style={[styles.callerName, { color: theme.colors.onSurface }]}>
          {displayName}
        </Text>
        <Text
          variant="titleMedium"
          style={{ color: theme.colors.onSurfaceVariant, marginTop: 4 }}
        >
          {fallbackDisplayPhone}
        </Text>
        {phase === 'talking' && (
          <Chip
            mode="flat"
            icon="creation"
            style={{ marginTop: 12, alignSelf: 'center' }}
          >
            Afterglow listening
          </Chip>
        )}
      </View>

      {/* Avatar zone */}
      <View style={styles.avatarZone}>
        <Animated.View style={{ transform: [{ scale: phase === 'ringing' ? pulse : 1 }] }}>
          <Avatar.Text
            size={phase === 'ringing' ? 128 : 160}
            label={initials || '?'}
            color="#FFFFFF"
            style={{ backgroundColor: callGreen }}
          />
        </Animated.View>
        {phase === 'ringing' ? (
          <CallerContext customer={customer} recentCalls={recentCalls} callerMode={callerMode} />
        ) : null}
      </View>

      {/* Footer / actions */}
      <Surface
        mode="flat"
        style={[
          styles.footer,
          { backgroundColor: theme.colors.elevation.level1, borderTopColor: theme.colors.outlineVariant },
        ]}
      >
        {(phase === 'human' || phase === 'talking') && (
          <View style={styles.controlsRow}>
            <ControlBtn icon="dialpad" label="Keypad" />
            <ControlBtn icon="microphone-off" label="Mute" />
            <ControlBtn icon="volume-high" label="Speaker" />
            <ControlBtn icon="dots-horizontal" label="More" />
          </View>
        )}

        {phase === 'ringing' ? (
          <View style={styles.fabRow}>
            <View style={styles.fabCol}>
              <FAB
                icon="phone-hangup"
                color="#FFFFFF"
                style={[styles.actionFab, { backgroundColor: callRed }]}
                onPress={hangUp}
              />
              <Text variant="labelSmall" style={styles.fabLabel}>
                Decline
              </Text>
            </View>
            <View style={styles.fabCol}>
              <FAB
                icon="creation"
                color="#FFFFFF"
                style={[styles.actionFab, { backgroundColor: theme.colors.primary }]}
                onPress={acceptAi}
              />
              <Text variant="labelSmall" style={styles.fabLabel}>
                AI
              </Text>
            </View>
            <View style={styles.fabCol}>
              <FAB
                icon="phone"
                color="#FFFFFF"
                style={[styles.actionFab, { backgroundColor: callGreen }]}
                onPress={acceptHuman}
              />
              <Text variant="labelSmall" style={styles.fabLabel}>
                Accept
              </Text>
            </View>
          </View>
        ) : (
          <View style={styles.hangupCenter}>
            <FAB
              icon="phone-hangup"
              color="#FFFFFF"
              style={[styles.hangupPill, { backgroundColor: callRed }]}
              onPress={hangUp}
            />
          </View>
        )}
      </Surface>
    </View>
  );
}

function ControlBtn({ icon, label }: { icon: string; label: string }) {
  return (
    <View style={{ alignItems: 'center', gap: 4 }}>
      <IconButton mode="contained-tonal" icon={icon} size={24} />
      <Text variant="labelSmall">{label}</Text>
    </View>
  );
}

function CallerContext({
  customer,
  recentCalls,
  callerMode,
}: {
  customer: CustomerCard | null;
  recentCalls: CallListItem[];
  callerMode: CallerMode;
}) {
  const theme = useTheme();
  if (!customer) {
    return (
      <Chip mode="outlined" icon="account-plus-outline" style={{ marginTop: 16 }}>
        {callerMode === 'new' ? 'New customer · will be created on submit' : 'New caller'}
      </Chip>
    );
  }

  const tags = (customer.tags ?? []).slice(0, 3);
  const lastCall = customer.last_call_at ? relativeTime(customer.last_call_at) : null;

  return (
    <View style={styles.contextBlock}>
      <View style={styles.metaRow}>
        <Chip compact mode="outlined" icon="phone">
          {`${customer.total_calls} ${customer.total_calls === 1 ? 'call' : 'calls'}`}
        </Chip>
        {customer.preferred_language ? (
          <Chip compact mode="outlined" icon="translate">
            {customer.preferred_language.toUpperCase()}
          </Chip>
        ) : null}
        {lastCall ? (
          <Chip compact mode="outlined" icon="clock-outline">
            {`last ${lastCall}`}
          </Chip>
        ) : null}
      </View>

      {tags.length > 0 ? (
        <View style={styles.tagRow}>
          {tags.map((t) => (
            <Chip key={t} compact mode="flat">
              {t}
            </Chip>
          ))}
        </View>
      ) : null}

      {customer.memory_summary ? (
        <Card mode="elevated" style={{ backgroundColor: theme.colors.elevation.level2 }}>
          <Card.Title
            title="Next-call briefing"
            titleVariant="labelLarge"
            left={(p) => <Avatar.Icon {...p} icon="lightbulb-on-outline" size={32} />}
          />
          <Card.Content>
            <Text variant="bodyMedium" numberOfLines={3} style={{ lineHeight: 20 }}>
              {customer.memory_summary}
            </Text>
          </Card.Content>
        </Card>
      ) : null}

      {recentCalls.length > 0 ? (
        <View style={{ gap: 4 }}>
          <Text variant="labelSmall" style={{ color: theme.colors.onSurfaceVariant }}>
            RECENT CALLS
          </Text>
          {recentCalls.slice(0, 2).map((c) => (
            <Text key={c.id} variant="bodySmall" style={{ color: theme.colors.onSurfaceVariant }}>
              · {relativeTime(c.created_at)} · {c.status}
            </Text>
          ))}
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1 },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 12 },
  header: {
    paddingTop: 56,
    paddingHorizontal: 24,
    paddingBottom: 24,
    alignItems: 'center',
  },
  callerName: {
    fontSize: 32,
    fontWeight: '600',
    marginTop: 8,
    textAlign: 'center',
  },
  avatarZone: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 24,
    gap: 24,
  },
  footer: {
    paddingTop: 24,
    paddingBottom: 32,
    paddingHorizontal: 24,
    borderTopWidth: StyleSheet.hairlineWidth,
    gap: 24,
  },
  controlsRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    alignItems: 'flex-start',
  },
  fabRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    alignItems: 'flex-start',
  },
  fabCol: { alignItems: 'center', gap: 6 },
  actionFab: { width: 72, height: 72, borderRadius: 20 },
  fabLabel: { fontWeight: '500' },
  hangupCenter: { alignItems: 'center' },
  hangupPill: {
    width: '60%',
    minWidth: 200,
    height: 64,
    borderRadius: 999,
  },
  contextBlock: {
    width: '100%',
    maxWidth: 360,
    gap: 12,
  },
  metaRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'center',
    gap: 6,
  },
  tagRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'center',
    gap: 6,
  },
});
