import os

app_js_path = os.path.join("web", "app.js")
with open(app_js_path, "r", encoding="utf-8") as f:
    code = f.read()

# 1. Update LIVE_SIM state
old_state = """// ── State ──────────────────────────────────────────────────────────────────
const LIVE_SIM = {
  mode:           'manual', // 'manual' | 'scheduled'
  selectedClass:  'Normal',
  statusPollId:   null,
  streamBuffer:   { L1: [], L2: [], L3: [] },
  currentBuffer:  { L1: [], L2: [], L3: [] },
  telSubbed:      false,
  activeRunId:    null,
  onsetTime:      0.12,
  samplingRate:   5000,
  lastStatus:     'idle',
};

function setLiveMode(mode) {
  LIVE_SIM.mode = mode;
  const mBtn = $('btn-mode-manual');
  const sBtn = $('btn-mode-scheduled');
  if (mBtn) mBtn.classList.toggle('active', mode === 'manual');
  if (sBtn) sBtn.classList.toggle('active', mode === 'scheduled');
  liveLog(`Execution mode set to: ${mode === 'manual' ? 'Live Manual Injection' : 'Scheduled Scenario'}`, 'info');
}"""

new_state = """// ── State ──────────────────────────────────────────────────────────────────
const LIVE_SIM = {
  mode:           'continuous', // 'continuous' | 'scheduled'
  selectedClass:  'Normal',
  statusPollId:   null,
  streamBuffer:   { L1: [], L2: [], L3: [] },
  currentBuffer:  { L1: [], L2: [], L3: [] },
  telSubbed:      false,
  activeRunId:    null,
  onsetTime:      0.12,
  samplingRate:   5000,
  lastStatus:     'idle',
};

function setLiveMode(mode) {
  LIVE_SIM.mode = mode;
  const cBtn = $('btn-mode-continuous');
  const sBtn = $('btn-mode-scheduled');
  if (cBtn) cBtn.classList.toggle('active', mode === 'continuous');
  if (sBtn) sBtn.classList.toggle('active', mode === 'scheduled');
  liveLog(`Execution mode: ${mode === 'continuous' ? 'Continuous Interactive SIL' : 'Scheduled Scenario'}`, 'info');
}"""

code = code.replace(old_state.replace('\n', '\r\n'), new_state.replace('\n', '\r\n'))
code = code.replace(old_state, new_state)

# 2. Update default buildSimConfig mode
code = code.replace("const mode = LIVE_SIM.mode || 'manual';", "const mode = LIVE_SIM.mode || 'continuous';")

# 3. Update subscribeLiveTelemetry to incrementally append to circular stream buffer
old_sub = """function subscribeLiveTelemetry() {
  if (_liveEvtSrc) { _liveEvtSrc.close(); }
  _liveEvtSrc = new EventSource('/api/stream/telemetry');
  _liveEvtSrc.onmessage = (ev) => {
    try {
      const telem = JSON.parse(ev.data);
      if (!LIVE_SIM.activeRunId) return;

      const wf = telem.waveforms || telem.waveform;
      if (wf && wf.L1 && wf.L1.length > 0) {
        LIVE_SIM.streamBuffer = wf;
        drawLiveWaveform('live-voltage-canvas', LIVE_SIM.streamBuffer, 'live-v-samples');
      }
      const ci = telem.current_waveforms || telem.current_waveform || telem.currents;
      if (ci && ci.L1 && ci.L1.length > 0) {
        LIVE_SIM.currentBuffer = ci;
        drawLiveWaveform('live-current-canvas', LIVE_SIM.currentBuffer, 'live-i-samples');
      }

      updateLiveMetrics(telem);
    } catch (_) {}
  };
}"""

new_sub = """function subscribeLiveTelemetry() {
  if (_liveEvtSrc) { _liveEvtSrc.close(); }
  _liveEvtSrc = new EventSource('/api/stream/telemetry');
  _liveEvtSrc.onmessage = (ev) => {
    try {
      const telem = JSON.parse(ev.data);
      if (!LIVE_SIM.activeRunId) return;

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
    } catch (_) {}
  };
}"""

code = code.replace(old_sub.replace('\n', '\r\n'), new_sub.replace('\n', '\r\n'))
code = code.replace(old_sub, new_sub)

# 4. Update status polling & live prediction card rendering
old_pred_ui = """function displayLivePrediction(result) {
  if (!result || !result.predicted_class) return;
  const predEl   = $('live-pred-class');
  const confEl   = $('live-pred-conf');
  const mlPanel  = $('live-ml-prediction');
  const reqEl    = $('live-requested-dist');
  const physEl   = $('live-phys-assess');
  const domainEl = $('live-domain-status');

  if (predEl)  predEl.textContent  = result.predicted_class;
  if (confEl)  confEl.textContent  = ((result.confidence || 0) * 100).toFixed(1) + '%';
  if (reqEl && result.requested_disturbance) reqEl.textContent = result.requested_disturbance;
  if (physEl && result.measured_physical_assessment) {
    physEl.textContent = result.measured_physical_assessment;
    physEl.style.color = result.measured_physical_assessment === 'Normal' ? '#166534' : '#dc2626';
  }
  if (domainEl && result.model_domain_status) {
    domainEl.textContent = result.model_domain_status === 'MODEL_COMPATIBLE' ? '60 Hz → 50 Hz Space' : result.model_domain_status;
  }
  if (mlPanel) mlPanel.style.display = 'block';
}"""

