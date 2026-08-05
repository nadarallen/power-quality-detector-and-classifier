/*
 * Root Mobile Application Entry Point (App.js)
 */

import React from 'react';
import { SafeAreaView, StatusBar, StyleSheet } from 'react-native';
import { MinimalismTheme } from './src/theme/minimalismTheme';
import { LiveMonitoringScreen } from './src/screens/LiveMonitoringScreen';

export default function App() {
  return (
    <SafeAreaView style={styles.safeArea}>
      <StatusBar barStyle="light-content" backgroundColor={MinimalismTheme.colors.bgSpace} />
      <LiveMonitoringScreen />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: MinimalismTheme.colors.bgSpace,
  },
});
