import { DrawerActions } from '@react-navigation/native';
import { useLocalSearchParams, useNavigation, useRouter } from 'expo-router';
import { useCallback, useEffect, useState } from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';
import {
  ActivityIndicator,
  Appbar,
  Avatar,
  Banner,
  Button,
  Card,
  Chip,
  List,
  Text,
  useTheme,
} from 'react-native-paper';
import { api, ApiError } from '../../lib/api';
import type { SimulationConfig, SimulationScenario, TemplateView } from '../../lib/types';

type CallerMode = 'existing' | 'new';

function domainIcon(domain: string | null | undefined): string {
  switch (domain) {
    case 'restaurant':
      return 'silverware-fork-knife';
    case 'dentist':
      return 'tooth-outline';
    case 'bodyshop':
      return 'car-wrench';
    default:
      return 'phone-in-talk';
  }
}

export default function SimulatorScreen() {
  const theme = useTheme();
  const router = useRouter();
  const navigation = useNavigation();
  const params = useLocalSearchParams<{ audioMissing?: string }>();
  const audioMissingHint = params.audioMissing === '1';
  const [template, setTemplate] = useState<TemplateView | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [generatingScript, setGeneratingScript] = useState(false);
  const [generatingAudio, setGeneratingAudio] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [missingBannerVisible, setMissingBannerVisible] = useState(audioMissingHint);

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
        const updated = await api.uploadSimulationAudio(template.id, file, file.name);
        setTemplate(updated);
      } catch (e) {
        setError(e instanceof ApiError ? e.message : String(e));
      } finally {
        setUploading(false);
      }
    };
    input.click();
  };

  const header = (
    <Appbar.Header mode="small" elevated={false} style={{ backgroundColor: theme.colors.background }}>
      <Appbar.Action icon="menu" onPress={() => navigation.dispatch(DrawerActions.openDrawer())} />
      <Appbar.Content title="Test simulator" />
    </Appbar.Header>
  );

  if (loading) {
    return (
      <View style={{ flex: 1, backgroundColor: theme.colors.background }}>
        {header}
        <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center' }}>
          <ActivityIndicator />
        </View>
      </View>
    );
  }

  if (!template) {
    return (
      <View style={{ flex: 1, backgroundColor: theme.colors.background }}>
        {header}
        <ScrollView contentContainerStyle={styles.scroll}>
          <Card mode="elevated">
            <Card.Title
              title="No active template"
              left={(p) => <Avatar.Icon {...p} icon="alert-circle-outline" />}
            />
            <Card.Content>
              <Text variant="bodyMedium" style={{ color: theme.colors.onSurfaceVariant }}>
                Pick or create a template in the drawer and activate it before running the simulator.
              </Text>
            </Card.Content>
          </Card>
          {error ? (
            <Banner visible icon="alert-circle-outline">
              {error}
            </Banner>
          ) : null}
        </ScrollView>
      </View>
    );
  }

  const sim = template.simulation_config;
  const seededScenariosReady =
    sim?.scenarios?.existing?.audio_status === 'ready' &&
    !!sim?.scenarios?.existing?.audio_url &&
    sim?.scenarios?.new?.audio_status === 'ready' &&
    !!sim?.scenarios?.new?.audio_url;
  const legacyReady = sim?.audio_status === 'ready' && !!sim?.audio_url;
  const audioReady = seededScenariosReady || legacyReady;
  // Seed templates ship `scenarios.{existing,new}` AND a matching seeded
  // Customer row for the existing-caller phone, so the incoming-call
  // screen can resolve a real customer when the operator hits "Call
  // from existing customer". Wizard-built (non-seed) templates also
  // ship two scenarios, but the existing-caller phone is fabricated by
  // Gemini ("never a real number" — see simulation_script.py) and will
  // never match a seeded Customer. The dialer would then mislabel the
  // call as "New caller" anyway, so we hide the button entirely on
  // wizard templates and only expose the "new customer" path until the
  // wizard learns to seed a matching Customer.
  const hasTwoScenarios =
    !!(sim?.scenarios?.existing && sim?.scenarios?.new) && !!template.is_seed;
  const hasScript =
    (sim?.scenarios?.existing?.script_turns?.length ?? 0) > 0 ||
    (sim?.scenarios?.new?.script_turns?.length ?? 0) > 0 ||
    (sim?.script_turns?.length ?? 0) > 0;

  return (
    <View style={{ flex: 1, backgroundColor: theme.colors.background }}>
      {header}
      <ScrollView contentContainerStyle={styles.scroll}>
      <Card mode="elevated">
        <Card.Content style={{ gap: 12 }}>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}>
            <Avatar.Icon size={40} icon={domainIcon(template.domain_hint)} />
            <View style={{ flex: 1 }}>
              <Text variant="labelMedium" style={{ color: theme.colors.onSurfaceVariant }}>
                Active template
              </Text>
              <Text variant="titleMedium">{template.name}</Text>
              <Text variant="bodySmall" style={{ color: theme.colors.onSurfaceVariant }}>
                {template.domain_hint}
              </Text>
            </View>
          </View>
          <Chip
            icon={audioReady ? 'check' : 'progress-clock'}
            compact
            selected={audioReady}
            style={{ alignSelf: 'flex-start' }}
          >
            {audioReady ? 'Audio ready' : 'Audio not ready'}
          </Chip>
        </Card.Content>
      </Card>

      {audioReady ? (
        <Card mode="elevated">
          <Card.Title title="Trigger demo call" />
          <Card.Content>
            <Text variant="bodyMedium" style={{ color: theme.colors.onSurfaceVariant, marginBottom: 12 }}>
              {hasTwoScenarios
                ? 'Existing customer plays back a recording for a caller the system already knows; new customer generates a fresh phone so you can watch Afterglow create the record from scratch.'
                : 'Custom templates only expose the new-customer path: the Wizard fabricates a fresh phone number for the existing-caller script, which won’t match any seeded contact, so we keep the demo honest and skip that button.'}
            </Text>
          </Card.Content>
          <Card.Actions style={{ flexDirection: 'column', gap: 8, padding: 16 }}>
            {hasTwoScenarios ? (
              <Button
                mode="contained"
                icon="phone-incoming"
                onPress={() => trigger('existing')}
                style={{ alignSelf: 'stretch' }}
                contentStyle={{ paddingVertical: 6 }}
              >
                Call from existing customer
              </Button>
            ) : null}
            <Button
              mode={hasTwoScenarios ? 'outlined' : 'contained'}
              icon="account-plus-outline"
              onPress={() => trigger('new')}
              style={{ alignSelf: 'stretch' }}
              contentStyle={{ paddingVertical: 6 }}
            >
              Call from new customer
            </Button>
          </Card.Actions>
        </Card>
      ) : (
        <Card mode="elevated">
          <Card.Title
            title="This template has no demo recording yet"
            left={(p) => <Avatar.Icon {...p} icon="microphone-message-off" />}
          />
          <Card.Content>
            <Text variant="bodyMedium" style={{ color: theme.colors.onSurfaceVariant, marginBottom: 12 }}>
              Generate a script + MP3 with Speechmatics TTS, or upload your own recording. Once an
              audio is in place the trigger buttons will appear.
            </Text>
          </Card.Content>
          <Card.Actions style={{ flexDirection: 'column', gap: 8, padding: 16 }}>
            <Button
              mode="text"
              icon="script-text-outline"
              onPress={generateScript}
              loading={generatingScript}
            >
              {hasScript ? 'Regenerate script' : 'Generate script'}
            </Button>
            <Button
              mode="contained-tonal"
              icon="record-rec"
              onPress={generateAudio}
              loading={generatingAudio}
              disabled={!hasScript}
            >
              Generate audio (Speechmatics TTS)
            </Button>
            <Button mode="text" icon="upload-outline" onPress={pickAndUpload} loading={uploading}>
              Upload audio file (mp3/wav)
            </Button>
          </Card.Actions>
        </Card>
      )}

      {hasScript ? <ScriptPreview sim={sim} /> : null}

      {missingBannerVisible ? (
        <Banner
          visible
          icon="alert-circle-outline"
          actions={[
            { label: 'Dismiss', onPress: () => setMissingBannerVisible(false) },
          ]}
        >
          The audio for this template was flagged ready but is missing on disk. Regenerate it below to make the dialer work again.
        </Banner>
      ) : null}
      {error ? (
        <Banner visible icon="alert-circle-outline">
          {error}
        </Banner>
      ) : null}
      </ScrollView>
    </View>
  );
}

