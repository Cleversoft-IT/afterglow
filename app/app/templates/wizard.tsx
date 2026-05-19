import { router, Stack } from 'expo-router';
import { useEffect, useRef, useState } from 'react';
import {
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  View,
} from 'react-native';
import {
  ActivityIndicator,
  Appbar,
  Banner,
  Button,
  Card,
  Chip,
  ProgressBar,
  Surface,
  Text,
  TextInput,
  useTheme,
} from 'react-native-paper';
import { api, ApiError } from '../../lib/api';
import { detectLanguage, type DetectedLanguage } from '../../lib/detectLanguage';
import type {
  TemplateWizardResponse,
  ValidationReport,
  WizardChatTurn,
} from '../../lib/types';

const INITIAL_GREETING =
  'Hi! Tell me a bit about your business — what kind of phone calls do you usually take?';

function formatSlot(v: unknown): string {
  if (v == null) return '—';
  if (Array.isArray(v)) return v.length === 0 ? '[]' : v.map(formatSlot).join(', ');
  if (typeof v === 'object') return JSON.stringify(v);
  return String(v);
}

export default function TemplateWizardScreen() {
  const theme = useTheme();
  const [messages, setMessages] = useState<WizardChatTurn[]>([
    { role: 'assistant', content: INITIAL_GREETING },
  ]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [slots, setSlots] = useState<Record<string, unknown>>({});
  const [confidence, setConfidence] = useState(0);
  const [ready, setReady] = useState(false);
  const [draft, setDraft] = useState<TemplateWizardResponse | null>(null);
  const [validation, setValidation] = useState<ValidationReport | null>(null);
  const [proposedKeys, setProposedKeys] = useState<string[]>([]);
  const [language, setLanguage] = useState<DetectedLanguage>('en');

  const scrollRef = useRef<ScrollView | null>(null);

  useEffect(() => {
    scrollRef.current?.scrollToEnd({ animated: true });
  }, [messages]);

  const send = async () => {
    const trimmed = input.trim();
    if (!trimmed || sending) return;
    const nextMessages: WizardChatTurn[] = [
      ...messages,
      { role: 'user', content: trimmed },
    ];
    setMessages(nextMessages);
    setInput('');
    setSending(true);
    setError(null);
    // Lock the conversation language to whatever the user opened with —
    // mixing English questions with an Italian user disorients the model
    // mid-turn, while re-detecting every reply risks flipping on a short
    // "ok" or "sì".
    const turnLanguage =
      messages.filter((m) => m.role === 'user').length === 0
        ? detectLanguage(trimmed)
        : language;
    if (turnLanguage !== language) setLanguage(turnLanguage);
    try {
      const resp = await api.runWizardChat({
        messages: nextMessages,
        draft_partial: draft,
        slots_filled: slots,
        language: turnLanguage,
      });
      setMessages([...nextMessages, { role: 'assistant', content: resp.assistant_message }]);
      setSlots(resp.slots_filled ?? {});
      setConfidence(resp.confidence);
      setReady(resp.ready);
      setDraft(resp.draft_partial ?? null);
      setValidation(resp.validation ?? null);
      setProposedKeys(resp.proposed_actions_from_catalog ?? []);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setSending(false);
    }
  };

  const save = async (setActive: boolean) => {
    if (!draft) return;
    setSaving(true);
    setError(null);
    try {
      await api.createTemplate({ template: draft, set_active: setActive });
      router.replace('/(drawer)/templates' as never);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  };

  const renameDraft = (next: string) => {
    setDraft((current) => (current ? { ...current, name: next } : current));
  };

  return (
    <KeyboardAvoidingView
      style={{ flex: 1, backgroundColor: theme.colors.background }}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <Stack.Screen
        options={{
          title: 'New template from prompt',
          headerLeft: () => (
            <Appbar.BackAction onPress={() => router.back()} />
          ),
        }}
      />

      <ScrollView
        ref={scrollRef}
        contentContainerStyle={styles.scroll}
        onContentSizeChange={() => scrollRef.current?.scrollToEnd({ animated: true })}
      >
        {messages.map((m, i) => (
          <ChatBubble key={i} role={m.role}>
            {m.content}
          </ChatBubble>
        ))}

        {sending ? (
          <Surface
            mode="flat"
            style={[
              styles.bubble,
              styles.assistantBubble,
              { backgroundColor: theme.colors.elevation.level1 },
            ]}
          >
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
              <ActivityIndicator size="small" />
              <Text variant="bodyMedium" style={{ color: theme.colors.onSurface }}>
                Thinking…
              </Text>
            </View>
          </Surface>
        ) : null}

        <DraftSidebar
          slots={slots}
          confidence={confidence}
          ready={ready}
          draft={draft}
          validation={validation}
          proposedKeys={proposedKeys}
          onRename={renameDraft}
        />

        {error ? (
          <Banner visible icon="alert-circle-outline">
            {error}
          </Banner>
        ) : null}
      </ScrollView>

      <Surface
        elevation={2}
        style={[styles.composer, { backgroundColor: theme.colors.surface }]}
      >
        <TextInput
          mode="outlined"
          value={input}
          onChangeText={setInput}
          placeholder="Type your reply…"
          multiline
          numberOfLines={2}
          editable={!sending}
          onKeyPress={(e) => {
            const ne = e.nativeEvent as { key?: string; shiftKey?: boolean };
            if (ne.key === 'Enter' && !ne.shiftKey) {
              (e as unknown as { preventDefault?: () => void }).preventDefault?.();
              void send();
            }
          }}
          right={
            <TextInput.Icon
              icon="send"
              onPress={send}
              disabled={sending || input.trim() === ''}
            />
          }
        />
        {ready && draft ? (
          <View style={styles.composerActions}>
            <Button
              mode="contained-tonal"
              icon="content-save"
              loading={saving}
              onPress={() => save(false)}
            >
              Save draft
            </Button>
            <Button mode="contained" icon="check" loading={saving} onPress={() => save(true)}>
              Save & activate
            </Button>
          </View>
        ) : null}
      </Surface>
    </KeyboardAvoidingView>
  );
}

function ChatBubble({ role, children }: { role: 'user' | 'assistant'; children: string }) {
  const theme = useTheme();
  const isUser = role === 'user';
  return (
    <Surface
      mode="flat"
      style={[
        styles.bubble,
        isUser ? styles.userBubble : styles.assistantBubble,
        {
          backgroundColor: isUser
            ? theme.colors.primaryContainer
            : theme.colors.elevation.level1,
        },
      ]}
    >
      <Text
        variant="bodyMedium"
        style={{
          color: isUser ? theme.colors.onPrimaryContainer : theme.colors.onSurface,
          lineHeight: 22,
        }}
      >
        {children}
      </Text>
    </Surface>
  );
}

function DraftSidebar({
  slots,
  confidence,
  ready,
  draft,
  validation,
  proposedKeys,
  onRename,
}: {
  slots: Record<string, unknown>;
  confidence: number;
  ready: boolean;
  draft: TemplateWizardResponse | null;
  validation: ValidationReport | null;
  proposedKeys: string[];
  onRename: (next: string) => void;
}) {
  const theme = useTheme();
  const hasContent =
    Object.keys(slots).length > 0 || draft != null || proposedKeys.length > 0;
  if (!hasContent) return null;
  const confidencePct = Math.round(confidence * 100);
  return (
    <Card mode="elevated" style={{ backgroundColor: theme.colors.elevation.level2 }}>
      <Card.Title title="Draft preview" />
      <Card.Content>
        <View style={{ marginBottom: 12 }}>
          <ProgressBar
            progress={Math.min(1, Math.max(0, confidence))}
            color={ready ? theme.colors.primary : theme.colors.secondary}
            style={{ height: 6, borderRadius: 3, marginBottom: 4 }}
          />
          <Text variant="bodySmall" style={{ color: theme.colors.onSurfaceVariant }}>
            {`${confidencePct}% ready`}
          </Text>
        </View>
        {draft ? (
          <View style={{ marginBottom: 12 }}>
            <TextInput
              mode="outlined"
              label="Template name"
              value={draft.name}
              onChangeText={onRename}
              dense
            />
          </View>
        ) : null}

        {Object.keys(slots).length > 0 ? (
          <View style={{ gap: 4 }}>
            {Object.entries(slots).map(([k, v]) => {
              // Prefer the human label from the draft schema; fall back to
              // the raw slot key so we never show nothing if the wizard
              // produced a slot before the matching field landed in the draft.
              const labelFromDraft = draft?.fields_schema.find((f) => f.key === k)?.label;
              const display = labelFromDraft && labelFromDraft.trim() !== '' ? labelFromDraft : k;
              return (
                <Text key={k} variant="bodySmall">
                  <Text style={{ fontWeight: '600' }}>{display}:</Text> {formatSlot(v)}
                </Text>
              );
            })}
          </View>
        ) : null}

        {draft ? (
          <View style={{ marginTop: 12, gap: 8 }}>
            <Text variant="labelMedium" style={{ color: theme.colors.onSurfaceVariant }}>
              Fields ({draft.fields_schema.length})
            </Text>
            <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6 }}>
              {draft.fields_schema.slice(0, 8).map((f) => (
                <Chip key={f.key} mode="outlined" compact textStyle={{ fontSize: 11 }}>
                  {f.label || f.key}
                </Chip>
              ))}
              {draft.fields_schema.length > 8 ? (
                <Chip mode="flat" compact textStyle={{ fontSize: 11 }}>
                  {`+${draft.fields_schema.length - 8} more`}
                </Chip>
              ) : null}
            </View>

            <Text
              variant="labelMedium"
              style={{ color: theme.colors.onSurfaceVariant, marginTop: 4 }}
            >
              Actions ({draft.action_types.length})
            </Text>
            <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6 }}>
              {draft.action_types.map((a) => (
                <Chip key={a.key} mode="outlined" compact textStyle={{ fontSize: 11 }}>
                  {a.label || a.key}
                </Chip>
              ))}
            </View>
          </View>
        ) : null}

        {proposedKeys.length > 0 ? (
          <View style={{ marginTop: 12 }}>
            <Text variant="labelMedium" style={{ color: theme.colors.onSurfaceVariant }}>
              Dropped — not in catalog
            </Text>
            {proposedKeys.map((k) => (
              <Text key={k} variant="bodySmall" style={{ color: theme.colors.onSurfaceVariant }}>
                · {k}
              </Text>
            ))}
          </View>
        ) : null}

        {validation && validation.issues.length > 0 ? (
          <View style={{ marginTop: 12 }}>
            <Text variant="labelMedium" style={{ color: theme.colors.onSurfaceVariant }}>
              Validation
            </Text>
            {validation.issues.map((iss, i) => (
              <Text key={i} variant="bodySmall" style={{ color: theme.colors.onSurfaceVariant }}>
                [{iss.severity}] {iss.field_path}: {iss.message}
              </Text>
            ))}
          </View>
        ) : null}
      </Card.Content>
    </Card>
  );
}

const styles = StyleSheet.create({
  scroll: { padding: 16, gap: 12, paddingBottom: 32 },
  bubble: {
    paddingHorizontal: 16,
    paddingVertical: 14,
    borderRadius: 20,
    maxWidth: '88%',
  },
  userBubble: { alignSelf: 'flex-end', borderBottomRightRadius: 4 },
  assistantBubble: { alignSelf: 'flex-start', borderBottomLeftRadius: 4 },
  composer: { padding: 12, gap: 12 },
  composerActions: { flexDirection: 'row', gap: 8, flexWrap: 'wrap' },
});
