import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { Card } from '../../components/Card';
import { colors, spacing } from '../../lib/theme';

const apiBase = process.env.EXPO_PUBLIC_API_BASE ?? 'http://localhost:8000';

export default function SettingsScreen() {
  return (
    <ScrollView contentContainerStyle={styles.scroll}>
      <Card>
        <Text style={styles.heading}>Backend</Text>
        <Row label="API base" value={apiBase} />
      </Card>
      <Card>
        <Text style={styles.heading}>About</Text>
        <Text style={styles.body}>
          Afterglow turns the seconds after a phone call into structured data, customer memory,
          and autonomously executed actions. The operator handles the call; the AI runs once the
          call ends.
        </Text>
      </Card>
    </ScrollView>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.row}>
      <Text style={styles.label}>{label}</Text>
      <Text style={styles.value}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  scroll: { padding: spacing.lg, gap: spacing.md },
  heading: { color: colors.text, fontWeight: '700', fontSize: 15 },
  row: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: 8 },
  label: { color: colors.textMuted, fontSize: 13 },
  value: { color: colors.text, fontSize: 13, fontFamily: 'monospace', flex: 1, textAlign: 'right' },
  body: { color: colors.textMuted, fontSize: 13, lineHeight: 18 },
});
