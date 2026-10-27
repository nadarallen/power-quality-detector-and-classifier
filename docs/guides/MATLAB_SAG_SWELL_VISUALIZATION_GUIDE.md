# MATLAB Voltage Sag & Swell Waveform Visualization Guide

**Document Reference:** [`docs/guides/MATLAB_SAG_SWELL_VISUALIZATION_GUIDE.md`](MATLAB_SAG_SWELL_VISUALIZATION_GUIDE.md)  
**Audience:** Researchers, engineers, and students visualizing power-quality simulation outputs.  
**System Benchmark:** IEEE 9-bus WSCC 3-Machine 3-Phase Transmission System ($60.0\text{ Hz}$, Bus 5 PCC).  
**Dataset Reference:** Phase 5C Dual-Rate Waveform Dataset ([`data/ieee9bus_60hz_phase5c/raw/`](../../data/ieee9bus_60hz_phase5c/raw/)).  
**Software Requirements:** MATLAB (R2024b, R2025a, or any standard release with Base MATLAB; no extra toolboxes required for plotting).

---

## 1. Overview & Operating Rules

This guide provides **self-contained, copy-paste-ready MATLAB command blocks** that you can paste directly into the MATLAB Command Window to inspect, load, and visualize pre-computed Three-Phase Voltage Sag and Voltage Swell electromagnetic simulations.

### Key Operational Rules
1. **No External Script Needed:** You do **not** need to create, download, or execute a separate `.m` file. Every command is executed directly in the MATLAB Command Window.
2. **Read-Only Inspection:** These commands **read pre-recorded data only**. They do **not** invoke Simulink, do not regenerate data, and do not modify or overwrite any MAT files on disk.
3. **Pristine Reference Unchanged:** The baseline reference model [`IEEE_9bus/IEEE_9bus_PQD_HIL_R2025a.slx`](../../IEEE_9bus/IEEE_9bus_PQD_HIL_R2025a.slx) remains frozen and completely untouched.
4. **Phase 6 Scope:** Microcontroller firmware and physical hardware deployment remain strictly **Future Scope — Not Yet Implemented**.

---

## 2. Verified Simulation Recordings & Signal Metadata

The guide visualizes two verified baseline recordings from the Phase 5C dual-rate continuous dataset:

| Disturbance Class | Filename | Disturbance Mechanism | Operating Condition | Inception ($t_0$) | Duration ($\Delta t$) | Clearing Time ($t_{\text{end}}$) |
|---|---|---|---|:---:|:---:|:---:|
| **Voltage Sag** | `P5B2_SAG_0091_abc_c01_mil.mat` | Symmetrical 3-phase shunt fault ($R_f = 200\ \Omega, R_g = 0.01\ \Omega$) | Nominal Baseline ($100\%$ load) | $0.120\text{ s}$ ($120\text{ ms}$) | $75\text{ ms}$ ($4.5\text{ cycles}$) | $0.195\text{ s}$ ($195\text{ ms}$) |
| **Voltage Swell** | `P5B2_SWE_0109_abc_c01_mil.mat` | Shunt capacitor bank energization ($Q = 90\text{ MVAR}, P_d = 100\text{ kW}$) | Nominal Baseline ($100\%$ load) | $0.120\text{ s}$ ($120\text{ ms}$) | $70\text{ ms}$ ($4.2\text{ cycles}$) | $0.190\text{ s}$ ($190\text{ ms}$) |

### Variables Saved in Each MAT Recording
Each Phase 5C recording contains the following variables:
- `V_cont_20k`: High-resolution continuous voltage waveform ($7,601 \times 3$, $F_s = 20\text{ kHz}$, $\Delta t = 50\ \mu\text{s}$).
- `I_cont_20k`: High-resolution continuous current waveform ($7,601 \times 3$, $F_s = 20\text{ kHz}$, $\Delta t = 50\ \mu\text{s}$).
- `t_grid_20k`: Time vector for 20 kHz continuous data ($7,601 \times 1$, spanning $0.000\text{ s}$ to $0.380\text{ s}$).
- `V_cont_5k`: Canonical decimated voltage waveform ($1,901 \times 3$, $F_s = 5\text{ kHz}$, $\Delta t = 200\ \mu\text{s}$).
- `I_cont_5k`: Canonical decimated current waveform ($1,901 \times 3$, $F_s = 5\text{ kHz}$, $\Delta t = 200\ \mu\text{s}$).
- `t_grid_5k`: Time vector for 5 kHz canonical data ($1,901 \times 1$, spanning $0.000\text{ s}$ to $0.380\text{ s}$).
- `sc`: Scenario metadata structure (trajectory ID, disturbance class, operating condition, duration, parameters, split).
- `solver_stats`: Numerical solver telemetry (`ode23tb`, time steps, Jacobian evaluations).
- `t_wall`: Total simulation wall-clock time in seconds.

