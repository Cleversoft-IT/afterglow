import { TextInput as PaperTextInput } from 'react-native-paper';
import type { TextInputProps } from 'react-native';

export function Textarea({
  value,
  onChangeText,
  placeholder,
  editable,
  numberOfLines = 4,
  style,
  ...rest
}: TextInputProps) {
  return (
    <PaperTextInput
      mode="outlined"
      value={value ?? ''}
      onChangeText={onChangeText}
      placeholder={placeholder}
      editable={editable}
      multiline
      numberOfLines={numberOfLines}
      style={style as never}
      {...(rest as object)}
    />
  );
}
