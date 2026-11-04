import os

index_path = os.path.join("web", "index.html")
with open(index_path, "r", encoding="utf-8") as f:
    html = f.read()

# 1. Update Mode Selector
old_mode = """          <!-- Execution Mode selector -->
          <div class="ctrl-group">
            <div class="ctrl-label">EXECUTION MODE</div>
            <div style="display:flex;gap:0.4rem;">
              <button class="mode-btn active" id="btn-mode-manual" onclick="setLiveMode('manual')">Live Manual Injection</button>
              <button class="mode-btn" id="btn-mode-scheduled" onclick="setLiveMode('scheduled')">Scheduled Scenario</button>
            </div>
          </div>"""

new_mode = """          <!-- Execution Mode selector -->
          <div class="ctrl-group">
            <div class="ctrl-label">EXECUTION MODE</div>
            <div style="display:flex;gap:0.4rem;">
              <button class="mode-btn active" id="btn-mode-continuous" onclick="setLiveMode('continuous')">Continuous Interactive SIL</button>
              <button class="mode-btn" id="btn-mode-scheduled" onclick="setLiveMode('scheduled')">Scheduled Scenario</button>
            </div>
          </div>"""

html = html.replace(old_mode.replace('\n', '\r\n'), new_mode.replace('\n', '\r\n'))

# 2. Update ML Status Card
old_card = """          <!-- Independent Disturbance Assessment & ML Prediction Card -->
          <div class="ctrl-group" id="live-ml-prediction" style="display:none;background:#f8fafc;border:1.5px solid var(--border-card);border-radius:8px;padding:0.75rem;">
            <div style="font-size:0.68rem;font-weight:800;color:#475569;margin-bottom:0.5rem;letter-spacing:0.04em;text-transform:uppercase;">Demonstration Assessment & ML Status</div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.6rem;font-size:0.75rem;">
              <div>
                <span style="color:#64748b;display:block;font-size:0.65rem;">Requested Disturbance</span>
                <strong id="live-requested-dist" style="color:#1e293b;font-size:0.78rem;">Normal</strong>
              </div>
              <div>
                <span style="color:#64748b;display:block;font-size:0.65rem;">Physical Assessment (IEEE 1159)</span>
                <strong id="live-phys-assess" style="color:var(--accent-primary);font-size:0.78rem;">Normal</strong>
              </div>
              <div>
                <span style="color:#64748b;display:block;font-size:0.65rem;">Independent ML Prediction</span>
                <div style="display:flex;align-items:center;gap:0.35rem;margin-top:0.15rem;">
                  <span class="val-value-badge badge-predicted" id="live-pred-class" style="font-size:0.75rem;padding:0.15rem 0.45rem;">—</span>
                  <span style="font-family:var(--font-mono);font-size:0.75rem;color:var(--accent-success);" id="live-pred-conf">—</span>
                </div>
              </div>
              <div>
                <span style="color:#64748b;display:block;font-size:0.65rem;">Domain Adaptation</span>
                <span id="live-domain-status" style="font-size:0.7rem;color:#166534;font-weight:700;">60 Hz → 50 Hz Space</span>
              </div>
            </div>
          </div>"""

new_card = """          <!-- Independent Disturbance Assessment & ML Prediction Card -->
          <div class="ctrl-group" id="live-ml-prediction" style="display:block;background:#f8fafc;border:1.5px solid var(--border-card);border-radius:8px;padding:0.75rem;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.5rem;">
              <span style="font-size:0.68rem;font-weight:800;color:#475569;letter-spacing:0.04em;text-transform:uppercase;">Demonstration Assessment & ML Status</span>
              <span style="font-size:0.68rem;color:#2563eb;font-weight:700;">Next eval: <strong id="live-countdown">5 s</strong></span>
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.6rem;font-size:0.75rem;">
              <div>
                <span style="color:#64748b;display:block;font-size:0.65rem;">Requested Disturbance</span>
                <strong id="live-requested-dist" style="color:#1e293b;font-size:0.78rem;">Normal</strong>
                <span id="live-cmd-status" style="display:inline-block;margin-left:0.25rem;font-size:0.62rem;font-weight:700;color:#166534;background:#dcfce7;padding:0.05rem 0.3rem;border-radius:3px;">IDLE</span>
              </div>
              <div>
                <span style="color:#64748b;display:block;font-size:0.65rem;">Physical Assessment (IEEE 1159)</span>
                <strong id="live-phys-assess" style="color:var(--accent-primary);font-size:0.78rem;">Normal</strong>
              </div>
              <div>
                <span style="color:#64748b;display:block;font-size:0.65rem;">Independent ML Prediction</span>
                <div style="display:flex;align-items:center;gap:0.35rem;margin-top:0.15rem;">
                  <span class="val-value-badge badge-predicted" id="live-pred-class" style="font-size:0.75rem;padding:0.15rem 0.45rem;">Normal</span>
                  <span style="font-family:var(--font-mono);font-size:0.75rem;color:var(--accent-success);" id="live-pred-conf">99.9%</span>
                </div>
              </div>
              <div>
                <span style="color:#64748b;display:block;font-size:0.65rem;">Signal Quality</span>
                <span id="live-signal-quality" style="font-size:0.7rem;color:#166534;font-weight:700;">VALID (Bus 5 3-Phase)</span>
              </div>
              <div style="grid-column:1 / -1;">
                <div style="display:flex;justify-content:space-between;font-size:0.65rem;color:#64748b;margin-bottom:0.25rem;">
                  <span>ML Probabilities (8-Class Inference)</span>
                  <span id="live-domain-status" style="color:#166534;font-weight:600;">60 Hz → 50 Hz Space</span>
                </div>
                <div id="live-prob-bars" style="display:grid;grid-template-columns:repeat(4, 1fr);gap:0.35rem;">
                </div>
              </div>
            </div>
          </div>"""

html = html.replace(old_card.replace('\n', '\r\n'), new_card.replace('\n', '\r\n'))

with open(index_path, "w", encoding="utf-8") as f:
    f.write(html)

print("Updated index.html successfully!")

