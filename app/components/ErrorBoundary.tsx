import { Component, type ReactNode } from 'react';
import { View } from 'react-native';
import { Banner, Button } from 'react-native-paper';

// Defensive boundary for list-heavy screens. If a single row's render throws
// (most common cause: malformed booking date emitted by a custom template's
// `Date` field), keep the rest of the screen alive instead of crashing the
// whole React tree to a blank surface.
//
// Functional ErrorBoundaries don't exist — React requires class components.

type Props = { children: ReactNode; onReset?: () => void };
type State = { error: Error | null };

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error): void {
    // eslint-disable-next-line no-console
    console.error('[ErrorBoundary]', error);
  }

  reset = (): void => {
    this.setState({ error: null });
    this.props.onReset?.();
  };

  render(): ReactNode {
    if (this.state.error) {
      return (
        <View style={{ padding: 12 }}>
          <Banner
            visible
            icon="alert-circle-outline"
            actions={[{ label: 'Retry', onPress: this.reset }]}
          >
            Something went wrong rendering this section. The rest of the app is
            still working — tap Retry, or reload if it keeps failing.
          </Banner>
        </View>
      );
    }
    return this.props.children;
  }
}
