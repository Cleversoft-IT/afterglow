import { Stack, useLocalSearchParams, useRouter } from 'expo-router';
import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';
import {
  ActivityIndicator,
  Button,
  Card,
  Checkbox,
  Chip,
  HelperText,
  Icon,
  IconButton,
  Menu,
  SegmentedButtons,
  Text,
  TextInput,
  TouchableRipple,
  useTheme,
} from 'react-native-paper';
import { api, ApiError } from '../../lib/api';
import type { AppTheme } from '../../lib/paperTheme';
import type {
  ActionCatalogEntry,
  ActionDefinition,
  ExecutionMode,
  ExtractorHint,
  FieldDefinition,
  PromptHintRule,
  TemplateView,
} from '../../lib/types';

const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  xxl: 32,
} as const;

const FIELD_TYPES = [
  { value: 'string', label: 'string' },
  { value: 'integer', label: 'integer' },
  { value: 'boolean', label: 'boolean' },
  { value: 'date', label: 'date' },
  { value: 'time', label: 'time' },
  { value: 'enum', label: 'enum' },
  { value: 'string_list', label: 'list' },
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

type Option = { label: string; value: string };

export default function TemplateDetailScreen() {
  const theme = useTheme<AppTheme>();
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
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [domainHint, setDomainHint] = useState('');
  const [fields, setFields] = useState<FieldDefinition[]>([]);
  const [actions, setActions] = useState<ActionDefinition[]>([]);
  const [promptHints, setPromptHints] = useState<PromptHintRule[]>([]);

  const load = useCallback(async () => {
    if (!id) return;
    try {
      setError(null);
      const data = await api.getTemplate(id);
      setTemplate(data);
      setName(data.name ?? '');
      setDescription(data.description ?? '');
      setDomainHint(data.domain_hint ?? '');
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
        name: name.trim(),
        description,
        domain_hint: domainHint,
        fields_schema: fields,
        action_types: actions,
        prompt_hints: promptHints,
      });
      setTemplate(updated);
      setName(updated.name ?? '');
      router.replace('/(drawer)/templates' as never);
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) {
        setError('A template with this name already exists.');
      } else if (e instanceof ApiError && e.status === 422) {
        setError('Template name cannot be empty.');
      } else {
        setError(e instanceof ApiError ? e.message : String(e));
      }
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
    return <ActivityIndicator color={theme.colors.primary} style={{ marginTop: spacing.xxl }} />;
  }
  if (!template) {
    return (
      <View style={styles.container}>
        <Text variant="bodyMedium" style={{ color: theme.colors.error }}>
          {error ?? 'Not found'}
        </Text>
      </View>
    );
  }

  const readOnly = template.is_seed === true;

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Stack.Screen options={{ title: template.name }} />

      <Card mode="elevated">
        <Card.Content style={styles.cardContent}>
          <View style={styles.headerRow}>
            <View style={styles.headerTitle}>
              <Text variant="titleMedium">{template.name}</Text>
              <Text variant="bodySmall" style={{ color: theme.colors.onSurfaceVariant }}>
                v{template.version} - {template.is_seed ? 'seed (read-only)' : 'custom'}
              </Text>
            </View>
            {template.is_active ? (
              <Chip compact mode="flat" style={{ backgroundColor: theme.colors.primaryContainer }}>
                Active
              </Chip>
            ) : (
              <Button mode="outlined" onPress={activate} loading={activating}>
                Activate
              </Button>
            )}
          </View>

          {readOnly ? (
            <View style={styles.cloneRow}>
              <Text variant="bodySmall" style={{ color: theme.colors.onSurfaceVariant }}>
                Seed templates are read-only. Make a custom copy to edit fields and actions.
              </Text>
              <Button mode="outlined" onPress={cloneAndEdit} loading={cloning}>
                Customize copy
              </Button>
            </View>
          ) : null}

          <FormField label="Name">
            <TextInput
              mode="outlined"
              value={name}
              onChangeText={setName}
              editable={!readOnly}
            />
          </FormField>
          <FormField label="Description">
            <TextInput
              mode="outlined"
              value={description}
              onChangeText={setDescription}
              editable={!readOnly}
              multiline
              numberOfLines={4}
            />
          </FormField>
          <FormField label="Domain hint">
            <TextInput
              mode="outlined"
              value={domainHint}
              onChangeText={setDomainHint}
              editable={!readOnly}
            />
          </FormField>
        </Card.Content>
      </Card>

      <Card mode="elevated">
        <Card.Content style={styles.cardContent}>
          <View style={styles.sectionHeader}>
            <Text variant="titleSmall">Fields ({fields.length})</Text>
            {!readOnly ? (
              <Button
                mode="text"
                icon="plus"
                compact
                onPress={() =>
                  setFields([
                    ...fields,
                    {
                      key: `field_${fields.length + 1}`,
                      label: 'New field',
                      type: 'string',
                      extractor_hint: 'freeform',
                      required: false,
                      options: [],
                      depends_on: [],
                    },
                  ])
                }
              >
                Add field
              </Button>
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
        </Card.Content>
      </Card>

      <Card mode="elevated">
        <Card.Content style={styles.cardContent}>
          <View style={styles.sectionHeader}>
            <Text variant="titleSmall">Actions ({actions.length})</Text>
            {!readOnly ? (
              <Button
                mode="text"
                icon="plus"
                compact
                onPress={() =>
                  setActions([
                    ...actions,
                    {
                      key: catalog[0]?.key ?? 'booking.create',
                      label: catalog[0]?.label ?? 'New action',
                      execution_mode: 'auto',
                      preconditions: [],
                      confidence_threshold: 0.7,
                      evidence_required: true,
                    },
                  ])
                }
              >
                Add action
              </Button>
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
        </Card.Content>
      </Card>

      <Card mode="elevated">
        <Card.Content style={styles.cardContent}>
          <View style={styles.sectionHeader}>
            <Text variant="titleSmall">Prompt rules ({promptHints.length})</Text>
            {!readOnly ? (
              <Button
                mode="text"
                icon="plus"
                compact
                onPress={() => setPromptHints([...promptHints, { when: 'always', then: '' }])}
              >
                Add rule
              </Button>
            ) : null}
          </View>
          {promptHints.map((h, idx) => (
            <View key={`h-${idx}`} style={styles.itemRow}>
              <View style={styles.itemContent}>
                <FormField label="when">
                  <TextInput
                    mode="outlined"
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
                  <TextInput
                    mode="outlined"
                    value={h.then}
                    onChangeText={(v) =>
                      setPromptHints(
                        promptHints.map((curr, i) => (i === idx ? { ...curr, then: v } : curr)),
                      )
                    }
                    editable={!readOnly}
                    multiline
                    numberOfLines={4}
                  />
                </FormField>
              </View>
              {!readOnly ? (
                <IconButton
                  icon="trash-can-outline"
                  iconColor={theme.colors.error}
                  onPress={() => setPromptHints(promptHints.filter((_, i) => i !== idx))}
                />
              ) : null}
            </View>
          ))}
        </Card.Content>
      </Card>

      {error ? (
        <Text variant="bodySmall" style={{ color: theme.colors.error }}>
          {error}
        </Text>
      ) : null}

      {!readOnly ? (
        <View style={styles.footer}>
          <Button mode="contained" onPress={save} loading={saving}>
            Save changes
          </Button>
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
  const theme = useTheme<AppTheme>();
  const styles = useTemplateDetailStyles();
  const [expanded, setExpanded] = useState(false);

  return (
    <View style={styles.editorRow}>
      <EditorHeader
        expanded={expanded}
        title={field.label || field.key}
        meta={`${field.key} - ${field.type}`}
        onPress={() => setExpanded(!expanded)}
        trailing={
          !readOnly ? (
            <IconButton
              icon="trash-can-outline"
              iconColor={theme.colors.error}
              onPress={onRemove}
            />
          ) : null
        }
      />

      {expanded ? (
        <View style={styles.editorBody}>
          <FormField label="Label (what the operator sees)">
            <TextInput
              mode="outlined"
              value={field.label}
              onChangeText={(v) => onChange({ ...field, label: v })}
              editable={!readOnly}
            />
          </FormField>
          <FormField label="Key (machine name, snake_case)">
            <TextInput
              mode="outlined"
              value={field.key}
              onChangeText={(v) => onChange({ ...field, key: v })}
              editable={!readOnly}
              autoCapitalize="none"
            />
          </FormField>
          <FormField label="Type">
            <SelectField
              value={field.type}
              options={FIELD_TYPES}
              disabled={readOnly}
              onChange={(v) => onChange({ ...field, type: v })}
            />
          </FormField>
          <FormField label="Extractor hint">
            <SelectField
              value={field.extractor_hint ?? 'freeform'}
              options={EXTRACTOR_HINTS.map((p) => ({ value: p.value, label: p.label }))}
              disabled={readOnly}
              onChange={(v) => onChange({ ...field, extractor_hint: v as ExtractorHint })}
            />
          </FormField>
          <Checkbox.Item
            label="Required"
            status={field.required ? 'checked' : 'unchecked'}
            onPress={() => onChange({ ...field, required: !field.required })}
            disabled={readOnly}
            position="leading"
          />
          {field.type === 'enum' ? (
            <FormField label="Enum options (comma-separated)">
              <TextInput
                mode="outlined"
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
            <TextInput
              mode="outlined"
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
          <FormField label="Confidence threshold (0.0-1.0, optional)">
            <TextInput
              mode="outlined"
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
  const theme = useTheme<AppTheme>();
  const styles = useTemplateDetailStyles();
  const [expanded, setExpanded] = useState(false);
  const catalogEntry = catalog.find((c) => c.key === action.key);
  const integrationBadge = catalogEntry?.integration_kind ?? 'unknown';

  return (
    <View style={styles.editorRow}>
      <EditorHeader
        expanded={expanded}
        title={action.label || action.key}
        meta={`${action.key} - ${action.execution_mode} - ${
          integrationBadge === 'internal_real'
            ? 'internal'
            : integrationBadge === 'mock_external'
              ? 'mock'
              : '?'
        }`}
        onPress={() => setExpanded(!expanded)}
        badges={
          <View style={styles.badgeRow}>
            {catalogEntry?.mutates ? (
              <Chip compact textStyle={{ fontSize: 11 }}>
                Changes records
              </Chip>
            ) : null}
            {action.evidence_required ? (
              <Chip compact textStyle={{ fontSize: 11 }}>
                Needs transcript proof
              </Chip>
            ) : null}
          </View>
        }
        trailing={
          !readOnly ? (
            <IconButton
              icon="trash-can-outline"
              iconColor={theme.colors.error}
              onPress={onRemove}
            />
          ) : null
        }
      />

      {expanded ? (
        <View style={styles.editorBody}>
          <FormField label="Action key (from catalog)">
            <SelectField
              value={action.key}
              options={catalog.map((c) => ({ value: c.key, label: c.key }))}
              disabled={readOnly}
              onChange={(v) => {
                const next = catalog.find((c) => c.key === v);
                onChange({
                  ...action,
                  key: v,
                  label: next?.label ?? action.label,
                });
              }}
            />
          </FormField>
          {catalogEntry ? (
            <Text variant="bodySmall" style={styles.metaText}>
              {catalogEntry.description}
            </Text>
          ) : (
            <Text variant="bodySmall" style={{ color: theme.colors.error }}>
              Unknown action key. Pick one from the catalog or the executor will refuse it.
            </Text>
          )}
          <FormField label="Label (operator-facing)">
            <TextInput
              mode="outlined"
              value={action.label}
              onChangeText={(v) => onChange({ ...action, label: v })}
              editable={!readOnly}
            />
          </FormField>
          <FormField label="Execution mode">
            <SelectField
              value={action.execution_mode}
              options={EXECUTION_MODES.map((m) => ({ value: m.value, label: m.label }))}
              disabled={readOnly}
              onChange={(v) => onChange({ ...action, execution_mode: v as ExecutionMode })}
            />
          </FormField>
          <FormField label="Preconditions (comma-separated field keys)">
            <TextInput
              mode="outlined"
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
              <Text variant="bodySmall" style={styles.metaText}>
                Available field keys: {fieldKeys.join(', ')}
              </Text>
            ) : null}
          </FormField>
          <FormField label="Confidence threshold (0.0-1.0)">
            <TextInput
              mode="outlined"
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
          <Checkbox.Item
            label="Needs transcript proof"
            status={action.evidence_required ? 'checked' : 'unchecked'}
            onPress={() => onChange({ ...action, evidence_required: !action.evidence_required })}
            disabled={readOnly}
            position="leading"
          />
          <FormField
            label="Payload schema (JSONSchema, optional)"
            hint="Use { } for type:object schemas. Invalid JSON shows as a warning at save time."
          >
            <TextInput
              mode="outlined"
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
                  onChange({ ...action, payload_schema: action.payload_schema });
                }
              }}
              editable={!readOnly}
              multiline
              numberOfLines={6}
            />
          </FormField>
        </View>
      ) : null}
    </View>
  );
}

function FormField({
  label,
  hint,
  error,
  children,
}: {
  label: string;
  hint?: string;
  error?: string | null;
  children: ReactNode;
}) {
  return (
    <View style={fieldStyles.wrap}>
      <Text variant="labelLarge">{label}</Text>
      {children}
      {error ? (
        <HelperText type="error" visible>
          {error}
        </HelperText>
      ) : hint ? (
        <HelperText type="info" visible>
          {hint}
        </HelperText>
      ) : null}
    </View>
  );
}

function SelectField({
  value,
  options,
  disabled,
  onChange,
}: {
  value: string | null | undefined;
  options: Option[];
  disabled?: boolean;
  onChange: (next: string) => void;
}) {
  if (options.length > 0 && options.length <= 4) {
    return (
      <SegmentedButtons
        value={value ?? ''}
        onValueChange={onChange}
        buttons={options.map((o) => ({ value: o.value, label: o.label, disabled }))}
      />
    );
  }

  return <MenuSelect value={value} options={options} disabled={disabled} onChange={onChange} />;
}

function MenuSelect({
  value,
  options,
  disabled,
  onChange,
}: {
  value: string | null | undefined;
  options: Option[];
  disabled?: boolean;
  onChange: (next: string) => void;
}) {
  const [visible, setVisible] = useState(false);
  const current = options.find((o) => o.value === value);
  return (
    <View style={fieldStyles.menuWrap}>
      <Menu
        visible={visible}
        onDismiss={() => setVisible(false)}
        anchor={
          <Button
            mode="outlined"
            icon="chevron-down"
            disabled={disabled || options.length === 0}
            onPress={() => setVisible(true)}
          >
            {current?.label ?? 'Select'}
          </Button>
        }
      >
        {options.map((opt) => (
          <Menu.Item
            key={opt.value}
            onPress={() => {
              onChange(opt.value);
              setVisible(false);
            }}
            title={opt.label}
          />
        ))}
      </Menu>
    </View>
  );
}

function EditorHeader({
  expanded,
  title,
  meta,
  badges,
  trailing,
  onPress,
}: {
  expanded: boolean;
  title: string;
  meta: string;
  badges?: ReactNode;
  trailing?: ReactNode;
  onPress: () => void;
}) {
  const theme = useTheme<AppTheme>();
  const styles = useTemplateDetailStyles();
  return (
    <TouchableRipple onPress={onPress} borderless>
      <View style={styles.editorHeader}>
        <Icon
          source={expanded ? 'chevron-down' : 'chevron-right'}
          size={20}
          color={theme.colors.onSurfaceVariant}
        />
        <View style={styles.itemContent}>
          <Text variant="bodyMedium">{title}</Text>
          <Text variant="bodySmall" style={styles.metaText}>
            {meta}
          </Text>
          {badges ? <View style={{ marginTop: 4 }}>{badges}</View> : null}
        </View>
        {trailing}
      </View>
    </TouchableRipple>
  );
}

function useTemplateDetailStyles() {
  const theme = useTheme<AppTheme>();
  return useMemo(() => createTemplateDetailStyles(theme), [theme]);
}

function createTemplateDetailStyles(theme: AppTheme) {
  return StyleSheet.create({
    container: {
      padding: spacing.lg,
      gap: spacing.md,
      backgroundColor: theme.colors.background,
    },
    cardContent: { gap: spacing.md },
    headerRow: { flexDirection: 'row', alignItems: 'center', gap: spacing.md },
    headerTitle: { flex: 1, gap: 2 },
    cloneRow: { gap: spacing.sm },
    sectionHeader: {
      flexDirection: 'row',
      alignItems: 'center',
      justifyContent: 'space-between',
      gap: spacing.md,
    },
    editorRow: {
      borderTopWidth: StyleSheet.hairlineWidth,
      borderTopColor: theme.colors.outlineVariant,
      paddingTop: spacing.sm,
    },
    editorHeader: {
      minHeight: 48,
      flexDirection: 'row',
      alignItems: 'center',
      gap: spacing.sm,
      paddingVertical: spacing.xs,
    },
    editorBody: {
      paddingTop: spacing.sm,
      paddingLeft: spacing.xl,
      gap: spacing.sm,
    },
    itemRow: {
      flexDirection: 'row',
      gap: spacing.sm,
      alignItems: 'flex-start',
      borderTopWidth: StyleSheet.hairlineWidth,
      borderTopColor: theme.colors.outlineVariant,
      paddingTop: spacing.sm,
    },
    itemContent: { flex: 1, gap: spacing.xs },
    metaText: { color: theme.colors.onSurfaceVariant },
    badgeRow: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.xs, justifyContent: 'flex-start' },
    footer: { paddingTop: spacing.md, paddingBottom: spacing.xl },
  });
}

const fieldStyles = StyleSheet.create({
  wrap: { gap: spacing.xs },
  menuWrap: { alignSelf: 'flex-start' },
});