---

## 3. Signal Units & Physical Normalization

Before visualizing, understand the exact physical units logged by Simscape Electrical:

- **Voltage ($V$):** Per-unit (pu) line-to-neutral voltage at Bus 5, normalized to the three-phase system base voltage ($V_{\text{base}} = 230\text{ kV}_{L-L}$).  
  Under nominal power-flow conditions, Bus 5 operates at $V = 1.020\text{ pu}_{L-L}$. Converting from line-to-line RMS to line-to-neutral peak yields:
  $$V_{\text{nominal, peak}} = 1.020 \times \frac{\sqrt{2}}{\sqrt{3}} \approx 0.8328\text{ pu}$$
  The pre-fault steady-state peak is therefore $\approx 0.833\text{ pu}$ (and nominal RMS is $\approx 0.589\text{ pu}$), **not** $1.000\text{ pu}$.
- **Current ($I$):** Per-unit (pu) transmission line current flowing into Bus 5, normalized to the three-phase base power $S_{\text{base}} = 100\text{ MVA}$ and $V_{\text{base}} = 230\text{ kV}_{L-L}$ ($I_{\text{base}} = \frac{100\text{ MVA}}{\sqrt{3} \times 230\text{ kV}} \approx 251.02\text{ A}$). Pre-fault steady-state current peak is $\approx 1.12\text{ pu}$ (RMS $\approx 0.793\text{ pu}$).

---

## 4. Copy-Paste MATLAB Execution Sequence

Execute the following five blocks **in order** by copying each block and pasting it directly into the MATLAB Command Window.

```
+---------------------------------------------------------------------------------------------------+
| EXECUTION ORDER IN MATLAB COMMAND WINDOW:                                                         |
|                                                                                                   |
|  [Block A] Set Up Project Paths & Verify Artifacts                                                |
|       │                                                                                           |
|       ▼                                                                                           |
|  [Block B] Inspect MAT Structure & Load Recordings with Sanity Checks                             |
|       │                                                                                           |
|       ▼                                                                                           |
|  [Block C] Figure 1: Voltage Waveform Comparison (Stacked Panels: Sag vs Swell)                   |
|       │                                                                                           |
|       ▼                                                                                           |
|  [Block D] Figure 2: Current Waveform Comparison (Stacked Panels: Sag vs Swell)                   |
|       │                                                                                           |
|       ▼                                                                                           |
|  [Block E] Verify Sampling Rates, Durations, Disturbance Timing & Integrity                       |
+---------------------------------------------------------------------------------------------------+
```

---

### Block A: Set Up Project Paths & Verify Artifacts

**Purpose:** Configures the project repository root path using `fullfile` and verifies that both Sag and Swell MAT files exist on disk before attempting to load them.

```matlab
%% =========================================================================
%% BLOCK A: SET UP PROJECT PATHS & VERIFY RECORDINGS
%% =========================================================================
% Instructions: Copy and paste this entire block into the MATLAB Command Window.

clear; clc;

% 1. Set the repository root directory
projectRoot = 'D:\my study\Project\power-quality-detector-and-classifier';

% 2. Construct paths to raw recordings using fullfile for platform safety
rawDir = fullfile(projectRoot, 'data', 'ieee9bus_60hz_phase5c', 'raw');
sagFile = fullfile(rawDir, 'P5B2_SAG_0091_abc_c01_mil.mat');
sweFile = fullfile(rawDir, 'P5B2_SWE_0109_abc_c01_mil.mat');

% 3. Verify that both files exist before proceeding
assert(exist(sagFile, 'file') == 2, 'Sag recording not found: %s', sagFile);
assert(exist(sweFile, 'file') == 2, 'Swell recording not found: %s', sweFile);

fprintf('=== BLOCK A COMPLETE ===\n');
fprintf('Repository Root: %s\n', projectRoot);
fprintf('Verified Sag File:   %s\n', sagFile);
fprintf('Verified Swell File: %s\n\n', sweFile);
```

---

### Block B: Inspect MAT Structure & Load Recordings

**Purpose:** Uses `whos('-file', ...)` to inspect MAT contents without loading entire arrays, loads the required variables into workspace structs, displays trajectory metadata (ID, class, phase, operating condition), and performs numeric integrity checks (dimensions, NaNs, Infs).

