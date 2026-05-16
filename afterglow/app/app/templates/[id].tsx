import { Stack, useLocalSearchParams } from 'expo-router';
import { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { Badge } from '../../components/Badge';
import { Button } from '../../components/Button';
import { Card } from '../../components/Card';
import { FormField } from '../../components/FormField';
import { Input } from '../../components/Input';
import { Textarea } from '../../components/Textarea';
import { api, ApiError } from '../../lib/api';
import { colors, spacing } from '../../lib/theme';
import type { TemplateView } from '../../lib/types';

export default function TemplateDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const [template, setTemplate] = useState<TemplateView | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [activating, setActivating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Editable copies (only the simple top-level fields; the field/action
  // schemas remain read-only here — the wizard owns the deep edit surface
  // for now and a future iteration can add an inline field editor).
  const [description, setDescription] = useState('');
  const [domainHint, setDomainHint] = useState('');
  const [dictionary, setDictionary] = useState('');

  const load = useCallback(async () => {
    if (!id) return;
    try {
      setError(null);
      const data = await api.getTemplate(id);
      setTemplate(data);
      setDescription(data.description ?? '');
      setDomainHint(data.domain_hint ?? '');
      setDictionary((data.custom_dictionary ?? []).join(', '));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  const save = async () => {
    if (!template || template.is_seed) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await api.updateTemplate(template.id, {
        description,
        domain_hint: domainHint,
        custom_dictionary: dictionary
          .split(',')
          .map((t) => t.trim())
          .filter((t) => t.length > 0),
      });
      setTemplate(updated);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  };

  const activate = async () => {
    if (!template) return;
    setActivating(true);
    setError(null);
    try {
      const updated = await api.setActiveTemplate(template.id);
      setTemplate(updated);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setActivating(false);
    }
  };

  if (loading) {
    return <ActivityIndicator color={colors.brand} style={{ marginTop: spacing.xxl }} />;
  }
  if (!template) {
    return (
      <View style={styles.container}>
        <Text style={styles.error}>{error ?? 'Not found'}</Text>
      </View>
    );
  }

  const readOnly = template.is_seed;

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Stack.Screen options={{ title: template.name }} />

      <Card>
        <View style={styles.headerRow}>
          <View style={{ flex: 1 }}>
            <Text style={styles.title}>{template.name}</Text>
            <Text style={styles.meta}>
              v{template.version} · {template.is_seed ? 'seed' : 'custom'}
            </Text>
          </View>
          {template.is_active ? (
            <Badge tone="brand">Active</Badge>
          ) : (
            <Button title="Activate" variant="secondary" onPress={activate} loading={activating} />
          )}
        </View>

        {readOnly ? (
          <Text style={styles.readOnlyNote}>
            Seed templates are read-only. Duplicate via the wizard to customize.
          </Text>
        ) : null}

        <FormField label="Description">
          <Textarea
            value={description}
            onChangeText={setDescription}
            editable={!readOnly}
          />
        </FormField>
        <FormField label="Domain hint">
          <Input
            value={domainHint}
            onChangeText={setDomainHint}
            editable={!readOnly}
          />
        </FormField>
        <FormField
          label="Custom dictionary"
          hint="Comma-separated terms the ASR engine should know."
        >
          <Textarea
            value={dictionary}
            onChangeText={setDictionary}
            editable={!readOnly}
          />
        </FormField>

        {!readOnly ? (
          <Button title="Save changes" onPress={save} loading={saving} />
        ) : null}
        {error ? <Text style={styles.error}>{error}</Text> : null}
      </Card>

      <Card>
        <Text style={styles.sectionTitle}>Fields ({template.fields_schema.length})</Text>
        {template.fields_schema.map((f) => (
          <View key={f.key} style={styles.itemRow}>
            <View style={{ flex: 1 }}>
              <Text style={styles.itemName}>
                {f.key} <Text style={styles.itemType}>· {f.type}</Text>
              </Text>
              <Text style={styles.itemMeta}>
                pii={f.pii_class ?? 'none'} · hint={f.extractor_hint ?? 'freeform'}
                {f.confidence_threshold != null ? ` · ≥${f.confidence_threshold}` : ''}
                {f.depends_on && f.depends_on.length ? ` · depends_on=${f.depends_on.join(',')}` : ''}
              </Text>
            </View>
            {f.required ? <Badge tone="neutral">required</Badge> : null}
            {f.sensitive ? <Badge tone="warning">sensitive</Badge> : null}
          </View>
        ))}
      </Card>

      <Card>
        <Text style={styles.sectionTitle}>Actions ({template.action_types.length})</Text>
        {template.action_types.map((a) => (
          <View key={a.key} style={styles.itemRow}>
            <View style={{ flex: 1 }}>
              <Text style={styles.itemName}>{a.key}</Text>
              <Text style={styles.itemMeta}>
                {a.execution_mode} · mock={a.mock_target ?? '—'}
                {a.preconditions && a.preconditions.length
                  ? ` · needs=${a.preconditions.join(',')}`
                  : ''}
                {a.confidence_threshold != null ? ` · ≥${a.confidence_threshold}` : ''}
              </Text>
            </View>
            {a.mutates ? <Badge tone="warning">mutates</Badge> : null}
            {a.evidence_required ? <Badge tone="neutral">evidence</Badge> : null}
          </View>
        ))}
      </Card>

      {template.prompt_hints && template.prompt_hints.length > 0 ? (
        <Card>
          <Text style={styles.sectionTitle}>
            Prompt rules ({template.prompt_hints.length})
          </Text>
          {template.prompt_hints.map((h, i) => (
            <View key={i} style={{ gap: 2, marginBottom: spacing.sm }}>
              <Text style={styles.itemName}>when: {h.when}</Text>
              <Text style={styles.itemMeta}>{h.then}</Text>
            </View>
          ))}
        </Card>
      ) : null}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: spacing.lg, gap: spacing.md },
  headerRow: { flexDirection: 'row', alignItems: 'center', gap: spacing.md, marginBottom: spacing.md },
  title: { color: colors.text, fontSize: 18, fontWeight: '700' },
  meta: { color: colors.textMuted, fontSize: 12, marginTop: 2 },
  readOnlyNote: {
    color: colors.textMuted,
    fontStyle: 'italic',
    fontSize: 13,
    marginBottom: spacing.sm,
  },
  error: { color: colors.danger, marginTop: spacing.sm, fontSize: 13 },
  sectionTitle: { color: colors.text, fontWeight: '700', fontSize: 14, marginBottom: spacing.sm },
  itemRow: {
    flexDirection: 'row',
    gap: spacing.sm,
    alignItems: 'center',
    marginBottom: spacing.sm,
    paddingBottom: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  itemName: { color: colors.text, fontFamily: 'monospace', fontSize: 13, fontWeight: '600' },
  itemType: { color: colors.textMuted, fontWeight: '400' },
  itemMeta: { color: colors.textSubtle, fontSize: 11, marginTop: 2 },
});
