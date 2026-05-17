import { SegmentedButtons, Menu, Button as PaperButton } from 'react-native-paper';
import { useState } from 'react';
import { View, StyleSheet } from 'react-native';

type Option = { label: string; value: string };

export function Select({
  value,
  options,
  onChange,
  placeholder,
}: {
  value: string | null | undefined;
  options: Option[];
  onChange: (next: string) => void;
  placeholder?: string;
}) {
  // For small option sets, use SegmentedButtons (more MD3-native + tap-friendly).
  if (options.length > 0 && options.length <= 4) {
    return (
      <SegmentedButtons
        value={value ?? ''}
        onValueChange={onChange}
        buttons={options.map((o) => ({ value: o.value, label: o.label }))}
      />
    );
  }

  // For larger sets, fall back to a Menu anchored on a Button.
  return <MenuSelect value={value} options={options} onChange={onChange} placeholder={placeholder} />;
}

function MenuSelect({
  value,
  options,
  onChange,
  placeholder,
}: {
  value: string | null | undefined;
  options: Option[];
  onChange: (next: string) => void;
  placeholder?: string;
}) {
  const [visible, setVisible] = useState(false);
  const current = options.find((o) => o.value === value);
  return (
    <View style={styles.wrap}>
      <Menu
        visible={visible}
        onDismiss={() => setVisible(false)}
        anchor={
          <PaperButton mode="outlined" onPress={() => setVisible(true)} icon="chevron-down">
            {current?.label ?? placeholder ?? 'Select…'}
          </PaperButton>
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

const styles = StyleSheet.create({
  wrap: { alignSelf: 'flex-start' },
});
