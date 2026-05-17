import { Checkbox as PaperCheckbox } from 'react-native-paper';

export function Checkbox({
  value,
  onChange,
  label,
}: {
  value: boolean;
  onChange: (next: boolean) => void;
  label: string;
}) {
  return (
    <PaperCheckbox.Item
      label={label}
      status={value ? 'checked' : 'unchecked'}
      onPress={() => onChange(!value)}
      position="leading"
    />
  );
}
