/*
 * Minimalist Status Hero Card Component for Mobile App
 */

import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { MinimalismTheme } from '../theme/minimalismTheme';

export const StatusHeroCard = ({ stateName = 'Normal', confidence = 96.3 }) => {
  const getBadgeColor = (name) => {
    switch (name) {
      case 'Normal': return MinimalismTheme.colors.normal;
      case 'Sag': return MinimalismTheme.colors.sag;
      case 'Swell': return MinimalismTheme.colors.swell;
      case 'Harmonics': return MinimalismTheme.colors.harmonics;
      case 'Interruption': return MinimalismTheme.colors.interruption;
      default: return MinimalismTheme.colors.accentCyan;
    }
  };

  const badgeColor = getBadgeColor(stateName);

  return (
    <View style={styles.card}>
      <Text style={styles.subLabel}>CURRENT GRID STATUS</Text>
      <Text style={[styles.statusTitle, { color: badgeColor }]}>{stateName}</Text>
      <View style={styles.confidenceBadge}>
        <Text style={styles.confidenceText}>Confidence: {confidence.toFixed(1)}%</Text>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  card: {
    backgroundColor: MinimalismTheme.colors.bgCardSolid,
    borderRadius: MinimalismTheme.borderRadius.lg,
    padding: 24,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: MinimalismTheme.colors.borderGlow,
    marginBottom: 16,
  },
  subLabel: {
    fontSize: 12,
    fontWeight: '600',
    color: MinimalismTheme.colors.textMuted,
    letterSpacing: 1,
    marginBottom: 6,
  },
  statusTitle: {
    fontSize: 32,
    fontWeight: '700',
    marginVertical: 4,
  },
  confidenceBadge: {
    backgroundColor: 'rgba(0, 242, 254, 0.12)',
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 12,
    marginTop: 8,
  },
  confidenceText: {
    fontSize: 13,
    color: MinimalismTheme.colors.accentCyan,
    fontWeight: '600',
  }
});