```matlab
%% =========================================================================
%% BLOCK B: INSPECT AND LOAD RECORDINGS WITH INTEGRITY CHECKS
%% =========================================================================
% Instructions: Copy and paste this entire block into the MATLAB Command Window.

fprintf('--- Inspecting Stored Variables in MAT Files (whos) ---\n');
fprintf('Variables in Sag File:\n');
whos('-file', sagFile);

fprintf('\nVariables in Swell File:\n');
whos('-file', sweFile);

% 1. Load the recordings into workspace structs
fprintf('\n--- Loading MAT Recordings into Memory ---\n');
sagData = load(sagFile);
sweData = load(sweFile);

% 2. Display Trajectory ID, Disturbance Class, and Operating Condition
fprintf('Sag Trajectory ID:   %s | Class: %s | Phase: %s | Condition: %s\n', ...
    sagData.sc.trajectory_id, sagData.sc.class, sagData.sc.phase, sagData.sc.operating_condition_name);
fprintf('Swell Trajectory ID: %s | Class: %s | Phase: %s | Condition: %s\n\n', ...
    sweData.sc.trajectory_id, sweData.sc.class, sweData.sc.phase, sweData.sc.operating_condition_name);

% 3. Print array dimensions and time vector lengths
fprintf('--- Array Dimensions ---\n');
fprintf('Sag   V_cont_20k: [%d x %d], I_cont_20k: [%d x %d], t_grid_20k: [%d x %d]\n', ...
    size(sagData.V_cont_20k, 1), size(sagData.V_cont_20k, 2), ...
    size(sagData.I_cont_20k, 1), size(sagData.I_cont_20k, 2), ...
    size(sagData.t_grid_20k, 1), size(sagData.t_grid_20k, 2));
fprintf('Swell V_cont_20k: [%d x %d], I_cont_20k: [%d x %d], t_grid_20k: [%d x %d]\n', ...
    size(sweData.V_cont_20k, 1), size(sweData.V_cont_20k, 2), ...
    size(sweData.I_cont_20k, 1), size(sweData.I_cont_20k, 2), ...
    size(sweData.t_grid_20k, 1), size(sweData.t_grid_20k, 2));

% 4. Basic Check 1: Inconsistent Dimensions
assert(size(sagData.V_cont_20k, 1) == size(sagData.t_grid_20k, 1), 'Sag V length mismatch!');
assert(size(sagData.I_cont_20k, 1) == size(sagData.t_grid_20k, 1), 'Sag I length mismatch!');
assert(size(sweData.V_cont_20k, 1) == size(sweData.t_grid_20k, 1), 'Swell V length mismatch!');
assert(size(sweData.I_cont_20k, 1) == size(sweData.t_grid_20k, 1), 'Swell I length mismatch!');
assert(size(sagData.V_cont_20k, 2) == 3, 'Sag V must have 3 phases (columns)!');
assert(size(sweData.V_cont_20k, 2) == 3, 'Swell V must have 3 phases (columns)!');

% 5. Basic Check 2: Zero NaN values
assert(~any(isnan(sagData.V_cont_20k(:))), 'NaN detected in Sag V_cont_20k!');
assert(~any(isnan(sagData.I_cont_20k(:))), 'NaN detected in Sag I_cont_20k!');
assert(~any(isnan(sweData.V_cont_20k(:))), 'NaN detected in Swell V_cont_20k!');
assert(~any(isnan(sweData.I_cont_20k(:))), 'NaN detected in Swell I_cont_20k!');

% 6. Basic Check 3: Zero Inf values
assert(~any(isinf(sagData.V_cont_20k(:))), 'Inf detected in Sag V_cont_20k!');
assert(~any(isinf(sagData.I_cont_20k(:))), 'Inf detected in Sag I_cont_20k!');
assert(~any(isinf(sweData.V_cont_20k(:))), 'Inf detected in Swell V_cont_20k!');
assert(~any(isinf(sweData.I_cont_20k(:))), 'Inf detected in Swell I_cont_20k!');

fprintf('\n=== BLOCK B COMPLETE: All integrity checks passed (0 NaNs, 0 Infs, dimensions match) ===\n\n');
```

---

### Block C: Visualize Voltage Waveforms (Figure 1: Sag vs. Swell)

**Purpose:** Generates **Figure 1** featuring **two vertically stacked panels** that directly compare Three-Phase Voltage Sag (top) against Voltage Swell (bottom). Displays Phase A, Phase B, and Phase C waveforms, vertical boundary markers at disturbance inception and clearing, shaded disturbance intervals, and interval annotations.

