import { Ionicons } from '@expo/vector-icons';
import { Stack, useLocalSearchParams, useRouter } from 'expo-router';
import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { Badge } from '../../components/Badge';
import { Button } from '../../components/Button';
import { Card } from '../../components/Card';
import { Checkbox } from '../../components/Checkbox';
import { FormField } from '../../components/FormField';
import { Input } from '../../components/Input';
import { Select } from '../../components/Select';
import { Textarea } from '../../components/Textarea';
import { api, ApiError } from '../../lib/api';
import { useTheme } from '../../lib/ThemeContext';
import { radius, spacing, type ColorPalette } from '../../lib/theme';
import type {
  ActionCatalogEntry,
  ActionDefinition,
  ExecutionMode,
  ExtractorHint,
  FieldDefinition,
  PiiClass,
  PromptHintRule,
  TemplateView,
} from '../../lib/types';

const FIELD_TYPES = [
  { value: 'string', label: 'string' },
  { value: 'integer', label: 'integer' },
  { value: 'boolean', label: 'boolean' },
  { value: 'date', label: 'date' },
  { value: 'time', label: 'time' },
  { value: 'enum', label: 'enum' },
  { value: 'string_list', label: 'list' },
];

const PII_CLASSES: { value: PiiClass; label: string }[] = [
  { value: 'none', label: 'none' },
  { value: 'contact', label: 'contact' },
  { value: 'health', label: 'health' },
  { value: 'financial', label: 'financial' },
  { value: 'identity', label: 'identity' },
];

const EXTRACTOR_HINTS: { value: ExtractorHint; label: string }[] = [
  { value: 'freeform', label: 'freeform' },
  { value: 'regex', label: 'regex' },
  { value: 'enum', label: 'enum' },
  { value: 'llm_only', label: 'llm-only' },
];

const EXECUTION_MODES: { value: ExecutionMode; label: string }[] = [
  { value: 'auto', label: 'auto' },
  { value: 'manual-only', label: 'manual-only' },
];