new_pred_ui = """function displayLivePrediction(result) {
  if (!result) return;
  const predCls  = result.raw_ml_prediction || result.predicted_class || 'Normal';
  const confVal  = result.confidence !== undefined ? result.confidence : 0.999;
  const predEl   = $('live-pred-class');
  const confEl   = $('live-pred-conf');
  const mlPanel  = $('live-ml-prediction');
  const reqEl    = $('live-requested-dist');
  const physEl   = $('live-phys-assess');
  const domainEl = $('live-domain-status');
  const cmdEl    = $('live-cmd-status');
  const sigEl    = $('live-signal-quality');
  const cntEl    = $('live-countdown');

  if (predEl)  predEl.textContent = predCls;
  if (confEl)  confEl.textContent = (confVal * 100).toFixed(1) + '%';
  if (reqEl && result.requested_disturbance) reqEl.textContent = result.requested_disturbance;
  if (physEl && result.measured_physical_assessment) {
    physEl.textContent = result.measured_physical_assessment;
    physEl.style.color = result.measured_physical_assessment === 'Normal' ? '#166534' : '#dc2626';
  }
  if (domainEl && result.model_domain_status) {
    domainEl.textContent = result.model_domain_status === 'MODEL_COMPATIBLE' ? '60 Hz → 50 Hz Space' : result.model_domain_status;
  }
  if (cmdEl && result.command_status) {
    cmdEl.textContent = result.command_status;
    cmdEl.style.background = result.command_status === 'APPLIED' ? '#dcfce7' : (result.command_status === 'RESET' ? '#dbeafe' : '#f1f5f9');
    cmdEl.style.color = result.command_status === 'APPLIED' ? '#166534' : (result.command_status === 'RESET' ? '#1d4ed8' : '#475569');
  }
  if (sigEl && result.signal_quality_status) {
    sigEl.textContent = result.signal_quality_status;
    sigEl.style.color = result.signal_quality_status === 'VALID' ? '#166534' : '#dc2626';
  }
  if (cntEl && result.countdown_s !== undefined) {
    cntEl.textContent = result.countdown_s + ' s';
  }

  // Render 8-class probability bars
  const probs = result.raw_ml_probabilities || (result.prediction && result.prediction.raw_ml_probabilities) || result.probabilities;
  const barsContainer = $('live-prob-bars');
  if (barsContainer && probs && typeof probs === 'object') {
    const classes = ['Normal', 'Sag', 'Swell', 'Interruption', 'Harmonics', 'Flicker', 'Notch', 'Transient'];
    barsContainer.innerHTML = '';
    classes.forEach(c => {
      const p = Math.max(0, Math.min(1.0, probs[c] || 0.0));
      const pct = (p * 100).toFixed(1);
      const isWinner = (c === predCls);
      const barDiv = document.createElement('div');
      barDiv.style.background = isWinner ? '#e0f2fe' : '#f8fafc';
      barDiv.style.border = isWinner ? '1px solid #38bdf8' : '1px solid #e2e8f0';
      barDiv.style.borderRadius = '4px';
      barDiv.style.padding = '0.2rem 0.35rem';
      barDiv.style.fontSize = '0.62rem';
      barDiv.innerHTML = `
        <div style="display:flex;justify-content:space-between;margin-bottom:0.15rem;">
          <span style="font-weight:${isWinner?'700':'500'};color:${isWinner?'#0369a1':'#475569'};">${c}</span>
          <span style="font-family:monospace;color:${isWinner?'#0284c7':'#64748b'};">${pct}%</span>
        </div>
        <div style="height:3px;background:#e2e8f0;border-radius:2px;overflow:hidden;">
          <div style="width:${pct}%;height:100%;background:${isWinner?'#0284c7':'#94a3b8'};"></div>
        </div>
      `;
      barsContainer.appendChild(barDiv);
    });
  }

  if (mlPanel) mlPanel.style.display = 'block';
}"""

code = code.replace(old_pred_ui.replace('\n', '\r\n'), new_pred_ui.replace('\n', '\r\n'))
code = code.replace(old_pred_ui, new_pred_ui)

# 5. In updateSimStatusUI: pass entire status 's' to displayLivePrediction
old_status_call = """  if (s.prediction && s.prediction.predicted_class) {
    displayLivePrediction(s.prediction);
  }"""

new_status_call = """  displayLivePrediction(s);"""
code = code.replace(old_status_call.replace('\n', '\r\n'), new_status_call.replace('\n', '\r\n'))
code = code.replace(old_status_call, new_status_call)

with open(app_js_path, "w", encoding="utf-8") as f:
    f.write(code)

print("Updated app.js successfully!")