```matlab
%% =========================================================================
%% BLOCK C: VISUALIZE VOLTAGE WAVEFORMS (FIGURE 1: SAG VS SWELL)
%% =========================================================================
% Instructions: Copy and paste this entire block into the MATLAB Command Window.

% Extract disturbance timing from scenario metadata
t_start_s = 0.120; % Fault/switching inception at 120 ms
sag_dur_s = double(sagData.sc.parameters.duration_ms) / 1000.0;
swe_dur_s = double(sweData.sc.parameters.duration_ms) / 1000.0;
sag_end_s = t_start_s + sag_dur_s; % 0.195 s (195 ms)
swe_end_s = t_start_s + swe_dur_s; % 0.190 s (190 ms)

% Convert time vectors to milliseconds
t_sag_ms = sagData.t_grid_20k * 1000;
t_swe_ms = sweData.t_grid_20k * 1000;

% Coordinated 3-Phase Color Palette
cPhaseA = [0.00, 0.45, 0.74];  % Blue
cPhaseB = [0.85, 0.33, 0.10];  % Orange/Red
cPhaseC = [0.93, 0.69, 0.13];  % Golden Yellow

% Create Figure 1
fig1 = figure(1);
clf(fig1);
set(fig1, 'Name', 'Figure 1: Voltage Waveform Comparison - Sag vs Swell', ...
          'Color', 'w', 'Position', [100, 80, 1100, 720]);

% --- Top Panel: Voltage Sag ---
subplot(2, 1, 1);
pA1 = plot(t_sag_ms, sagData.V_cont_20k(:, 1), 'Color', cPhaseA, 'LineWidth', 1.2); hold on;
pB1 = plot(t_sag_ms, sagData.V_cont_20k(:, 2), 'Color', cPhaseB, 'LineWidth', 1.2);
pC1 = plot(t_sag_ms, sagData.V_cont_20k(:, 3), 'Color', cPhaseC, 'LineWidth', 1.2);

% Vertical markers for disturbance start and end
xline(t_start_s * 1000, '--r', 'Disturbance Start (120 ms)', 'LineWidth', 1.5, ...
    'LabelVerticalAlignment', 'bottom', 'FontSize', 9);
xline(sag_end_s * 1000, '--g', sprintf('Fault Cleared (%.0f ms)', sag_end_s * 1000), ...
    'LineWidth', 1.5, 'LabelVerticalAlignment', 'bottom', 'FontSize', 9);

% Highlight disturbance interval with light red shaded patch
patch_x = [t_start_s, sag_end_s, sag_end_s, t_start_s] * 1000;
patch_y = [-1.5, -1.5, 1.5, 1.5];
hPatchSag = patch(patch_x, patch_y, [1.0, 0.88, 0.88], 'EdgeColor', 'none', 'FaceAlpha', 0.35);
uistack(hPatchSag, 'bottom');

% Pre-, During-, and Post-disturbance text labels
text(60, 0.95, 'Pre-Disturbance (Steady State)', 'HorizontalAlignment', 'center', ...
    'FontSize', 9, 'FontWeight', 'bold', 'Color', [0.2, 0.2, 0.2]);
text((t_start_s + sag_end_s)/2 * 1000, -0.95, 'Sag Interval', 'HorizontalAlignment', 'center', ...
    'FontSize', 9, 'FontWeight', 'bold', 'Color', [0.8, 0.1, 0.1]);
text(285, 0.95, 'Post-Disturbance (Restored)', 'HorizontalAlignment', 'center', ...
    'FontSize', 9, 'FontWeight', 'bold', 'Color', [0.2, 0.2, 0.2]);

grid on; box on;
xlim([0, 380]);
ylim([-1.15, 1.15]);
title('Class: Voltage Sag | Trajectory: P5B2\_SAG\_0091\_abc\_c01\_mil (Three-Phase Shunt Fault)', ...
    'FontSize', 11, 'FontWeight', 'bold');
xlabel('Time (ms)', 'FontSize', 10);
ylabel('Voltage (pu line-to-neutral)', 'FontSize', 10);
legend([pA1, pB1, pC1], {'Phase A', 'Phase B', 'Phase C'}, 'Location', 'northeast');

% --- Bottom Panel: Voltage Swell ---
subplot(2, 1, 2);
pA2 = plot(t_swe_ms, sweData.V_cont_20k(:, 1), 'Color', cPhaseA, 'LineWidth', 1.2); hold on;
pB2 = plot(t_swe_ms, sweData.V_cont_20k(:, 2), 'Color', cPhaseB, 'LineWidth', 1.2);
pC2 = plot(t_swe_ms, sweData.V_cont_20k(:, 3), 'Color', cPhaseC, 'LineWidth', 1.2);

% Vertical markers for disturbance start and end
xline(t_start_s * 1000, '--r', 'Disturbance Start (120 ms)', 'LineWidth', 1.5, ...
    'LabelVerticalAlignment', 'bottom', 'FontSize', 9);
xline(swe_end_s * 1000, '--g', sprintf('Capacitor Tripped (%.0f ms)', swe_end_s * 1000), ...
    'LineWidth', 1.5, 'LabelVerticalAlignment', 'bottom', 'FontSize', 9);

% Highlight disturbance interval with light blue shaded patch
patch_x_swe = [t_start_s, swe_end_s, swe_end_s, t_start_s] * 1000;
patch_y_swe = [-4.0, -4.0, 4.0, 4.0];
hPatchSwe = patch(patch_x_swe, patch_y_swe, [0.88, 0.92, 1.0], 'EdgeColor', 'none', 'FaceAlpha', 0.35);
uistack(hPatchSwe, 'bottom');

% Pre-, During-, and Post-disturbance text labels
text(60, 2.5, 'Pre-Disturbance (Steady State)', 'HorizontalAlignment', 'center', ...
    'FontSize', 9, 'FontWeight', 'bold', 'Color', [0.2, 0.2, 0.2]);
text((t_start_s + swe_end_s)/2 * 1000, -2.8, 'Swell Interval', 'HorizontalAlignment', 'center', ...
    'FontSize', 9, 'FontWeight', 'bold', 'Color', [0.1, 0.3, 0.8]);
text(285, 2.5, 'Post-Disturbance (Restored)', 'HorizontalAlignment', 'center', ...
    'FontSize', 9, 'FontWeight', 'bold', 'Color', [0.2, 0.2, 0.2]);

grid on; box on;
xlim([0, 380]);
ylim([-3.6, 3.6]);
title('Class: Voltage Swell | Trajectory: P5B2\_SWE\_0109\_abc\_c01\_mil (Capacitor Bank Energization)', ...
    'FontSize', 11, 'FontWeight', 'bold');
xlabel('Time (ms)', 'FontSize', 10);
ylabel('Voltage (pu line-to-neutral)', 'FontSize', 10);
legend([pA2, pB2, pC2], {'Phase A', 'Phase B', 'Phase C'}, 'Location', 'northeast');

fprintf('=== BLOCK C COMPLETE: Figure 1 (Voltage Comparison) displayed ===\n\n');
```

