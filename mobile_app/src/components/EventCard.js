/*
 * Event Card Item Component for Mobile App
 */

import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { MinimalismTheme } from '../theme/minimalismTheme';

export const EventCard = ({ timestamp, predictedClass, rms, thd, duration }) => {
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

  const badgeColor = getBadgeColor(predictedClass);

  return (
    <View style={styles.card}>
      <View style={styles.headerRow}>
        <View style={[styles.badge, { backgroundColor: badgeColor + '20' }]}>
          <Text style={[styles.badgeText, { color: badgeColor }]}>{predictedClass}</Text>
        </View>
        <Text style={styles.timeText}>{timestamp}</Text>
      </View>

      <Text style={styles.detailsText}>
        RMS: {rms} pu  |  THD: {thd}%  |  Duration: {duration}
      </Text>
    </View>
  );
};

const styles = StyleSheet.create({
  card: {
    backgroundColor: MinimalismTheme.colors.bgCardSolid,
    borderRadius: MinimalismTheme.borderRadius.md,
    padding: 12,
    marginBottom: 8,
    borderWidth: 1,
    borderColor: MinimalismTheme.colors.borderSubtle,
  },
  headerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 6,
  },
  badge: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
  },
  badgeText: {
    fontSize: 12,
    fontWeight: '700',
  },
  timeText: {
    fontSize: 11,
    color: MinimalismTheme.colors.textDim,
  },
  detailsText: {
    fontSize: 12,
    color: MinimalismTheme.colors.textMuted,
  }
});
