import { Ionicons } from '@expo/vector-icons';
import { router, Stack } from 'expo-router';
import { useEffect, useMemo, useRef, useState } from 'react';
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { Badge } from '../../components/Badge';
import { Button } from '../../components/Button';
import { Card } from '../../components/Card';
import { Textarea } from '../../components/Textarea';
import { api, ApiError } from '../../lib/api';
import { useTheme } from '../../lib/ThemeContext';
import { radius, spacing, type ColorPalette } from '../../lib/theme';
import type {
  TemplateWizardResponse,
  ValidationReport,
  WizardChatTurn,
} from '../../lib/types';

const INITIAL_GREETING =
  'Hi! Tell me a bit about your business — what kind of phone calls do you usually take?';

export default function TemplateWizardScreen() {
  const { colors } = useTheme();
  const styles = useWizardStyles();
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
    try {
      const resp = await api.runWizardChat({
        messages: nextMessages,
        draft_partial: draft,
        slots_filled: slots,
        language: 'en',
      });
      setMessages([
        ...nextMessages,
        { role: 'assistant', content: resp.assistant_message },
      ]);
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
      const created = await api.createTemplate({
        template: draft,
        set_active: setActive,
      });
      router.replace(`/templates/${created.id}` as never);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  };

  return (
    <KeyboardAvoidingView
      style={{ flex: 1, backgroundColor: colors.bg }}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <Stack.Screen options={{ title: 'New template from prompt' }} />
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
          <View style={[styles.bubble, styles.assistant, { flexDirection: 'row', gap: spacing.sm }]}>
            <ActivityIndicator color={colors.brand} size="small" />
            <Text style={styles.bubbleText}>Thinking…</Text>
          </View>
        ) : null}

        <DraftSidebar
          slots={slots}
          confidence={confidence}
          ready={ready}
          draft={draft}
          validation={validation}
          proposedKeys={proposedKeys}
        />

        {error ? <Text style={styles.error}>{error}</Text> : null}
      </ScrollView>

      <View style={styles.composer}>
        <Textarea
          value={input}
          onChangeText={setInput}
          placeholder="Type your reply…"
          numberOfLines={2}
          editable={!sending}
        />
        <View style={styles.composerRow}>
          <Pressable
            onPress={send}
            disabled={sending || input.trim() === ''}
            style={({ pressed }) => [
              styles.send,
              { opacity: sending || !input.trim() ? 0.5 : pressed ? 0.85 : 1 },
            ]}
          >
            <Ionicons name="send" size={16} color={colors.onPrimary} />
            <Text style={styles.sendText}>Send</Text>
          </Pressable>
          {ready && draft ? (
            <>
              <Button
                title="Save draft"
                variant="secondary"
                onPress={() => save(false)}
                loading={saving}
              />
              <Button
                title="Save & activate"
                onPress={() => save(true)}
                loading={saving}
              />
            </>
          ) : null}
        </View>
      </View>
    </KeyboardAvoidingView>
  );
}

function ChatBubble({
  role,
  children,
}: {
  role: 'user' | 'assistant';
  children: string;
}) {
  const styles = useWizardStyles();
  const isUser = role === 'user';
  return (
    <View style={[styles.bubble, isUser ? styles.user : styles.assistant]}>
      <Text style={[styles.bubbleText, isUser && styles.bubbleTextUser]}>{children}</Text>
    </View>
  );
}