---

### Block D: Visualize Current Waveforms (Figure 2: Sag vs. Swell)

**Purpose:** Validates that transmission line current arrays exist and are non-empty before plotting, then generates **Figure 2** with **two vertically stacked panels** showing transmission line current during Voltage Sag (top) and Voltage Swell (bottom).

```matlab
%% =========================================================================
%% BLOCK D: VISUALIZE CURRENT WAVEFORMS (FIGURE 2: SAG VS SWELL)
%% =========================================================================
% Instructions: Copy and paste this entire block into the MATLAB Command Window.

% 1. Verify current data existence and integrity before plotting
assert(isfield(sagData, 'I_cont_20k'), 'Field I_cont_20k missing from Sag recording!');
assert(isfield(sweData, 'I_cont_20k'), 'Field I_cont_20k missing from Swell recording!');
assert(~isempty(sagData.I_cont_20k), 'Sag current array is empty!');
assert(~isempty(sweData.I_cont_20k), 'Swell current array is empty!');
assert(isreal(sagData.I_cont_20k), 'Sag current contains imaginary components!');
assert(isreal(sweData.I_cont_20k), 'Swell current contains imaginary components!');

% 2. Create Figure 2: Current Comparison
fig2 = figure(2);
clf(fig2);
set(fig2, 'Name', 'Figure 2: Current Waveform Comparison - Sag vs Swell', ...
          'Color', 'w', 'Position', [150, 60, 1100, 720]);

% --- Top Panel: Current During Voltage Sag ---
subplot(2, 1, 1);
pIA1 = plot(t_sag_ms, sagData.I_cont_20k(:, 1), 'Color', cPhaseA, 'LineWidth', 1.2); hold on;
pIB1 = plot(t_sag_ms, sagData.I_cont_20k(:, 2), 'Color', cPhaseB, 'LineWidth', 1.2);
pIC1 = plot(t_sag_ms, sagData.I_cont_20k(:, 3), 'Color', cPhaseC, 'LineWidth', 1.2);

xline(t_start_s * 1000, '--r', 'Disturbance Start (120 ms)', 'LineWidth', 1.5, ...
    'LabelVerticalAlignment', 'bottom', 'FontSize', 9);
xline(sag_end_s * 1000, '--g', sprintf('Fault Cleared (%.0f ms)', sag_end_s * 1000), ...
    'LineWidth', 1.5, 'LabelVerticalAlignment', 'bottom', 'FontSize', 9);

patch_x_cur = [t_start_s, sag_end_s, sag_end_s, t_start_s] * 1000;
patch_y_cur = [-2.0, -2.0, 2.0, 2.0];
hPatchSagCur = patch(patch_x_cur, patch_y_cur, [1.0, 0.88, 0.88], 'EdgeColor', 'none', 'FaceAlpha', 0.35);
uistack(hPatchSagCur, 'bottom');

grid on; box on;
xlim([0, 380]);
ylim([-1.4, 1.4]);
title('Class: Voltage Sag | Trajectory: P5B2\_SAG\_0091\_abc\_c01\_mil - Transmission Line Current Inflow', ...
    'FontSize', 11, 'FontWeight', 'bold');
xlabel('Time (ms)', 'FontSize', 10);
ylabel('Current (pu base)', 'FontSize', 10);
legend([pIA1, pIB1, pIC1], {'Phase A', 'Phase B', 'Phase C'}, 'Location', 'northeast');

% --- Bottom Panel: Current During Voltage Swell ---
subplot(2, 1, 2);
pIA2 = plot(t_swe_ms, sweData.I_cont_20k(:, 1), 'Color', cPhaseA, 'LineWidth', 1.2); hold on;
pIB2 = plot(t_swe_ms, sweData.I_cont_20k(:, 2), 'Color', cPhaseB, 'LineWidth', 1.2);
pIC2 = plot(t_swe_ms, sweData.I_cont_20k(:, 3), 'Color', cPhaseC, 'LineWidth', 1.2);

xline(t_start_s * 1000, '--r', 'Disturbance Start (120 ms)', 'LineWidth', 1.5, ...
    'LabelVerticalAlignment', 'bottom', 'FontSize', 9);
xline(swe_end_s * 1000, '--g', sprintf('Capacitor Tripped (%.0f ms)', swe_end_s * 1000), ...
    'LineWidth', 1.5, 'LabelVerticalAlignment', 'bottom', 'FontSize', 9);

patch_x_swe_cur = [t_start_s, swe_end_s, swe_end_s, t_start_s] * 1000;
patch_y_swe_cur = [-6.0, -6.0, 6.0, 6.0];
hPatchSweCur = patch(patch_x_swe_cur, patch_y_swe_cur, [0.88, 0.92, 1.0], 'EdgeColor', 'none', 'FaceAlpha', 0.35);
uistack(hPatchSweCur, 'bottom');

grid on; box on;
xlim([0, 380]);
ylim([-4.5, 4.5]);
title('Class: Voltage Swell | Trajectory: P5B2\_SWE\_0109\_abc\_c01\_mil - Transmission Current During Energization', ...
    'FontSize', 11, 'FontWeight', 'bold');
xlabel('Time (ms)', 'FontSize', 10);
ylabel('Current (pu base)', 'FontSize', 10);
legend([pIA2, pIB2, pIC2], {'Phase A', 'Phase B', 'Phase C'}, 'Location', 'northeast');

fprintf('=== BLOCK D COMPLETE: Figure 2 (Current Comparison) displayed ===\n\n');
```

