/*
 * Live Monitoring Mobile Screen
 */

import React, { useState, useEffect } from 'react';
import { View, Text, ScrollView, StyleSheet, TouchableOpacity } from 'react-native';
import { MinimalismTheme } from '../theme/minimalismTheme';
import { StatusHeroCard } from '../components/StatusHeroCard';
import { MetricGrid } from '../components/MetricGrid';
import { EventCard } from '../components/EventCard';

export const LiveMonitoringScreen = () => {
  const [currentState, setCurrentState] = useState('Normal');
  const [rms, setRms] = useState(0.998);
  const [thd, setThd] = useState(0.82);
  const [confidence, setConfidence] = useState(96.3);

  const [recentEvents, setRecentEvents] = useState([
    { id: '1', timestamp: '10:14:02', predictedClass: 'Normal', rms: '0.998', thd: '0.82', duration: '0.0 ms' },
    { id: '2', timestamp: '10:13:58', predictedClass: 'Sag', rms: '0.624', thd: '1.15', duration: '45.0 ms' },
    { id: '3', timestamp: '10:13:45', predictedClass: 'Harmonics', rms: '1.050', thd: '14.8', duration: 'Continuous' },
  ]);

  const simulateDisturbance = (type) => {
    setCurrentState(type);
    let newRms = 0.998;
    let newThd = 0.82;
    let dur = '0.0 ms';

    if (type === 'Sag') { newRms = 0.624; newThd = 1.15; dur = '45.0 ms'; }
    else if (type === 'Swell') { newRms = 1.482; newThd = 1.85; dur = '60.0 ms'; }
    else if (type === 'Interruption') { newRms = 0.042; newThd = 8.50; dur = '120.0 ms'; }
    else if (type === 'Harmonics') { newRms = 1.050; newThd = 14.80; dur = 'Continuous'; }

    setRms(newRms);
    setThd(newThd);

    const newEv = {
      id: Date.now().toString(),
      timestamp: new Date().toLocaleTimeString(),
      predictedClass: type,
      rms: newRms.toFixed(3),
      thd: newThd.toFixed(2),
      duration: dur
    };

    setRecentEvents([newEv, ...recentEvents.slice(0, 4)]);
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <View style={styles.header}>
        <Text style={styles.brandTitle}>⚡ PQD Mobile</Text>
        <View style={styles.liveIndicator}>
          <View style={styles.dot} />
          <Text style={styles.liveText}>ESP32 Connected</Text>
        </View>
      </View>

      <StatusHeroCard stateName={currentState} confidence={confidence} />
      
      <MetricGrid rms={rms} thd={thd} />

      <Text style={styles.sectionTitle}>Simulate Disturbance Trigger</Text>
      <View style={styles.simButtonsRow}>
        <TouchableOpacity style={styles.btn} onPress={() => simulateDisturbance('Normal')}>
          <Text style={styles.btnText}>Normal</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.btn} onPress={() => simulateDisturbance('Sag')}>
          <Text style={styles.btnText}>Sag</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.btn} onPress={() => simulateDisturbance('Swell')}>
          <Text style={styles.btnText}>Swell</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.btn} onPress={() => simulateDisturbance('Interruption')}>
          <Text style={styles.btnText}>Interruption</Text>
        </TouchableOpacity>
      </View>

      <Text style={styles.sectionTitle}>Recent Disturbance Feed</Text>
      {recentEvents.map(ev => (
        <EventCard
          key={ev.id}
          timestamp={ev.timestamp}
          predictedClass={ev.predictedClass}
          rms={ev.rms}
          thd={ev.thd}
          duration={ev.duration}
        />
      ))}
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: MinimalismTheme.colors.bgSpace,
  },
  content: {
    padding: 16,
    paddingBottom: 32,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
    marginTop: 10,
  },
  brandTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: MinimalismTheme.colors.textMain,
  },
  liveIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    backgroundColor: 'rgba(16, 185, 129, 0.15)',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
  },
  dot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: MinimalismTheme.colors.normal,
  },
  liveText: {
    fontSize: 11,
    color: MinimalismTheme.colors.normal,
    fontWeight: '600',
  },
  sectionTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: MinimalismTheme.colors.textMuted,
    marginVertical: 12,
  },
  simButtonsRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    marginBottom: 12,
  },
  btn: {
    backgroundColor: MinimalismTheme.colors.bgCardSolid,
    borderWidth: 1,
    borderColor: MinimalismTheme.colors.borderSubtle,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 8,
  },
  btnText: {
    fontSize: 12,
    color: MinimalismTheme.colors.textMain,
    fontWeight: '500',
  }
});
