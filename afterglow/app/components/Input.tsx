import { TextInput as PaperTextInput } from 'react-native-paper';
import type { TextInputProps } from 'react-native';

export function Input({ value, onChangeText, placeholder, editable, style, ...rest }: TextInputProps) {
  return (
    <PaperTextInput
      mode="outlined"
      value={value ?? ''}
      onChangeText={onChangeText}
      placeholder={placeholder}
      editable={editable}
      dense
      style={style as never}
      {...(rest as object)}
    />
  );
}