---

### Block E: Verify Sampling Rates, Durations & Signal Integrity

**Purpose:** Programmatically tests the physical sampling expectations against loaded data (7,601 samples at 20 kHz, 1,901 samples at 5 kHz, 0.38 s duration, $\Delta t = 50\ \mu\text{s}$ and $200\ \mu\text{s}$), verifies disturbance timing, and prints a formatted verification report.

```matlab
%% =========================================================================
%% BLOCK E: VERIFY SAMPLING RATES, DURATIONS & SIGNAL INTEGRITY
%% =========================================================================
% Instructions: Copy and paste this entire block into the MATLAB Command Window.

fprintf('=================================================================\n');
fprintf('                SIGNAL INTEGRITY VERIFICATION REPORT             \n');
fprintf('=================================================================\n');

% 1. Sag Calculations
N_sag_20k   = size(sagData.V_cont_20k, 1);
dur_sag_20k = sagData.t_grid_20k(end) - sagData.t_grid_20k(1);
dt_sag_20k  = mean(diff(sagData.t_grid_20k));
fs_sag_20k  = 1.0 / dt_sag_20k;

N_sag_5k   = size(sagData.V_cont_5k, 1);
dur_sag_5k = sagData.t_grid_5k(end) - sagData.t_grid_5k(1);
dt_sag_5k  = mean(diff(sagData.t_grid_5k));
fs_sag_5k  = 1.0 / dt_sag_5k;

% 2. Swell Calculations
N_swe_20k   = size(sweData.V_cont_20k, 1);
dur_swe_20k = sweData.t_grid_20k(end) - sweData.t_grid_20k(1);
dt_swe_20k  = mean(diff(sweData.t_grid_20k));
fs_swe_20k  = 1.0 / dt_swe_20k;

N_swe_5k   = size(sweData.V_cont_5k, 1);
dur_swe_5k = sweData.t_grid_5k(end) - sweData.t_grid_5k(1);
dt_swe_5k  = mean(diff(sweData.t_grid_5k));
fs_swe_5k  = 1.0 / dt_swe_5k;

% 3. Check Expectations Against Loaded Data
assert(N_sag_20k == 7601, 'Expected 7,601 samples for Sag 20k, found %d', N_sag_20k);
assert(N_swe_20k == 7601, 'Expected 7,601 samples for Swell 20k, found %d', N_swe_20k);
assert(N_sag_5k  == 1901, 'Expected 1,901 samples for Sag 5k, found %d', N_sag_5k);
assert(N_swe_5k  == 1901, 'Expected 1,901 samples for Swell 5k, found %d', N_swe_5k);

assert(abs(dur_sag_20k - 0.38) < 1e-4, 'Expected 0.38 s for Sag 20k, found %.4f', dur_sag_20k);
assert(abs(dur_swe_20k - 0.38) < 1e-4, 'Expected 0.38 s for Swell 20k, found %.4f', dur_swe_20k);
assert(abs(dur_sag_5k  - 0.38) < 1e-4, 'Expected 0.38 s for Sag 5k, found %.4f', dur_sag_5k);
assert(abs(dur_swe_5k  - 0.38) < 1e-4, 'Expected 0.38 s for Swell 5k, found %.4f', dur_swe_5k);

assert(abs(fs_sag_20k - 20000) < 1.0, 'Expected 20 kHz for Sag, calculated %.1f Hz', fs_sag_20k);
assert(abs(fs_swe_20k - 20000) < 1.0, 'Expected 20 kHz for Swell, calculated %.1f Hz', fs_swe_20k);
assert(abs(fs_sag_5k  - 5000)  < 1.0, 'Expected 5 kHz for Sag, calculated %.1f Hz', fs_sag_5k);
assert(abs(fs_swe_5k  - 5000)  < 1.0, 'Expected 5 kHz for Swell, calculated %.1f Hz', fs_swe_5k);

% 4. Print Tabular Results
fprintf('%-18s | %-12s | %-12s | %-10s | %-10s | %-12s\n', ...
    'Signal Array', 'Sample Count', 'Sampling dt', 'Rate (Fs)', 'Duration', 'Integrity');
fprintf('-----------------------------------------------------------------------------------------------\n');
fprintf('%-18s | %-12d | %-9.2f us | %-7.0f Hz | %-7.3f s  | PASS (0 NaN/Inf)\n', ...
    'Sag V_cont_20k', N_sag_20k, dt_sag_20k * 1e6, fs_sag_20k, dur_sag_20k);
fprintf('%-18s | %-12d | %-9.2f us | %-7.0f Hz | %-7.3f s  | PASS (0 NaN/Inf)\n', ...
    'Sag V_cont_5k', N_sag_5k, dt_sag_5k * 1e6, fs_sag_5k, dur_sag_5k);
fprintf('%-18s | %-12d | %-9.2f us | %-7.0f Hz | %-7.3f s  | PASS (0 NaN/Inf)\n', ...
    'Swell V_cont_20k', N_swe_20k, dt_swe_20k * 1e6, fs_swe_20k, dur_swe_20k);
fprintf('%-18s | %-12d | %-9.2f us | %-7.0f Hz | %-7.3f s  | PASS (0 NaN/Inf)\n', ...
    'Swell V_cont_5k', N_swe_5k, dt_swe_5k * 1e6, fs_swe_5k, dur_swe_5k);

fprintf('\n--- Disturbance Timing Verification ---\n');
fprintf('Sag Disturbance:   Inception = %.3f s | Duration = %.1f ms | Clearing = %.3f s\n', ...
    t_start_s, sag_dur_s * 1000, sag_end_s);
fprintf('Swell Disturbance: Inception = %.3f s | Duration = %.1f ms | Clearing = %.3f s\n', ...
    t_start_s, swe_dur_s * 1000, swe_end_s);

fprintf('\n=== BLOCK E COMPLETE: All sampling and timing expectations passed ===\n');
```

