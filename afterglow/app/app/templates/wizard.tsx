import { router, Stack } from 'expo-router';
import { useState } from 'react';
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
import type {
  TemplateWizardResponse,
  ValidationIssue,
  ValidationReport,
} from '../../lib/types';

type Step = 'describe' | 'review';

export default function TemplateWizardScreen() {
  const [step, setStep] = useState<Step>('describe');
  const [description, setDescription] = useState('');
  const [language] = useState('en');
  const [generating, setGenerating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [revalidating, setRevalidating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState<TemplateWizardResponse | null>(null);

  const generate = async () => {
    setGenerating(true);
    setError(null);
    try {
      const out = await api.runWizard({ description, language });
      setDraft(out);
      setStep('review');
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setGenerating(false);
    }
  };

  const revalidate = async () => {
    if (!draft) return;
    setRevalidating(true);
    setError(null);
    try {
      const report = await api.validateDraft(draft);
      setDraft({ ...draft, validation: report });
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setRevalidating(false);
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
    <ScrollView contentContainerStyle={styles.container}>
      <Stack.Screen options={{ title: 'New template from prompt' }} />

      {step === 'describe' ? (
        <Card>
          <FormField
            label="Describe the business intake"
            hint="One or two sentences. The wizard turns this into a structured template."
          >
            <Textarea
              value={description}
              onChangeText={setDescription}
              placeholder="e.g. Booking intake for a barbershop with kids haircuts and walk-ins."
              numberOfLines={5}
            />
          </FormField>
          <Button
            title="Generate template"
            onPress={generate}
            loading={generating}
            disabled={description.trim().length < 20}
          />
          {error ? <Text style={styles.error}>{error}</Text> : null}
        </Card>
      ) : null}

      {step === 'review' && draft ? (
        <View style={{ gap: spacing.md }}>
          <Card>
            <FormField label="Name">
              <Input
                value={draft.name}
                onChangeText={(text) => setDraft({ ...draft, name: text })}
              />
            </FormField>
            <FormField label="Description">
              <Textarea
                value={draft.description}
                onChangeText={(text) => setDraft({ ...draft, description: text })}
              />
            </FormField>
            <FormField label="Domain hint">
              <Input
                value={draft.domain_hint ?? ''}
                onChangeText={(text) => setDraft({ ...draft, domain_hint: text })}
              />
            </FormField>
          </Card>

          <ValidationCard report={draft.validation ?? null} />

          <FieldsCard fields={draft.fields_schema} />
          <ActionsCard actions={draft.action_types} />
          <PromptHintsCard hints={draft.prompt_hints} />
          <DictionaryCard terms={draft.custom_dictionary} />

          {error ? <Text style={styles.error}>{error}</Text> : null}

          <View style={styles.actionsRow}>
            <Button
              title="Re-validate"
              variant="secondary"
              onPress={revalidate}
              loading={revalidating}
            />
            <Button
              title="Save (draft)"
              variant="secondary"
              onPress={() => save(false)}
              loading={saving}
            />
            <Button
              title="Save & activate"
              onPress={() => save(true)}
              loading={saving}
            />
          </View>
        </View>
      ) : null}

      {generating ? (
        <ActivityIndicator color={colors.brand} style={{ marginTop: spacing.lg }} />
      ) : null}
    </ScrollView>
  );
}

function ValidationCard({ report }: { report: ValidationReport | null }) {
  if (!report) return null;
  const hasIssues = report.issues.length > 0;
  const hasMocks = report.proposed_mocks.length > 0;
  if (!hasIssues && !hasMocks) {
    return (
      <Card>
        <Text style={styles.sectionTitle}>Validation</Text>
        <Badge tone="success">No issues</Badge>
      </Card>
    );
  }
  return (
    <Card>
      <Text style={styles.sectionTitle}>Validation</Text>
      {report.issues.map((issue, i) => (
        <View key={`${issue.field_path}-${i}`} style={styles.issueRow}>
          <Badge tone={severityTone(issue.severity)}>{issue.severity}</Badge>
          <View style={{ flex: 1 }}>
            <Text style={styles.fieldPath}>{issue.field_path}</Text>
            <Text style={styles.fieldMsg}>{issue.message}</Text>
          </View>
        </View>
      ))}
      {hasMocks ? (
        <View style={{ marginTop: spacing.md, gap: spacing.xs }}>
          <Text style={styles.sectionSubtitle}>Proposed mock targets</Text>
          {report.proposed_mocks.map((m) => (
            <Text key={m.action_key} style={styles.fieldMsg}>
              <Text style={styles.fieldPath}>{m.action_key}</Text>
              {' → '}
              <Text style={{ color: colors.brand }}>{m.suggested_mock_target}</Text>
              {`. ${m.rationale}`}
            </Text>
          ))}
        </View>
      ) : null}
    </Card>
  );
}

function severityTone(s: ValidationIssue['severity']) {
  if (s === 'error') return 'danger' as const;
  if (s === 'warning') return 'warning' as const;
  return 'neutral' as const;
}

function FieldsCard({ fields }: { fields: TemplateWizardResponse['fields_schema'] }) {
  return (
    <Card>
      <Text style={styles.sectionTitle}>Fields ({fields.length})</Text>
      {fields.map((f) => (
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
  );
}

function ActionsCard({ actions }: { actions: TemplateWizardResponse['action_types'] }) {
  return (
    <Card>
      <Text style={styles.sectionTitle}>Actions ({actions.length})</Text>
      {actions.map((a) => (
        <View key={a.key} style={styles.itemRow}>
          <View style={{ flex: 1 }}>
            <Text style={styles.itemName}>{a.key}</Text>
            <Text style={styles.itemMeta}>
              {a.execution_mode} · mock={a.mock_target ?? '—'}
              {a.preconditions && a.preconditions.length ? ` · needs=${a.preconditions.join(',')}` : ''}
              {a.confidence_threshold != null ? ` · ≥${a.confidence_threshold}` : ''}
            </Text>
          </View>
          {a.mutates ? <Badge tone="warning">mutates</Badge> : null}
          {a.evidence_required ? <Badge tone="neutral">evidence</Badge> : null}
        </View>
      ))}
    </Card>
  );
}

function PromptHintsCard({ hints }: { hints: TemplateWizardResponse['prompt_hints'] }) {
  if (!hints || hints.length === 0) return null;
  return (
    <Card>
      <Text style={styles.sectionTitle}>Prompt rules ({hints.length})</Text>
      {hints.map((h, i) => (
        <View key={i} style={{ gap: 2, marginBottom: spacing.sm }}>
          <Text style={styles.fieldPath}>when: {h.when}</Text>
          <Text style={styles.fieldMsg}>{h.then}</Text>
        </View>
      ))}
    </Card>
  );
}

function DictionaryCard({ terms }: { terms: string[] }) {
  return (
    <Card>
      <Text style={styles.sectionTitle}>Custom dictionary ({terms.length})</Text>
      <Text style={styles.fieldMsg}>{terms.join(', ') || '—'}</Text>
    </Card>
  );
}

const styles = StyleSheet.create({
  container: { padding: spacing.lg, gap: spacing.md },
  error: { color: colors.danger, marginTop: spacing.sm, fontSize: 13 },
  actionsRow: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm },
  sectionTitle: { color: colors.text, fontWeight: '700', fontSize: 14, marginBottom: spacing.sm },
  sectionSubtitle: { color: colors.textMuted, fontWeight: '600', fontSize: 12 },
  issueRow: { flexDirection: 'row', gap: spacing.sm, alignItems: 'flex-start', marginBottom: spacing.sm },
  fieldPath: { color: colors.text, fontFamily: 'monospace', fontSize: 12 },
  fieldMsg: { color: colors.textMuted, fontSize: 13 },
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
