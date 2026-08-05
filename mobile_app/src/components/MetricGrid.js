/*
 * Metric Grid Component for Mobile App
 */

import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { MinimalismTheme } from '../theme/minimalismTheme';

export const MetricGrid = ({ rms = 0.998, thd = 0.82, modelSize = '8.4 KB' }) => {
  return (
    <View style={styles.gridContainer}>
      <View style={styles.card}>
        <Text style={styles.label}>RMS VOLTAGE</Text>
        <Text style={styles.value}>{rms.toFixed(3)} <Text style={styles.unit}>pu</Text></Text>
        <Text style={styles.subtext}>12.0V Nominal</Text>
      </View>

      <View style={styles.card}>
        <Text style={styles.label}>THD PERCENT</Text>
        <Text style={styles.value}>{thd.toFixed(2)} <Text style={styles.unit}>%</Text></Text>
        <Text style={styles.subtext}>IEEE 519 Pass</Text>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  gridContainer: {
    flexDirection: 'row',
    gap: 12,
    marginBottom: 16,
  },
  card: {
    flex: 1,
    backgroundColor: MinimalismTheme.colors.bgCardSolid,
    borderRadius: MinimalismTheme.borderRadius.md,
    padding: 16,
    borderWidth: 1,
    borderColor: MinimalismTheme.colors.borderSubtle,
  },
  label: {
    fontSize: 10,
    fontWeight: '600',
    color: MinimalismTheme.colors.textMuted,
    letterSpacing: 0.5,
    marginBottom: 4,
  },
  value: {
    fontSize: 20,
    fontWeight: '700',
    color: MinimalismTheme.colors.textMain,
  },
  unit: {
    fontSize: 12,
    fontWeight: '400',
    color: MinimalismTheme.colors.textDim,
  },
  subtext: {
    fontSize: 11,
    color: MinimalismTheme.colors.textDim,
    marginTop: 4,
  }
});