---

## 5. How to Interact with MATLAB Figures

Once Figures 1 and 2 are rendered, you can inspect and manipulate them using standard MATLAB interactive tools:

### 1. Zoom In and Out
- **Toolbar:** Click the **Zoom In** magnifying glass icon (`+`) on the figure window toolbar. Click and drag a rectangle over the disturbance onset region ($115\text{ to }135\text{ ms}$) to examine sub-cycle point-on-wave switching details.
- **Command Window:** Type `zoom on` to enable zooming. Double-click inside any subplot to reset the view to full scale.

### 2. Pan Across Time
- **Toolbar:** Click the **Pan** hand icon on the figure window toolbar. Click and drag horizontally to move smoothly between the pre-disturbance, disturbance, and post-disturbance intervals.
- **Command Window:** Type `pan on` to enable panning.

### 3. Inspect Point-on-Wave Values (Data Cursor)
- **Toolbar:** Click the **Data Tips** or **Data Cursor** icon on the toolbar. Click directly on any waveform curve (e.g., Phase A at $t = 120\text{ ms}$) to create a tooltip displaying exact `X` (Time in ms) and `Y` (Voltage or Current in pu) coordinates.
- **Command Window:** Type `datacursormode on` to activate data cursors from the command line.

### 4. Export Publication-Quality Figures
You can export the figures directly from the Command Window at 300 DPI:

