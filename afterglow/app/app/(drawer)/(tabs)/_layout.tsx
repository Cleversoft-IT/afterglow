import { Tabs } from 'expo-router';
import { CommonActions } from '@react-navigation/native';
import { BottomNavigation, Icon } from 'react-native-paper';

export default function TabLayout() {
  return (
    <Tabs
      screenOptions={{ headerShown: false }}
      tabBar={(props) => (
        <BottomNavigation.Bar
          navigationState={props.state}
          safeAreaInsets={props.insets}
          onTabPress={({ route, preventDefault }) => {
            const event = props.navigation.emit({
              type: 'tabPress',
              target: route.key,
              canPreventDefault: true,
            });
            if (event.defaultPrevented) {
              preventDefault();
            } else {
              props.navigation.dispatch({
                ...CommonActions.navigate(route.name, route.params),
                target: props.state.key,
              });
            }
          }}
          renderIcon={({ route, focused, color }) => {
            const { options } = props.descriptors[route.key];
            if (options.tabBarIcon) {
              return options.tabBarIcon({ focused, color, size: 24 });
            }
            return null;
          }}
          getLabelText={({ route }) => {
            const { options } = props.descriptors[route.key];
            const label =
              typeof options.tabBarLabel === 'string'
                ? options.tabBarLabel
                : options.title ?? route.name;
            return label;
          }}
        />
      )}
    >
      <Tabs.Screen
        name="index"
        options={{
          tabBarLabel: 'Home',
          tabBarIcon: ({ color, size, focused }) => (
            <Icon source={focused ? 'home' : 'home-outline'} size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="keypad"
        options={{
          tabBarLabel: 'Keypad',
          tabBarIcon: ({ color, size }) => <Icon source="dialpad" size={size} color={color} />,
        }}
      />
    </Tabs>
  );
}