function ScriptPreview({ sim }: { sim: SimulationConfig | null | undefined }) {
  const theme = useTheme();
  if (!sim) return null;
  const fromScenarios: Array<{ key: CallerMode; label: string; scenario: SimulationScenario }> = [];
  if (sim.scenarios?.existing?.script_turns?.length) {
    fromScenarios.push({ key: 'existing', label: 'Existing caller', scenario: sim.scenarios.existing });
  }
  if (sim.scenarios?.new?.script_turns?.length) {
    fromScenarios.push({ key: 'new', label: 'New caller', scenario: sim.scenarios.new });
  }
  if (fromScenarios.length === 0 && sim.script_turns?.length) {
    fromScenarios.push({ key: 'existing', label: 'Script preview', scenario: sim as SimulationScenario });
  }
  if (fromScenarios.length === 0) return null;

  return (
    <Card mode="elevated">
      <Card.Title title="Script preview" />
      <Card.Content style={{ paddingHorizontal: 0 }}>
        {fromScenarios.map(({ key, label, scenario }) => (
          <List.Accordion
            key={key}
            title={label}
            description={`${scenario.caller_name ?? 'unknown'} · ${scenario.caller_phone_e164 ?? '(random)'}`}
            left={(p) => <List.Icon {...p} icon={key === 'existing' ? 'account' : 'account-plus-outline'} />}
          >
            <View style={{ paddingHorizontal: 16, paddingBottom: 8, gap: 6 }}>
              {scenario.script_turns?.map((t, i) => (
                <Text key={i} variant="bodyMedium" style={{ lineHeight: 20 }}>
                  <Text style={{ fontWeight: '600' }}>{t.speaker}</Text>
                  <Text style={{ color: theme.colors.onSurfaceVariant }}> ({t.voice})</Text>: {t.text}
                </Text>
              ))}
            </View>
          </List.Accordion>
        ))}
      </Card.Content>
    </Card>
  );
}

const styles = StyleSheet.create({
  scroll: { padding: 16, gap: 16, paddingBottom: 48 },
});