function DraftSidebar({
  slots,
  confidence,
  ready,
  draft,
  validation,
  proposedKeys,
}: {
  slots: Record<string, unknown>;
  confidence: number;
  ready: boolean;
  draft: TemplateWizardResponse | null;
  validation: ValidationReport | null;
  proposedKeys: string[];
}) {
  const styles = useWizardStyles();
  const hasContent =
    Object.keys(slots).length > 0 || draft != null || proposedKeys.length > 0;
  if (!hasContent) return null;
  const confidencePct = Math.round(confidence * 100);
  return (
    <Card>
      <View style={styles.draftHeader}>
        <Text style={styles.draftTitle}>Draft preview</Text>
        <Badge tone={ready ? 'success' : 'neutral'}>{`${confidencePct}% ready`}</Badge>
      </View>

      {Object.keys(slots).length > 0 ? (
        <View style={{ marginTop: spacing.sm, gap: 4 }}>
          {Object.entries(slots).map(([k, v]) => (
            <Text key={k} style={styles.slotLine}>
              <Text style={styles.slotKey}>{k}:</Text> {formatSlot(v)}
            </Text>
          ))}
        </View>
      ) : null}

      {draft ? (
        <View style={{ marginTop: spacing.md, gap: 4 }}>
          <Text style={styles.draftSection}>Fields ({draft.fields_schema.length})</Text>
          {draft.fields_schema.slice(0, 6).map((f) => (
            <Text key={f.key} style={styles.draftLine}>
              · {f.label || f.key} <Text style={styles.draftMeta}>({f.type})</Text>
            </Text>
          ))}
          {draft.fields_schema.length > 6 ? (
            <Text style={styles.draftMeta}>+{draft.fields_schema.length - 6} more</Text>
          ) : null}

          <Text style={[styles.draftSection, { marginTop: spacing.sm }]}>
            Actions ({draft.action_types.length})
          </Text>
          {draft.action_types.map((a) => (
            <Text key={a.key} style={styles.draftLine}>
              · {a.label || a.key} <Text style={styles.draftMeta}>({a.execution_mode})</Text>
            </Text>
          ))}
        </View>
      ) : null}

      {proposedKeys.length > 0 ? (
        <View style={{ marginTop: spacing.md }}>
          <Text style={styles.draftSection}>Dropped — not in catalog</Text>
          {proposedKeys.map((k) => (
            <Text key={k} style={styles.draftMeta}>· {k}</Text>
          ))}
        </View>
      ) : null}

      {validation && validation.issues.length > 0 ? (
        <View style={{ marginTop: spacing.md }}>
          <Text style={styles.draftSection}>Validation</Text>
          {validation.issues.map((iss, i) => (
            <Text key={i} style={styles.draftMeta}>
              [{iss.severity}] {iss.field_path}: {iss.message}
            </Text>
          ))}
        </View>
      ) : null}
    </Card>
  );
}

function formatSlot(v: unknown): string {
  if (v == null) return '—';
  if (Array.isArray(v)) return v.length === 0 ? '[]' : v.map(formatSlot).join(', ');
  if (typeof v === 'object') return JSON.stringify(v);
  return String(v);
}

function useWizardStyles() {
  const { colors } = useTheme();
  return useMemo(() => createWizardStyles(colors), [colors]);
}

function createWizardStyles(colors: ColorPalette) {
  return StyleSheet.create({
    scroll: { padding: spacing.lg, gap: spacing.md, paddingBottom: spacing.xxl },
    bubble: {
      paddingHorizontal: spacing.lg,
      paddingVertical: spacing.md + 2,
      borderRadius: radius.xl,
      maxWidth: '88%',
    },
    user: {
      alignSelf: 'flex-end',
      backgroundColor: colors.brand,
    },
    assistant: {
      alignSelf: 'flex-start',
      backgroundColor: colors.surface,
      borderWidth: StyleSheet.hairlineWidth,
      borderColor: colors.border,
    },
    bubbleText: { color: colors.text, fontSize: 15, lineHeight: 22 },
    bubbleTextUser: { color: colors.onPrimary },
    error: { color: colors.danger, fontSize: 14, marginTop: spacing.sm },
    composer: {
      padding: spacing.lg,
      borderTopWidth: StyleSheet.hairlineWidth,
      borderTopColor: colors.border,
      backgroundColor: colors.surface,
      gap: spacing.md,
    },
    composerRow: {
      flexDirection: 'row',
      alignItems: 'center',
      gap: spacing.sm,
      flexWrap: 'wrap',
    },
    send: {
      flexDirection: 'row',
      alignItems: 'center',
      gap: 6,
      paddingHorizontal: spacing.lg,
      paddingVertical: spacing.sm + 2,
      backgroundColor: colors.brand,
      borderRadius: radius.pill,
      minHeight: 40,
    },
    sendText: { color: colors.onPrimary, fontWeight: '500', fontSize: 14 },
    draftHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
    draftTitle: { color: colors.text, fontWeight: '600', fontSize: 15 },
    draftSection: { color: colors.textMuted, fontWeight: '600', fontSize: 12, marginBottom: 2 },
    draftLine: { color: colors.text, fontSize: 14, lineHeight: 20 },
    draftMeta: { color: colors.textSubtle, fontSize: 12 },
    slotLine: { color: colors.text, fontSize: 13, lineHeight: 19 },
    slotKey: { color: colors.text, fontWeight: '600' },
  });
}