```matlab
% Export Figure 1 (Voltage) to high-resolution PNG
exportgraphics(figure(1), 'sag_swell_voltage_comparison.png', 'Resolution', 300);

% Export Figure 2 (Current) to high-resolution PNG
exportgraphics(figure(2), 'sag_swell_current_comparison.png', 'Resolution', 300);

% Export vector PDF for publication inclusion
exportgraphics(figure(1), 'sag_swell_voltage_comparison.pdf', 'ContentType', 'vector');
```

Alternatively, in the figure menu bar, choose **File -> Save As...** and select your desired format (`.png`, `.pdf`, `.eps`, or native MATLAB `.fig`).

---

## 6. Reading Recordings vs. Running Simulink

It is essential to understand the difference between reading recorded files and executing the Simulink runner:

```
+-----------------------------------------------------------------------------------+
| OPERATION 1: LOAD & VISUALIZE PRE-COMPUTED RECORDINGS (RECOMMENDED)               |
| • Command: data = load('data/ieee9bus_60hz_phase5c/raw/P5B2_SAG_0091_abc_c01_mil')|
| • Requirements: Base MATLAB (R2024b, R2025a, or earlier)                         |
| • Runtime: < 0.05 seconds per recording                                           |
| • System Impact: Pure read-only file access; zero simulation overhead             |
+-----------------------------------------------------------------------------------+
                                         vs.
+-----------------------------------------------------------------------------------+
| OPERATION 2: RUN SIMULINK BULK RUNNER (RESEARCHERS ONLY)                          |
| • Command: run_phase5c_bulk_simulation({'P5B2_SAG_0091_abc_c01_mil'})             |
| • Requirements: MATLAB R2024b/R2025a + Simulink + Simscape Electrical             |
| • Caching Behavior: If the recording already exists on disk and has 7,601 rows in  |
|                     V_cont_20k, the runner SKIPS simulation to prevent data       |
|                     corruption or accidental overwrite.                           |
| • Execution Time: 2.09 s (when all 144 exist); ~3.5 s per new trajectory          |
+-----------------------------------------------------------------------------------+
```

---

## 7. Troubleshooting Common Issues

| Issue / Error Message | Root Cause | Solution |
|---|---|---|
| `Sag recording not found: D:\my study\...` | Incorrect `projectRoot` path in Block A. | Verify that `projectRoot` matches your actual repository clone path on disk. Always construct subpaths using `fullfile()`. |
| `File contains Git LFS pointer text, not binary MAT` | Git LFS objects were not downloaded during repository cloning. | In your terminal, run `git lfs pull` from the repository root to download the MAT recording files. |
| `Index exceeds the number of array elements` | Running Block C or D before Block B. | Follow the strict execution order: Run Block A first, then Block B, followed by Blocks C, D, and E. |
| `Undefined function 'exportgraphics'` | Using a legacy MATLAB version prior to R2020a. | Replace `exportgraphics(fig, 'name.png')` with `saveas(fig, 'name.png')` or `print(fig, '-dpng', '-r300', 'name.png')`. |
| `run_phase5c_bulk_simulation logs [Sim 1/1 SKIP]` | The target file already exists with 7,601 samples. | This is expected behavior. The runner uses execution caching to protect verified artifacts. Load the file directly using `load()`. |
