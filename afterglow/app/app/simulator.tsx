import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { Badge } from '../components/Badge';
import { Button } from '../components/Button';
import { Card } from '../components/Card';
import { api, ApiError } from '../lib/api';
import { useTheme } from '../lib/ThemeContext';
import { radius, spacing } from '../lib/theme';
import type { SimulationConfig, SimulationScenario, TemplateView } from '../lib/types';

type CallerMode = 'existing' | 'new';

export default function SimulatorScreen() {
  const { colors } = useTheme();
  const router = useRouter();
  const [template, setTemplate] = useState<TemplateView | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [generatingScript, setGeneratingScript] = useState(false);
  const [generatingAudio, setGeneratingAudio] = useState(false);
  const [uploading, setUploading] = useState(false);

  const load = useCallback(async () => {
    try {
      setError(null);
      const t = await api.getActiveTemplate();
      setTemplate(t);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const trigger = (mode: CallerMode) => {
    if (!template) return;
    router.push(`/incoming-call?caller=${mode}` as never);
  };

  const generateScript = async () => {
    if (!template) return;
    setGeneratingScript(true);
    setError(null);
    try {
      const updated = await api.generateSimulationScript(template.id);
      setTemplate(updated);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setGeneratingScript(false);
    }
  };

  const generateAudio = async () => {
    if (!template) return;
    setGeneratingAudio(true);
    setError(null);
    try {
      const updated = await api.generateSimulationAudio(template.id);
      setTemplate(updated);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setGeneratingAudio(false);
    }
  };

  const pickAndUpload = async () => {
    if (!template) return;
    if (typeof document === 'undefined') {
      setError('File upload is only available in the web build for now.');
      return;
    }
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'audio/wav,audio/mpeg,audio/mp3';
    input.onchange = async () => {
      const file = input.files?.[0];
      if (!file) return;
      setUploading(true);
      setError(null);
      try {
        const updated = await api.uploadSimulationAudio(
          template.id,
          file,
          file.name,
        );
        setTemplate(updated);
      } catch (e) {
        setError(e instanceof ApiError ? e.message : String(e));
      } finally {
        setUploading(false);
      }
    };
    input.click();
  };

  const styles = useMemo(
    () =>
      StyleSheet.create({
        scroll: { padding: spacing.lg, gap: spacing.lg, paddingBottom: spacing.xxxl },
        headerRow: {
          flexDirection: 'row',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: spacing.sm,
        },
        heading: { color: colors.text, fontWeight: '600', fontSize: 16, flex: 1 },
        section: { color: colors.text, fontWeight: '600', fontSize: 15, marginBottom: spacing.sm },
        body: { color: colors.textMuted, fontSize: 14, lineHeight: 21 },
        bold: { color: colors.text, fontWeight: '600' },
        cta: { alignItems: 'stretch', paddingVertical: spacing.md, gap: spacing.sm },
        scriptBlock: {
          marginTop: spacing.md,
          padding: spacing.md + 2,
          borderRadius: radius.lg,
          backgroundColor: colors.surfaceAlt,
          borderWidth: StyleSheet.hairlineWidth,
          borderColor: colors.border,
          gap: 4,
        },
        scriptTitle: {
          color: colors.text,
          fontWeight: '600',
          fontSize: 13,
          marginBottom: spacing.xs,
        },
        scriptLine: { color: colors.textMuted, fontSize: 13, lineHeight: 20 },
        scriptSpeaker: { color: colors.text, fontWeight: '600' },
        error: { color: colors.danger, fontSize: 14 },
      }),
    [colors],
  );

  if (loading) return <ActivityIndicator color={colors.brand} style={{ marginTop: 32 }} />;

  if (!template) {
    return (
      <ScrollView contentContainerStyle={styles.scroll}>
        <Card>
          <Text style={styles.heading}>No active template</Text>
          <Text style={styles.body}>
            Pick or create a template in the Templates tab and activate it before running the
            simulator.
          </Text>
        </Card>
        {error ? <Text style={styles.error}>{error}</Text> : null}
      </ScrollView>
    );
  }

  const sim = template.simulation_config;
  // Seeded templates ship `scenarios.{existing,new}`; wizard-built templates
  // still use the flat shape. Treat the simulator as "ready" if either the
  // legacy flat audio is in place OR both per-mode scenarios are ready.
  const seededScenariosReady =
    sim?.scenarios?.existing?.audio_status === 'ready' &&
    !!sim?.scenarios?.existing?.audio_url &&
    sim?.scenarios?.new?.audio_status === 'ready' &&
    !!sim?.scenarios?.new?.audio_url;
  const legacyReady = sim?.audio_status === 'ready' && !!sim?.audio_url;
  const audioReady = seededScenariosReady || legacyReady;
  const hasScript =
    (sim?.scenarios?.existing?.script_turns?.length ?? 0) > 0 ||
    (sim?.scenarios?.new?.script_turns?.length ?? 0) > 0 ||
    (sim?.script_turns?.length ?? 0) > 0;

  return (
    <ScrollView contentContainerStyle={styles.scroll}>
      <Card>
        <View style={styles.headerRow}>
          <Text style={styles.heading}>Incoming call simulator</Text>
          {audioReady ? (
            <Badge tone="success">audio ready</Badge>
          ) : (
            <Badge tone="warning">audio missing</Badge>
          )}
        </View>
        <Text style={styles.body}>
          Active template: <Text style={styles.bold}>{template.name}</Text> ({template.domain_hint})
        </Text>
      </Card>

      {audioReady ? (
        <Card>
          <Text style={styles.section}>Trigger demo call</Text>
          <Text style={styles.body}>
            Existing customer plays back the seed phone number for this template; new customer
            generates a fresh phone so you can watch Afterglow create the record from scratch.
          </Text>
          <View style={styles.cta}>
            <TriggerButton mode="existing" onPress={() => trigger('existing')} />
            <TriggerButton mode="new" onPress={() => trigger('new')} />
          </View>
        </Card>
      ) : (
        <Card>
          <Text style={styles.section}>This template has no demo recording yet</Text>
          <Text style={styles.body}>
            Generate a script + MP3 with Speechmatics TTS, or upload your own recording. Once an
            audio is in place the trigger buttons will appear.
          </Text>

          <View style={[styles.cta, { gap: spacing.sm }]}>
            <Button
              title={hasScript ? 'Regenerate script' : 'Generate script'}
              variant="secondary"
              onPress={generateScript}
              loading={generatingScript}
            />
            <Button
              title="Generate audio (Speechmatics TTS)"
              onPress={generateAudio}
              loading={generatingAudio}
              disabled={!hasScript}
            />
            <Button
              title="Upload audio file (mp3/wav)"
              variant="secondary"
              onPress={pickAndUpload}
              loading={uploading}
            />
          </View>

          {hasScript ? <ScriptPreview sim={sim} /> : null}
        </Card>
      )}

      {error ? (
        <Card>
          <Text style={styles.error}>{error}</Text>
        </Card>
      ) : null}
    </ScrollView>
  );
}

function ScriptPreview({ sim }: { sim: SimulationConfig | null | undefined }) {
  const { colors } = useTheme();
  const styles = useMemo(
    () =>
      StyleSheet.create({
        scriptBlock: {
          marginTop: spacing.md,
          padding: spacing.md + 2,
          borderRadius: radius.lg,
          backgroundColor: colors.surfaceAlt,
          borderWidth: StyleSheet.hairlineWidth,
          borderColor: colors.border,
          gap: 4,
        },
        scriptTitle: {
          color: colors.text,
          fontWeight: '600',
          fontSize: 13,
          marginBottom: spacing.xs,
        },
        scriptLine: { color: colors.textMuted, fontSize: 13, lineHeight: 20 },
        scriptSpeaker: { color: colors.text, fontWeight: '600' },
      }),
    [colors],
  );

  if (!sim) return null;
  const fromScenarios: Array<{ key: CallerMode; label: string; scenario: SimulationScenario }> = [];
  if (sim.scenarios?.existing?.script_turns?.length) {
    fromScenarios.push({
      key: 'existing',
      label: 'Existing caller',
      scenario: sim.scenarios.existing,
    });
  }
  if (sim.scenarios?.new?.script_turns?.length) {
    fromScenarios.push({
      key: 'new',
      label: 'New caller',
      scenario: sim.scenarios.new,
    });
  }
  // Custom wizard-built templates ship the legacy flat shape — render that
  // single block when no scenarios map is present.
  if (fromScenarios.length === 0 && sim.script_turns?.length) {
    fromScenarios.push({
      key: 'existing',
      label: 'Script preview',
      scenario: sim as SimulationScenario,
    });
  }
  if (fromScenarios.length === 0) return null;
  return (
    <View style={{ gap: spacing.md }}>
      {fromScenarios.map(({ key, label, scenario }) => (
        <View key={key} style={styles.scriptBlock}>
          <Text style={styles.scriptTitle}>
            {label} · {scenario.caller_name ?? 'unknown caller'} ·{' '}
            {scenario.caller_phone_e164 ?? '(random phone)'}
          </Text>
          {scenario.script_turns?.map((t, i) => (
            <Text key={i} style={styles.scriptLine}>
              <Text style={styles.scriptSpeaker}>{t.speaker}</Text> ({t.voice}): {t.text}
            </Text>
          ))}
        </View>
      ))}
    </View>
  );
}

function TriggerButton({
  mode,
  onPress,
}: {
  mode: CallerMode;
  onPress: () => void;
}) {
  const { colors } = useTheme();
  const styles = useMemo(
    () =>
      StyleSheet.create({
        triggerExisting: {
          flexDirection: 'row',
          alignItems: 'center',
          justifyContent: 'center',
          gap: spacing.sm,
          backgroundColor: colors.brand,
          paddingVertical: spacing.md + 2,
          paddingHorizontal: spacing.xl,
          borderRadius: radius.pill,
          minHeight: 48,
        },
        triggerNew: {
          flexDirection: 'row',
          alignItems: 'center',
          justifyContent: 'center',
          gap: spacing.sm,
          backgroundColor: colors.surface,
          paddingVertical: spacing.md + 2,
          paddingHorizontal: spacing.xl,
          borderRadius: radius.pill,
          borderWidth: 1,
          borderColor: colors.border,
          minHeight: 48,
        },
        triggerText: { color: colors.onPrimary, fontWeight: '500', fontSize: 15 },
        triggerTextOutline: { color: colors.text },
      }),
    [colors],
  );
  const existing = mode === 'existing';
  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [
        existing ? styles.triggerExisting : styles.triggerNew,
        { opacity: pressed ? 0.85 : 1, transform: [{ scale: pressed ? 0.98 : 1 }] },
      ]}
    >
      <Ionicons
        name={existing ? 'person' : 'person-add'}
        size={18}
        color={existing ? colors.onPrimary : colors.text}
      />
      <Text style={[styles.triggerText, !existing && styles.triggerTextOutline]}>
        {existing ? 'Call from existing customer' : 'Call from new customer'}
      </Text>
    </Pressable>
  );
}