export default function TemplateDetailScreen() {
  const { colors } = useTheme();
  const styles = useTemplateDetailStyles();
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const [template, setTemplate] = useState<TemplateView | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [activating, setActivating] = useState(false);
  const [cloning, setCloning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [catalog, setCatalog] = useState<ActionCatalogEntry[]>([]);

  // Editable working copies; `template` is the persisted truth from the API.
  const [description, setDescription] = useState('');
  const [domainHint, setDomainHint] = useState('');
  const [dictionary, setDictionary] = useState('');
  const [fields, setFields] = useState<FieldDefinition[]>([]);
  const [actions, setActions] = useState<ActionDefinition[]>([]);
  const [promptHints, setPromptHints] = useState<PromptHintRule[]>([]);

  const load = useCallback(async () => {
    if (!id) return;
    try {
      setError(null);
      const data = await api.getTemplate(id);
      setTemplate(data);
      setDescription(data.description ?? '');
      setDomainHint(data.domain_hint ?? '');
      setDictionary((data.custom_dictionary ?? []).join(', '));
      setFields((data.fields_schema ?? []).map((f) => ({ ...f })));
      setActions((data.action_types ?? []).map((a) => ({ ...a })));
      setPromptHints((data.prompt_hints ?? []).map((h) => ({ ...h })));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    api
      .listActionCatalog()
      .then(setCatalog)
      .catch(() => setCatalog([]));
  }, []);

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
        fields_schema: fields,
        action_types: actions,
        prompt_hints: promptHints,
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

  // Clone seed → editable copy in the same session.
  const cloneAndEdit = async () => {
    if (!template) return;
    setCloning(true);
    setError(null);
    try {
      const created = await api.createTemplate({
        template: {
          name: `${template.name} (custom)`,
          description: template.description ?? '',
          domain_hint: template.domain_hint,
          fields_schema: template.fields_schema,
          action_types: template.action_types,
          custom_dictionary: template.custom_dictionary,
          prompt_hints: template.prompt_hints ?? [],
        },
        set_active: false,
      });
      router.replace(`/templates/${created.id}` as never);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setCloning(false);
    }
  };

  const fieldKeys = useMemo(() => fields.map((f) => f.key).filter(Boolean), [fields]);

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

  const readOnly = template.is_seed === true;

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Stack.Screen options={{ title: template.name }} />

      <Card>
        <View style={styles.headerRow}>
          <View style={{ flex: 1 }}>
            <Text style={styles.title}>{template.name}</Text>
            <Text style={styles.meta}>
              v{template.version} · {template.is_seed ? 'seed (read-only)' : 'custom'}
            </Text>
          </View>
          {template.is_active ? (
            <Badge tone="brand">Active</Badge>
          ) : (
            <Button title="Activate" variant="secondary" onPress={activate} loading={activating} />
          )}
        </View>

        {readOnly ? (
          <View style={styles.cloneRow}>
            <Text style={styles.readOnlyNote}>
              Seed templates are read-only. Make a custom copy to edit fields and actions.
            </Text>
            <Button
              title="Customize copy"
              variant="secondary"
              onPress={cloneAndEdit}
              loading={cloning}
            />
          </View>
        ) : null}

        <FormField label="Description">
          <Textarea value={description} onChangeText={setDescription} editable={!readOnly} />
        </FormField>
        <FormField label="Domain hint">
          <Input value={domainHint} onChangeText={setDomainHint} editable={!readOnly} />
        </FormField>
        <FormField
          label="Custom dictionary"
          hint="Comma-separated terms the ASR engine should recognize."
        >
          <Textarea value={dictionary} onChangeText={setDictionary} editable={!readOnly} />
        </FormField>
      </Card>

      <Card>
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Fields ({fields.length})</Text>
          {!readOnly ? (
            <Pressable
              onPress={() =>
                setFields([
                  ...fields,
                  {
                    key: `field_${fields.length + 1}`,
                    label: 'New field',
                    type: 'string',
                    pii_class: 'none',
                    extractor_hint: 'freeform',
                    required: false,
                    sensitive: false,
                    options: [],
                    depends_on: [],
                  },
                ])
              }
              style={styles.addBtn}
            >
              <Ionicons name="add" size={16} color={colors.brand} />
              <Text style={styles.addBtnText}>Add field</Text>
            </Pressable>
          ) : null}
        </View>
        {fields.map((f, idx) => (
          <FieldEditor
            key={`f-${idx}`}
            field={f}
            otherKeys={fieldKeys.filter((k) => k !== f.key)}
            readOnly={readOnly}
            onChange={(next) =>
              setFields(fields.map((curr, i) => (i === idx ? next : curr)))
            }
            onRemove={() => setFields(fields.filter((_, i) => i !== idx))}
          />
        ))}
      </Card>

      <Card>
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Actions ({actions.length})</Text>
          {!readOnly ? (
            <Pressable
              onPress={() =>
                setActions([
                  ...actions,
                  {
                    key: catalog[0]?.key ?? 'booking.create',
                    label: catalog[0]?.label ?? 'New action',
                    execution_mode: 'auto',
                    mock_target: catalog[0]?.mock_target ?? 'booking',
                    preconditions: [],
                    confidence_threshold: 0.7,
                    mutates: false,
                    evidence_required: true,
                  },
                ])
              }
              style={styles.addBtn}
            >
              <Ionicons name="add" size={16} color={colors.brand} />
              <Text style={styles.addBtnText}>Add action</Text>
            </Pressable>
          ) : null}
        </View>
        {actions.map((a, idx) => (
          <ActionEditor
            key={`a-${idx}`}
            action={a}
            fieldKeys={fieldKeys}
            catalog={catalog}
            readOnly={readOnly}
            onChange={(next) =>
              setActions(actions.map((curr, i) => (i === idx ? next : curr)))
            }
            onRemove={() => setActions(actions.filter((_, i) => i !== idx))}
          />
        ))}
      </Card>

      <Card>
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Prompt rules ({promptHints.length})</Text>
          {!readOnly ? (
            <Pressable
              onPress={() => setPromptHints([...promptHints, { when: 'always', then: '' }])}
              style={styles.addBtn}
            >
              <Ionicons name="add" size={16} color={colors.brand} />
              <Text style={styles.addBtnText}>Add rule</Text>
            </Pressable>
          ) : null}
        </View>
        {promptHints.map((h, idx) => (
          <View key={`h-${idx}`} style={styles.itemRow}>
            <View style={{ flex: 1, gap: spacing.xs }}>
              <FormField label="when">
                <Input
                  value={h.when}
                  onChangeText={(v) =>
                    setPromptHints(
                      promptHints.map((curr, i) => (i === idx ? { ...curr, when: v } : curr)),
                    )
                  }
                  editable={!readOnly}
                />
              </FormField>
              <FormField label="then">
                <Textarea
                  value={h.then}
                  onChangeText={(v) =>
                    setPromptHints(
                      promptHints.map((curr, i) => (i === idx ? { ...curr, then: v } : curr)),
                    )
                  }
                  editable={!readOnly}
                />
              </FormField>
            </View>
            {!readOnly ? (
              <Pressable
                onPress={() => setPromptHints(promptHints.filter((_, i) => i !== idx))}
              >
                <Ionicons name="trash-outline" size={18} color={colors.danger} />
              </Pressable>
            ) : null}
          </View>
        ))}
      </Card>

      {error ? <Text style={styles.error}>{error}</Text> : null}

      {!readOnly ? (
        <View style={styles.footer}>
          <Button title="Save changes" onPress={save} loading={saving} />
        </View>
      ) : null}
    </ScrollView>
  );
}

function FieldEditor({
  field,
  otherKeys,
  readOnly,
  onChange,
  onRemove,
}: {
  field: FieldDefinition;
  otherKeys: string[];
  readOnly: boolean;
  onChange: (next: FieldDefinition) => void;
  onRemove: () => void;
}) {
  const { colors } = useTheme();
  const styles = useTemplateDetailStyles();
  const [expanded, setExpanded] = useState(false);
  return (
    <View style={styles.editorRow}>
      <Pressable
        style={styles.editorHeader}
        onPress={() => setExpanded(!expanded)}
      >
        <Ionicons
          name={expanded ? 'chevron-down' : 'chevron-forward'}
          size={16}
          color={colors.textMuted}
        />
        <View style={{ flex: 1 }}>
          <Text style={styles.itemName}>{field.label || field.key}</Text>
          <Text style={styles.itemMeta}>
            {field.key} · {field.type} · pii={field.pii_class ?? 'none'}
          </Text>
        </View>
        {!readOnly ? (
          <Pressable onPress={onRemove} hitSlop={8}>
            <Ionicons name="trash-outline" size={18} color={colors.danger} />
          </Pressable>
        ) : null}
      </Pressable>

      {expanded ? (
        <View style={styles.editorBody}>
          <FormField label="Label (what the operator sees)">
            <Input
              value={field.label}
              onChangeText={(v) => onChange({ ...field, label: v })}
              editable={!readOnly}
            />
          </FormField>
          <FormField label="Key (machine name, snake_case)">
            <Input
              value={field.key}
              onChangeText={(v) => onChange({ ...field, key: v })}
              editable={!readOnly}
              autoCapitalize="none"
            />
          </FormField>
          <FormField label="Type">
            <Select
              value={field.type}
              options={FIELD_TYPES}
              onChange={(v) => onChange({ ...field, type: v })}
            />
          </FormField>
          <FormField label="PII class">
            <Select
              value={field.pii_class ?? 'none'}
              options={PII_CLASSES.map((p) => ({ value: p.value, label: p.label }))}
              onChange={(v) => onChange({ ...field, pii_class: v as PiiClass })}
            />
          </FormField>
          <FormField label="Extractor hint">
            <Select
              value={field.extractor_hint ?? 'freeform'}
              options={EXTRACTOR_HINTS.map((p) => ({ value: p.value, label: p.label }))}
              onChange={(v) => onChange({ ...field, extractor_hint: v as ExtractorHint })}
            />
          </FormField>
          <Checkbox
            value={!!field.required}
            onChange={(v) => onChange({ ...field, required: v })}
            label="Required"
          />
          <Checkbox
            value={!!field.sensitive}
            onChange={(v) => onChange({ ...field, sensitive: v })}
            label="Sensitive (flag in audit)"
          />
          {field.type === 'enum' ? (
            <FormField label="Enum options (comma-separated)">
              <Input
                value={(field.options ?? []).join(', ')}
                onChangeText={(v) =>
                  onChange({
                    ...field,
                    options: v.split(',').map((s) => s.trim()).filter(Boolean),
                  })
                }
                editable={!readOnly}
              />
            </FormField>
          ) : null}
          <FormField label="Depends on (comma-separated field keys)">
            <Input
              value={(field.depends_on ?? []).join(', ')}
              onChangeText={(v) =>
                onChange({
                  ...field,
                  depends_on: v.split(',').map((s) => s.trim()).filter(Boolean),
                })
              }
              editable={!readOnly}
              autoCapitalize="none"
            />
          </FormField>
          <FormField label="Confidence threshold (0.0–1.0, optional)">
            <Input
              value={
                field.confidence_threshold != null ? String(field.confidence_threshold) : ''
              }
              onChangeText={(v) => {
                const parsed = v.trim() === '' ? null : Number(v);
                onChange({
                  ...field,
                  confidence_threshold:
                    parsed != null && Number.isFinite(parsed) ? parsed : null,
                });
              }}
              editable={!readOnly}
              keyboardType="decimal-pad"
            />
          </FormField>
          {otherKeys.length === 0 ? null : null}
        </View>
      ) : null}
    </View>
  );
}

function ActionEditor({
  action,
  fieldKeys,
  catalog,
  readOnly,
  onChange,
  onRemove,
}: {
  action: ActionDefinition;
  fieldKeys: string[];
  catalog: ActionCatalogEntry[];
  readOnly: boolean;
  onChange: (next: ActionDefinition) => void;
  onRemove: () => void;
}) {
  const { colors } = useTheme();
  const styles = useTemplateDetailStyles();
  const [expanded, setExpanded] = useState(false);
  const catalogEntry = catalog.find((c) => c.key === action.key);
  const integrationBadge = catalogEntry?.integration_kind ?? 'unknown';

  return (
    <View style={styles.editorRow}>
      <Pressable style={styles.editorHeader} onPress={() => setExpanded(!expanded)}>
        <Ionicons
          name={expanded ? 'chevron-down' : 'chevron-forward'}
          size={16}
          color={colors.textMuted}
        />
        <View style={{ flex: 1 }}>
          <Text style={styles.itemName}>{action.label || action.key}</Text>
          <Text style={styles.itemMeta}>
            {action.key} · {action.execution_mode}
            {' · '}
            {integrationBadge === 'internal_real' ? 'internal' : integrationBadge === 'mock_external' ? 'mock' : '?'}
          </Text>
        </View>
        {action.mutates ? <Badge tone="warning">Changes records</Badge> : null}
        {action.evidence_required ? <Badge>Needs transcript proof</Badge> : null}
        {!readOnly ? (
          <Pressable onPress={onRemove} hitSlop={8}>
            <Ionicons name="trash-outline" size={18} color={colors.danger} />
          </Pressable>
        ) : null}
      </Pressable>

      {expanded ? (
        <View style={styles.editorBody}>
          <FormField label="Action key (from catalog)">
            <Select
              value={action.key}
              options={catalog.map((c) => ({ value: c.key, label: c.key }))}
              onChange={(v) => {
                const next = catalog.find((c) => c.key === v);
                onChange({
                  ...action,
                  key: v,
                  label: next?.label ?? action.label,
                  mock_target: next?.mock_target ?? action.mock_target,
                });
              }}
            />
          </FormField>
          {catalogEntry ? (
            <Text style={styles.itemMeta}>{catalogEntry.description}</Text>
          ) : (
            <Text style={[styles.itemMeta, { color: colors.danger }]}>
              ⚠ Unknown action key — pick one from the catalog or the executor will refuse it.
            </Text>
          )}
          <FormField label="Label (operator-facing)">
            <Input
              value={action.label}
              onChangeText={(v) => onChange({ ...action, label: v })}
              editable={!readOnly}
            />
          </FormField>
          <FormField label="Execution mode">
            <Select
              value={action.execution_mode}
              options={EXECUTION_MODES.map((m) => ({ value: m.value, label: m.label }))}
              onChange={(v) => onChange({ ...action, execution_mode: v as ExecutionMode })}
            />
          </FormField>
          <FormField label="Preconditions (comma-separated field keys)">
            <Input
              value={(action.preconditions ?? []).join(', ')}
              onChangeText={(v) =>
                onChange({
                  ...action,
                  preconditions: v.split(',').map((s) => s.trim()).filter(Boolean),
                })
              }
              editable={!readOnly}
              autoCapitalize="none"
            />
            {action.preconditions && action.preconditions.length > 0 && fieldKeys.length > 0 ? (
              <Text style={styles.hint}>
                Available field keys: {fieldKeys.join(', ')}
              </Text>
            ) : null}
          </FormField>
          <FormField label="Confidence threshold (0.0–1.0)">
            <Input
              value={String(action.confidence_threshold ?? 0.7)}
              onChangeText={(v) => {
                const parsed = Number(v);
                onChange({
                  ...action,
                  confidence_threshold:
                    Number.isFinite(parsed) ? parsed : action.confidence_threshold,
                });
              }}
              editable={!readOnly}
              keyboardType="decimal-pad"
            />
          </FormField>
          <Checkbox
            value={!!action.mutates}
            onChange={(v) => onChange({ ...action, mutates: v })}
            label="Changes records (irreversible side effect)"
          />
          <Checkbox
            value={!!action.evidence_required}
            onChange={(v) => onChange({ ...action, evidence_required: v })}
            label="Needs transcript proof"
          />
          <FormField
            label="Payload schema (JSONSchema, optional)"
            hint="Use { } for type:object schemas. Invalid JSON shows as a warning at save time."
          >
            <Textarea
              value={
                action.payload_schema
                  ? JSON.stringify(action.payload_schema, null, 2)
                  : ''
              }
              onChangeText={(v) => {
                if (v.trim() === '') {
                  onChange({ ...action, payload_schema: null });
                  return;
                }
                try {
                  const parsed = JSON.parse(v);
                  onChange({ ...action, payload_schema: parsed });
                } catch {
                  // Defer parsing errors to backend validate; keep the
                  // raw text so the user can keep typing.
                  onChange({ ...action, payload_schema: action.payload_schema });
                }
              }}
              editable={!readOnly}
              numberOfLines={6}
            />
          </FormField>
        </View>
      ) : null}
    </View>
  );
}

function useTemplateDetailStyles() {
  const { colors } = useTheme();
  return useMemo(() => createTemplateDetailStyles(colors), [colors]);
}

function createTemplateDetailStyles(colors: ColorPalette) {
  return StyleSheet.create({
    container: { padding: spacing.lg, gap: spacing.md },
    headerRow: { flexDirection: 'row', alignItems: 'center', gap: spacing.md, marginBottom: spacing.md },
    title: { color: colors.text, fontSize: 18, fontWeight: '600' },
    meta: { color: colors.textMuted, fontSize: 12, marginTop: 2 },
    cloneRow: { gap: spacing.sm, marginBottom: spacing.md },
    readOnlyNote: { color: colors.textMuted, fontStyle: 'italic', fontSize: 13 },
    error: { color: colors.danger, marginTop: spacing.sm, fontSize: 13 },
    sectionHeader: {
      flexDirection: 'row',
      alignItems: 'center',
      justifyContent: 'space-between',
      marginBottom: spacing.sm,
    },
    sectionTitle: { color: colors.text, fontWeight: '600', fontSize: 15 },
    addBtn: {
      flexDirection: 'row',
      alignItems: 'center',
      gap: 4,
      paddingHorizontal: spacing.sm + 2,
      paddingVertical: 5,
      borderRadius: radius.pill,
      backgroundColor: colors.infoBg,
      borderWidth: StyleSheet.hairlineWidth,
      borderColor: colors.infoBorder,
    },
    addBtnText: { color: colors.text, fontSize: 12, fontWeight: '500' },
    editorRow: {
      borderTopWidth: 1,
      borderTopColor: colors.border,
      paddingTop: spacing.sm,
      paddingBottom: spacing.sm,
    },
    editorHeader: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm },
    editorBody: {
      paddingTop: spacing.sm,
      paddingLeft: spacing.lg,
      gap: spacing.sm,
    },
    itemName: { color: colors.text, fontSize: 14, fontWeight: '600' },
    itemMeta: { color: colors.textSubtle, fontSize: 11, marginTop: 2, fontFamily: 'monospace' },
    hint: { color: colors.textSubtle, fontSize: 11, marginTop: 4 },
    itemRow: {
      flexDirection: 'row',
      gap: spacing.sm,
      alignItems: 'flex-start',
      marginBottom: spacing.sm,
      paddingBottom: spacing.sm,
      borderBottomWidth: 1,
      borderBottomColor: colors.border,
    },
    footer: { paddingTop: spacing.md, paddingBottom: spacing.xl },
  });
}
