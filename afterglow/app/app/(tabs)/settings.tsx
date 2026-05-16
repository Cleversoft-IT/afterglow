import { ScrollView, StyleSheet, Text } from 'react-native';
import { Card } from '../../components/Card';
import { colors, spacing } from '../../lib/theme';

export default function SettingsScreen() {
  return (
    <ScrollView contentContainerStyle={styles.scroll}>
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

const styles = StyleSheet.create({
  scroll: { padding: spacing.lg, gap: spacing.md },
  heading: { color: colors.text, fontWeight: '700', fontSize: 15 },
  body: { color: colors.textMuted, fontSize: 13, lineHeight: 18 },
});
