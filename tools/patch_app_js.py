"""
Script to integrate live ML classification pipeline in web/app.js.
Ensures zero emojis and clean architecture.
"""
import sys
import re

def main():
    with open('web/app.js', 'r', encoding='utf-8') as f:
        content = f.read()

    # Define the new ML classification and SSE subscription block
    new_sse_block = '''// ── Telemetry & Classification SSE Subscription (Prompt 7) ──────────────────
const CANONICAL_CLASSES = ['Flicker', 'Harmonics', 'Interruption', 'Normal', 'Notch', 'Sag', 'Swell', 'Transient'];
let _liveEvtSrc = null;
let _mlInferenceTimeline = [];
const MAX_TIMELINE_ENTRIES = 20;
let _nextInferenceTime = Date.now() + 5000;
let _lastInferenceKey = null;

function renderHeroProbBars(probs, winnerCls) {
  const container = $('ml-hero-prob-bars');
  if (!container) return;
  container.innerHTML = '';
  CANONICAL_CLASSES.forEach(cls => {
    const p = Math.max(0, Math.min(1.0, (probs && typeof probs[cls] === 'number') ? probs[cls] : 0.0));
    const pct = (p * 100).toFixed(1);
    const isWinner = (cls.toLowerCase() === (winnerCls || '').toLowerCase());

    const row = document.createElement('div');
    row.className = 'ml-prob-bar-row' + (isWinner ? ' winner' : '');
    row.innerHTML = `
      <span class="ml-prob-name" title="${cls}">${cls}</span>
      <div class="ml-bar-track">
        <div class="ml-bar-fill" style="width: ${pct}%;"></div>
      </div>
      <span class="ml-prob-pct">${pct}%</span>
    `;
    container.appendChild(row);
  });
}

function addInferenceToTimeline(pred) {
  if (!pred) return;
  const key = `${pred.run_id || ''}_${pred.inference_sequence || 0}`;
  if (_mlInferenceTimeline.some(item => `${item.run_id || ''}_${item.inference_sequence || 0}` === key)) {
    return;
  }
  _mlInferenceTimeline.unshift(pred);
  if (_mlInferenceTimeline.length > MAX_TIMELINE_ENTRIES) {
    _mlInferenceTimeline.pop();
  }
  renderTimelineTable();
}

function renderTimelineTable() {
  const tbody = $('ml-timeline-tbody');
  const countBadge = $('ml-timeline-count-badge');
  if (countBadge) {
    countBadge.textContent = `${_mlInferenceTimeline.length} record${_mlInferenceTimeline.length === 1 ? '' : 's'}`;
  }
  if (!tbody) return;
  if (_mlInferenceTimeline.length === 0) {
    tbody.innerHTML = '<tr><td colspan="9" style="text-align:center;color:#94a3b8;padding:0.75rem;">Waiting for first live simulation evaluation...</td></tr>';
    return;
  }
  tbody.innerHTML = _mlInferenceTimeline.map(item => {
    const timeStr = item.timestamp ? new Date(item.timestamp).toLocaleTimeString() : '—';
    const win = item.analysis_window ? `${item.analysis_window.simulation_time_start.toFixed(2)}s - ${item.analysis_window.simulation_time_end.toFixed(2)}s` : '—';
    const rawCls = item.raw_ml_prediction || item.predicted_class || 'Normal';
    const confStr = ((item.confidence || 0) * 100).toFixed(1) + '%';
    const physState = item.measured_physical_assessment || 'Normal';
    const physColor = physState === 'Normal' ? '#166534' : '#b91c1c';
    const sigStatus = item.signal_quality_status || 'VALID';
    const sigPillClass = sigStatus === 'VALID' ? 'status-valid' : 'status-warn';
    const domainStr = item.model_domain_status || '60 Hz NATIVE';
    const latStr = item.inference_latency_ms !== undefined ? item.inference_latency_ms.toFixed(1) + ' ms' : '—';
    return `
      <tr>
        <td>#${item.inference_sequence || 0}</td>
        <td>${timeStr}</td>
        <td>${win}</td>
        <td><strong style="color:var(--accent-primary);">${rawCls}</strong></td>
        <td>${confStr}</td>
        <td><span style="color:${physColor};font-weight:600;">${physState}</span></td>
        <td><span class="ml-lifecycle-pill ${sigPillClass}">${sigStatus}</span></td>
        <td>${domainStr}</td>
        <td>${latStr}</td>
      </tr>
    `;
  }).join('');
}

function toggleTimelineExpand() {
  const content = $('ml-timeline-content');
  const lbl = $('ml-timeline-toggle-lbl');
  if (!content) return;
  const isHidden = (content.style.display === 'none' || !content.style.display);
  content.style.display = isHidden ? 'block' : 'none';
  if (lbl) {
    lbl.textContent = isHidden ? 'HIDE TABLE' : 'SHOW TABLE';
  }
}
window.toggleTimelineExpand = toggleTimelineExpand;

function handleLiveClassificationEvent(pred) {
  if (!pred) return;

  _nextInferenceTime = Date.now() + 5000;

  const predCls = pred.predicted_class || pred.raw_ml_prediction || 'Normal';
  const rawPredCls = pred.raw_ml_prediction || predCls;
  const confVal = pred.confidence !== undefined ? pred.confidence : 0.0;

  // 1. Hero Card A: Predicted Class & Confidence
  const heroPredEl = $('ml-hero-pred-class');
  if (heroPredEl) {
    heroPredEl.textContent = rawPredCls.toUpperCase();
    heroPredEl.className = 'ml-class-huge class-' + rawPredCls;
  }

  const heroConfEl = $('ml-hero-pred-conf');
  if (heroConfEl) {
    heroConfEl.textContent = (confVal * 100).toFixed(1) + '%';
  }

  const heroStatusEl = $('ml-hero-status-lbl');
  if (heroStatusEl) {
    heroStatusEl.textContent = pred.prediction_status || 'VALID';
  }

  const heroLastEvalEl = $('ml-hero-last-eval-lbl');
  if (heroLastEvalEl) {
    heroLastEvalEl.textContent = pred.timestamp ? new Date(pred.timestamp).toLocaleTimeString() : '—';
  }

  const heroLatEl = $('ml-hero-latency-lbl');
  if (heroLatEl) {
    heroLatEl.textContent = pred.inference_latency_ms !== undefined ? (pred.inference_latency_ms.toFixed(1) + ' ms') : '—';
  }

  const heroWinEl = $('ml-hero-window-lbl');
  if (heroWinEl) {
    if (pred.analysis_window) {
      const cnt = pred.analysis_window.sample_count || 1000;
      const dur = (cnt / 5000).toFixed(2);
      const t0 = pred.analysis_window.simulation_time_start !== undefined ? pred.analysis_window.simulation_time_start.toFixed(2) : '0.00';
      const t1 = pred.analysis_window.simulation_time_end !== undefined ? pred.analysis_window.simulation_time_end.toFixed(2) : dur;
      heroWinEl.textContent = `${cnt} samples [${t0}s - ${t1}s] (${dur} s @ 5 kHz)`;
    } else {
      heroWinEl.textContent = '1000 samples (0.20 s @ 5 kHz)';
    }
  }

  // 2. Hero Card B: 8-Class Probability Bars
  const probs = pred.raw_ml_probabilities || pred.probabilities;
  renderHeroProbBars(probs, rawPredCls);

  // 3. Hero Card C: Three Separate Results
  const cmdBadge = $('triplet-cmd-badge');
  if (cmdBadge) {
    const cmd = pred.command_status || 'IDLE';
    cmdBadge.textContent = cmd;
    cmdBadge.style.background = cmd === 'APPLIED' ? '#dcfce7' : (cmd === 'RESET' ? '#dbeafe' : '#f1f5f9');
    cmdBadge.style.color = cmd === 'APPLIED' ? '#166534' : (cmd === 'RESET' ? '#1e40af' : '#475569');
  }

  const reqVal = $('triplet-req-val');
  if (reqVal) {
    reqVal.textContent = pred.requested_disturbance || 'Normal';
  }

  const recBadge = $('triplet-rec-badge');
  if (recBadge) {
    const rec = pred.recovery_status || pred.active_physical_state || 'NORMAL';
    recBadge.textContent = rec;
    recBadge.style.background = rec === 'NORMAL' ? '#dbeafe' : '#fee2e2';
    recBadge.style.color = rec === 'NORMAL' ? '#1e40af' : '#991b1b';
  }

  const physVal = $('triplet-phys-val');
  if (physVal) {
    const phys = pred.measured_physical_assessment || 'Normal';
    physVal.textContent = phys;
    physVal.style.color = phys === 'Normal' ? '#166534' : '#dc2626';
  }

  const mlBadge = $('triplet-ml-badge');
  if (mlBadge) {
    mlBadge.textContent = pred.model_domain_status || '60 Hz NATIVE';
  }

  const mlVal = $('triplet-ml-val');
  if (mlVal) {
    mlVal.textContent = rawPredCls;
    mlVal.style.color = 'var(--accent-primary)';
  }

  const mlConfSub = $('triplet-ml-conf-sub');
  if (mlConfSub) {
    mlConfSub.textContent = (confVal * 100).toFixed(1) + '%';
  }

  // 4. Hero Header Badges
  const sigBadge = $('ml-signal-quality-badge');
  if (sigBadge) {
    const sig = pred.signal_quality_status || 'VALID';
    sigBadge.textContent = 'SIGNAL: ' + sig;
    sigBadge.className = 'ml-lifecycle-pill ' + (sig === 'VALID' ? 'status-valid' : 'status-warn');
  }

  const domBadge = $('ml-model-domain-badge');
  if (domBadge) {
    const dom = pred.model_domain_status || '60 Hz NATIVE';
    domBadge.textContent = 'DOMAIN: ' + dom;
    domBadge.className = 'ml-lifecycle-pill ' + (dom.includes('OUT_OF_RANGE') ? 'status-oor' : 'status-valid');
  }

  // 5. Timeline Table
  if (pred.inference_sequence !== undefined && pred.inference_sequence !== null) {
    addInferenceToTimeline(pred);
  }

  // 6. Overview Dashboard Synchronization
  if ($('ov-pred-class')) $('ov-pred-class').textContent = rawPredCls.toUpperCase();
  if ($('ov-pred-conf')) $('ov-pred-conf').textContent = ((confVal * 100).toFixed(1)) + '%';
  if (pred.requested_disturbance && $('ov-req-dist')) $('ov-req-dist').textContent = pred.requested_disturbance;
  if (pred.measured_physical_assessment && $('ov-active-phys')) {
    $('ov-active-phys').textContent = pred.measured_physical_assessment;
    $('ov-active-phys').style.color = (pred.measured_physical_assessment === 'Normal') ? '#166534' : '#dc2626';
  }
  if (pred.recovery_status && $('ov-rec-status')) $('ov-rec-status').textContent = pred.recovery_status;
}

function handleLiveTelemetryEvent(telem) {
  if (!telem) return;
  if (!LIVE_SIM.activeRunId && telem.run_id) {
    LIVE_SIM.activeRunId = telem.run_id;
  }

  const wf = telem.waveforms || telem.waveform;
  if (wf && wf.L1 && wf.L1.length > 0) {
    ['L1', 'L2', 'L3'].forEach(p => {
      if (wf[p]) {
        if (!LIVE_SIM.streamBuffer[p]) LIVE_SIM.streamBuffer[p] = [];
        LIVE_SIM.streamBuffer[p].push(...wf[p]);
        if (LIVE_SIM.streamBuffer[p].length > MAX_LIVE_SAMPLES) {
          LIVE_SIM.streamBuffer[p] = LIVE_SIM.streamBuffer[p].slice(-MAX_LIVE_SAMPLES);
        }
      }
    });
    drawLiveWaveform('live-voltage-canvas', LIVE_SIM.streamBuffer, 'live-v-samples');
  }

  const ci = telem.current_waveforms || telem.current_waveform || telem.currents;
  if (ci && ci.L1 && ci.L1.length > 0) {
    ['L1', 'L2', 'L3'].forEach(p => {
      if (ci[p]) {
        if (!LIVE_SIM.currentBuffer[p]) LIVE_SIM.currentBuffer[p] = [];
        LIVE_SIM.currentBuffer[p].push(...ci[p]);
        if (LIVE_SIM.currentBuffer[p].length > MAX_LIVE_SAMPLES) {
          LIVE_SIM.currentBuffer[p] = LIVE_SIM.currentBuffer[p].slice(-MAX_LIVE_SAMPLES);
        }
      }
    });
    drawLiveWaveform('live-current-canvas', LIVE_SIM.currentBuffer, 'live-i-samples');
  }

  updateLiveMetrics(telem);
  if (typeof drawLiveFFTSpectrum === 'function') drawLiveFFTSpectrum();
}

function handleLiveStatusEvent(status) {
  if (!status) return;
  updateSimStatusUI(status);

  const lifeBadge = $('ml-lifecycle-badge');
  if (lifeBadge) {
    if (status.status === 'idle') {
      lifeBadge.textContent = 'STATUS: WAITING FOR SIMULATION';
      lifeBadge.className = 'ml-lifecycle-pill status-idle';
    } else if (status.status === 'starting') {
      lifeBadge.textContent = 'STATUS: INITIALIZING SIGNAL ACQUISITION';
      lifeBadge.className = 'ml-lifecycle-pill status-init';
    } else if (status.status === 'streaming' || status.status === 'running') {
      lifeBadge.textContent = 'STATUS: CONTINUOUS SIMULATION ACTIVE';
      lifeBadge.className = 'ml-lifecycle-pill status-live';
    } else if (status.status === 'stopped' || status.status === 'completed') {
      lifeBadge.textContent = 'STATUS: SIMULATION STOPPED';
      lifeBadge.className = 'ml-lifecycle-pill status-stopped';
    } else if (status.status === 'error') {
      lifeBadge.textContent = 'STATUS: ERROR';
      lifeBadge.className = 'ml-lifecycle-pill status-warn';
    }
  }

  if (status.prediction) {
    handleLiveClassificationEvent(status.prediction);
  }
}

async function fetchLatestPrediction() {
  try {
    const res = await fetch('/api/live/simulation/prediction');
    if (!res.ok) return;
    const pred = await res.json();
    if (pred && (pred.prediction_status === 'VALID' || pred.predicted_class || pred.raw_ml_prediction)) {
      handleLiveClassificationEvent(pred);
    }
  } catch (_) {}
}

function subscribeLiveTelemetry() {
  if (_liveEvtSrc) { _liveEvtSrc.close(); }
  _liveEvtSrc = new EventSource('/api/live/simulation/stream');

  _liveEvtSrc.addEventListener('classification', (ev) => {
    try {
      const pred = JSON.parse(ev.data);
      handleLiveClassificationEvent(pred);
    } catch (e) {
      console.warn('Error parsing classification SSE:', e);
    }
  });

  _liveEvtSrc.addEventListener('telemetry', (ev) => {
    try {
      const telem = JSON.parse(ev.data);
      handleLiveTelemetryEvent(telem);
    } catch (e) {
      console.warn('Error parsing telemetry SSE:', e);
    }
  });

  _liveEvtSrc.addEventListener('status', (ev) => {
    try {
      const status = JSON.parse(ev.data);
      handleLiveStatusEvent(status);
    } catch (e) {
      console.warn('Error parsing status SSE:', e);
    }
  });

  _liveEvtSrc.onmessage = (ev) => {
    try {
      const payload = JSON.parse(ev.data);
      if (payload.status !== undefined) {
        handleLiveStatusEvent(payload);
      } else if (payload.raw_ml_prediction !== undefined || payload.predicted_class !== undefined) {
        handleLiveClassificationEvent(payload);
      } else if (payload.waveforms || payload.waveform || payload.rms_voltage !== undefined) {
        handleLiveTelemetryEvent(payload);
      }
    } catch (_) {}
  };

  _liveEvtSrc.onerror = (err) => {
    console.warn('Live SSE stream reconnecting...');
  };
}

// Global monotonic countdown tick for hero panel
setInterval(() => {
  const el = $('ml-hero-countdown-lbl');
  if (el) {
    const diff = Math.max(0, (_nextInferenceTime - Date.now()) / 1000);
    el.textContent = (diff < 10 ? '0' : '') + diff.toFixed(1) + ' s';
  }
}, 100);
'''

    # Pattern for the old subscribeLiveTelemetry
    pattern_old_sub = r'// ── Telemetry SSE subscription ──+[\s\S]*?function subscribeLiveTelemetry\(\)\s*\{[\s\S]*?\}\s*\}'
    if not re.search(pattern_old_sub, content):
        print("ERROR: Could not locate old subscribeLiveTelemetry in web/app.js")
        sys.exit(1)

    content = re.sub(pattern_old_sub, new_sse_block, content, count=1)

    # In displayLivePrediction, also pass through to handleLiveClassificationEvent
    pattern_disp = r'(function displayLivePrediction\(result\)\s*\{[\s\S]*?if \(!result\) return;)'
    replacement_disp = r'\1\n  if (result.raw_ml_prediction || result.predicted_class || result.raw_ml_probabilities) {\n    handleLiveClassificationEvent(result);\n  }'
    content = re.sub(pattern_disp, replacement_disp, content, count=1)

    # In switchPage, add fetchLatestPrediction() when pageId === 'live-simulink'
    pattern_switch = r"(else if \(pageId === 'live-simulink'\) \{[\s\S]*?drawLiveFFTSpectrum\(\);)"
    replacement_switch = r"\1\n    fetchLatestPrediction();"
    content = re.sub(pattern_switch, replacement_switch, content, count=1)

    # In DOMContentLoaded, call renderHeroProbBars({}, 'Normal') and fetchLatestPrediction()
    pattern_dom = r'(clearLiveCanvases\(\);)'
    replacement_dom = r"\1\n  renderHeroProbBars({}, 'Normal');\n  fetchLatestPrediction();"
    content = re.sub(pattern_dom, replacement_dom, content, count=1)

    with open('web/app.js', 'w', encoding='utf-8') as f:
        f.write(content)
    print("SUCCESS: web/app.js updated successfully.")

if __name__ == '__main__':
    main()
