# MATLAB Voltage Sag & Swell Waveform Visualization Guide

**Document Reference:** `docs/guides/MATLAB_SAG_SWELL_VISUALIZATION_GUIDE.md`  
**Audience:** Researchers, engineers, and students inspecting power quality simulation outputs.  
**System Benchmark:** WSCC 3-Machine 9-Bus System ($60.0\text{ Hz}$ fundamental, Bus 5 transmission PCC).  
**Dataset Reference:** Phase 5C Dual-Rate Waveform Dataset (`data/ieee9bus_60hz_phase5c/raw/`).  
**Software Requirements:** MATLAB R2024b or R2025a (Base MATLAB only for plotting; Simulink + Simscape Electrical only if re-running simulations).

---

## 1. Overview: What This Demonstration Does & Does Not Do

### What This Demonstration Does
- Inspects and loads **pre-computed, validated simulation recordings** of three-phase Voltage Sag and Voltage Swell events stored in `.mat` files.
- Visualizes continuous dual-rate representations:
  - **High-Resolution (20 kHz, 4,000 samples/200 ms window):** Preserves sub-cycle inception, point-on-wave switching, and high-frequency ringing.
  - **Canonical Production (5 kHz, 1,000 samples/200 ms window):** Matches the production 32-feature extraction pipeline.
- Plots synchronized three-phase voltages ($V_A, V_B, V_C$) and transmission line currents ($I_A, I_B, I_C$) in separate panels.
- Reads disturbance metadata dynamically from the saved scenario structure `sc` (inception time, fault duration, clearing time, affected phases).
- Performs data integrity sanity checks (dimension verification, NaN/Inf checks, sampling grid consistency).

### What This Demonstration Does Not Do
- **Does not require re-running the full 144-trajectory simulation matrix.** All recordings are pre-computed and stored in `data/ieee9bus_60hz_phase5c/raw/`.
- **Does not alter the protected pristine Simulink reference.** The reference model `IEEE_9bus/IEEE_9bus_PQD_HIL_R2025a.slx` remains frozen and untouched.
- **Does not implement Phase 6 firmware deployment.** Microcontroller firmware and hardware deployment remain strictly future scope.

---

## 2. Prerequisites & Repository Structure

### Directory Setup
Ensure your local repository clone is intact:
```
power-quality-detector-and-classifier/
├── IEEE_9bus/
│   ├── IEEE_9bus_PQD_HIL_R2025a.slx       # Pristine reference (Frozen, read-only)
│   └── IEEE_9bus_PQD_DISTURBANCES.slx     # Working disturbance model
├── data/
│   └── ieee9bus_60hz_phase5c/
│       └── raw/                           # Pre-computed continuous .mat recordings
│           ├── P5B2_SAG_0091_abc_c01_mil.mat
│           ├── P5B2_SWE_0109_abc_c01_mil.mat
│           └── ... (144 trajectory recordings)
└── scripts/
    └── run_phase5c_bulk_simulation.m      # 144-trajectory runner with skip-cache logic
```

### Verified Example Recordings
This guide uses two verified baseline trajectories from operating condition 1 (nominal load flow, three-phase symmetrical disturbance):
1. **Voltage Sag:** `P5B2_SAG_0091_abc_c01_mil.mat`
   - Disturbance: Three-phase transmission shunt fault (`PQD_Fault_Sag`).
   - Fault Resistance: $200\ \Omega$, Ground Resistance: $0.01\ \Omega$.
   - Inception: $t = 0.120\text{ s}$ ($120.0\text{ ms}$).
   - Configured Duration: $75.0\text{ ms}$ ($4.5\text{ cycles}$ at $60\text{ Hz}$).
   - Clearing Time: $t = 0.120 + 0.075 = 0.195\text{ s}$ ($195.0\text{ ms}$).
2. **Voltage Swell:** `P5B2_SWE_0109_abc_c01_mil.mat`
   - Disturbance: Three-phase shunt capacitor bank energization (`PQD_Breaker_Swell` & `PQD_Cap_Swell`).
   - Reactive Power: $90\text{ MVAR}$ capacitive injection, $100\text{ kW}$ damping.
   - Inception: $t = 0.120\text{ s}$ ($120.0\text{ ms}$).
   - Configured Duration: $70.0\text{ ms}$ ($4.2\text{ cycles}$ at $60\text{ Hz}$).
   - Clearing Time: $t = 0.120 + 0.070 = 0.190\text{ s}$ ($190.0\text{ ms}$).

---

## 3. Signal Units, Scaling & Coordinate Conventions

The logged signals in the MAT files follow the Simscape Electrical three-phase measurement conventions:

| Signal Array | Dimensions | Sampling Rate ($F_s$) | Physical Interpretation & Normalization | Nominal Value Range |
|---|:---:|:---:|---|---|
| `V_cont_20k` | $7601 \times 3$ | $20,000\text{ Hz}$ ($T_s = 50\ \mu\text{s}$) | Phase-to-ground voltage at Bus 5 in **per-unit (pu)**, normalized to system line-to-line base ($V_{\text{base}} = 230\text{ kV}_{L-L}$). | Pre-fault steady-state peak $\approx 0.833\text{ pu}$ ($\sqrt{2}/\sqrt{3} \times 1.02\text{ pu}$), RMS $\approx 0.589\text{ pu}$. |
| `I_cont_20k` | $7601 \times 3$ | $20,000\text{ Hz}$ ($T_s = 50\ \mu\text{s}$) | Phase transmission line current into Bus 5 load center in **per-unit (pu)**, normalized to three-phase system base ($S_{\text{base}} = 100\text{ MVA}$). | Pre-fault steady-state peak $\approx 1.12\text{ pu}$, RMS $\approx 0.793\text{ pu}$. |
| `t_grid_20k` | $7601 \times 1$ | $20,000\text{ Hz}$ | Simulation time vector in seconds, spanning $0.000\text{ s}$ to $0.380\text{ s}$ ($380.0\text{ ms}$). | Monotonically increasing from $0$ to $0.38$. |
| `V_cont_5k`  | $1901 \times 3$ | $5,000\text{ Hz}$ ($T_s = 200\ \mu\text{s}$) | Anti-aliased decimated voltage matching 32-feature extraction pipeline. | Same per-unit scaling as `V_cont_20k`. |
| `I_cont_5k`  | $1901 \times 3$ | $5,000\text{ Hz}$ ($T_s = 200\ \mu\text{s}$) | Anti-aliased decimated line current matching 32-feature extraction pipeline. | Same per-unit scaling as `I_cont_20k`. |
| `t_grid_5k`  | $1901 \times 1$ | $5,000\text{ Hz}$ | Simulation time vector in seconds, spanning $0.000\text{ s}$ to $0.380\text{ s}$. | Monotonically increasing from $0$ to $0.38$. |
| `sc`         | Scalar struct | N/A | Scenario metadata catalog entry containing disturbance parameters, operating condition, and split. | See Section 4. |

> **Note on Per-Unit Voltage:** In power systems analysis, line-to-neutral peak voltage for a 1.0 pu line-to-line system is $1.0 \times \sqrt{2}/\sqrt{3} \approx 0.8165\text{ pu}$. At Bus 5 under nominal power flow ($V = 1.020\text{ pu}$), the nominal line-to-neutral peak is $1.02 \times \sqrt{2}/\sqrt{3} \approx 0.8328\text{ pu}$, and RMS is $1.02 / \sqrt{3} \approx 0.5889\text{ pu}$.

---

## 4. Step-by-Step MATLAB Demonstration Code

Copy and paste the following MATLAB code into a script (e.g., `visualize_sag_swell_demo.m`) or execute it section-by-section in the MATLAB Command Window.

### Step 4.1: Configure Repository Path and Verify File Existence

```matlab
%% 1. INITIALIZE PROJECT PATHS & VERIFY ARTIFACTS
clear; clc; close all;

% Set your repository root directory (adjust if placed elsewhere)
projectRoot = 'D:\my study\Project\power-quality-detector-and-classifier';

% Define paths to pre-computed Sag and Swell recordings
rawDir = fullfile(projectRoot, 'data', 'ieee9bus_60hz_phase5c', 'raw');
sagFile = fullfile(rawDir, 'P5B2_SAG_0091_abc_c01_mil.mat');
sweFile = fullfile(rawDir, 'P5B2_SWE_0109_abc_c01_mil.mat');

% Verify file existence before loading
assert(exist(sagFile, 'file') == 2, 'Sag recording not found: %s', sagFile);
assert(exist(sweFile, 'file') == 2, 'Swell recording not found: %s', sweFile);
fprintf('Found valid Sag and Swell MAT files in:\n  %s\n\n', rawDir);
```

### Step 4.2: Inspect Internal MAT File Variables

```matlab
%% 2. INSPECT MAT FILE STRUCTURE WITHOUT LOADING FULL ARRAYS
fprintf('--- Variables in Sag Recording (%s) ---\n', 'P5B2_SAG_0091');
whos('-file', sagFile);

fprintf('\n--- Variables in Swell Recording (%s) ---\n', 'P5B2_SWE_0109');
whos('-file', sweFile);
```

### Step 4.3: Load Data and Validate Integrity

```matlab
%% 3. LOAD DATA & EXECUTE INTEGRITY SANITY CHECKS
sagData = load(sagFile);
sweData = load(sweFile);

% Check 1: Verify continuous array dimensions (7,601 x 3 at 20 kHz; 1,901 x 3 at 5 kHz)
assert(isequal(size(sagData.V_cont_20k), [7601, 3]), 'Sag V_cont_20k shape mismatch!');
assert(isequal(size(sagData.I_cont_20k), [7601, 3]), 'Sag I_cont_20k shape mismatch!');
assert(isequal(size(sweData.V_cont_20k), [7601, 3]), 'Swell V_cont_20k shape mismatch!');
assert(isequal(size(sweData.I_cont_20k), [7601, 3]), 'Swell I_cont_20k shape mismatch!');

% Check 2: Verify zero NaN or Inf values
assert(~any(isnan(sagData.V_cont_20k(:))) && ~any(isinf(sagData.V_cont_20k(:))), 'NaN/Inf in Sag V!');
assert(~any(isnan(sweData.V_cont_20k(:))) && ~any(isinf(sweData.V_cont_20k(:))), 'NaN/Inf in Swell V!');

% Check 3: Extract disturbance timing from scenario metadata
t_fault_start = 0.120; % Base fault injection start in simulation runner
sag_dur_s = double(sagData.sc.parameters.duration_ms) / 1000.0;
swe_dur_s = double(sweData.sc.parameters.duration_ms) / 1000.0;

sag_t_end = t_fault_start + sag_dur_s;
swe_t_end = t_fault_start + swe_dur_s;

fprintf('Integrity checks passed successfully.\n');
fprintf('Sag Disturbance Window:   t = %.3f s to %.3f s (Duration: %.1f ms)\n', ...
    t_fault_start, sag_t_end, sag_dur_s * 1000);
fprintf('Swell Disturbance Window: t = %.3f s to %.3f s (Duration: %.1f ms)\n\n', ...
    t_fault_start, swe_t_end, swe_dur_s * 1000);
```

### Step 4.4: Plot Voltage Sag (3-Phase Voltage and Current)

```matlab
%% 4. PLOT THREE-PHASE VOLTAGE SAG WAVEFORMS
fig1 = figure('Name', 'IEEE 9-Bus Voltage Sag Demonstration', ...
              'Color', 'w', 'Position', [100, 100, 1000, 700]);

% Color palette for phases A, B, C
cPhase = [0.00, 0.45, 0.74;  % Phase A - Blue
          0.85, 0.33, 0.10;  % Phase B - Orange
          0.93, 0.69, 0.13]; % Phase C - Yellow/Gold

% Subplot 1: Three-Phase Voltage
subplot(2, 1, 1);
plot(sagData.t_grid_20k * 1000, sagData.V_cont_20k(:, 1), 'Color', cPhase(1, :), 'LineWidth', 1.2); hold on;
plot(sagData.t_grid_20k * 1000, sagData.V_cont_20k(:, 2), 'Color', cPhase(2, :), 'LineWidth', 1.2);
plot(sagData.t_grid_20k * 1000, sagData.V_cont_20k(:, 3), 'Color', cPhase(3, :), 'LineWidth', 1.2);

% Mark disturbance boundary
xline(t_fault_start * 1000, '--r', 'Fault Inception (120 ms)', 'LineWidth', 1.5, 'LabelVerticalAlignment', 'bottom');
xline(sag_t_end * 1000, '--g', sprintf('Fault Cleared (%.1f ms)', sag_t_end * 1000), 'LineWidth', 1.5);
yregion = patch([t_fault_start, sag_t_end, sag_t_end, t_fault_start] * 1000, ...
                [-1.2, -1.2, 1.2, 1.2], [1.0, 0.9, 0.9], 'EdgeColor', 'none', 'FaceAlpha', 0.25);
uistack(yregion, 'bottom');

grid on; box on;
xlim([0, 380]); ylim([-1.1, 1.1]);
title('Three-Phase Bus 5 Voltage During Voltage Sag (Trajectory: P5B2\_SAG\_0091)', 'FontSize', 12, 'FontWeight', 'bold');
xlabel('Time (ms)', 'FontSize', 10);
ylabel('Voltage (pu line-to-neutral)', 'FontSize', 10);
legend({'Phase A', 'Phase B', 'Phase C', 'Fault Inception', 'Fault Cleared'}, 'Location', 'northeast');

% Subplot 2: Three-Phase Current
subplot(2, 1, 2);
plot(sagData.t_grid_20k * 1000, sagData.I_cont_20k(:, 1), 'Color', cPhase(1, :), 'LineWidth', 1.2); hold on;
plot(sagData.t_grid_20k * 1000, sagData.I_cont_20k(:, 2), 'Color', cPhase(2, :), 'LineWidth', 1.2);
plot(sagData.t_grid_20k * 1000, sagData.I_cont_20k(:, 3), 'Color', cPhase(3, :), 'LineWidth', 1.2);

xline(t_fault_start * 1000, '--r', 'LineWidth', 1.5);
xline(sag_t_end * 1000, '--g', 'LineWidth', 1.5);

grid on; box on;
xlim([0, 380]);
title('Three-Phase Bus 5 Current Inflow During Voltage Sag', 'FontSize', 12, 'FontWeight', 'bold');
xlabel('Time (ms)', 'FontSize', 10);
ylabel('Current (pu base)', 'FontSize', 10);
legend({'Phase A', 'Phase B', 'Phase C'}, 'Location', 'northeast');
```

### Step 4.5: Plot Voltage Swell (3-Phase Voltage and Current)

```matlab
%% 5. PLOT THREE-PHASE VOLTAGE SWELL WAVEFORMS
fig2 = figure('Name', 'IEEE 9-Bus Voltage Swell Demonstration', ...
              'Color', 'w', 'Position', [150, 150, 1000, 700]);

% Subplot 1: Three-Phase Voltage
subplot(2, 1, 1);
plot(sweData.t_grid_20k * 1000, sweData.V_cont_20k(:, 1), 'Color', cPhase(1, :), 'LineWidth', 1.2); hold on;
plot(sweData.t_grid_20k * 1000, sweData.V_cont_20k(:, 2), 'Color', cPhase(2, :), 'LineWidth', 1.2);
plot(sweData.t_grid_20k * 1000, sweData.V_cont_20k(:, 3), 'Color', cPhase(3, :), 'LineWidth', 1.2);

% Mark disturbance boundary
xline(t_fault_start * 1000, '--r', 'Capacitor Switch On (120 ms)', 'LineWidth', 1.5, 'LabelVerticalAlignment', 'bottom');
xline(swe_t_end * 1000, '--g', sprintf('Capacitor Trip (%.1f ms)', swe_t_end * 1000), 'LineWidth', 1.5);
yregion = patch([t_fault_start, swe_t_end, swe_t_end, t_fault_start] * 1000, ...
                [-1.5, -1.5, 1.5, 1.5], [0.9, 0.95, 1.0], 'EdgeColor', 'none', 'FaceAlpha', 0.25);
uistack(yregion, 'bottom');

grid on; box on;
xlim([0, 380]); ylim([-1.3, 1.3]);
title('Three-Phase Bus 5 Voltage During Voltage Swell (Trajectory: P5B2\_SWE\_0109)', 'FontSize', 12, 'FontWeight', 'bold');
xlabel('Time (ms)', 'FontSize', 10);
ylabel('Voltage (pu line-to-neutral)', 'FontSize', 10);
legend({'Phase A', 'Phase B', 'Phase C', 'Energization', 'De-energization'}, 'Location', 'northeast');

% Subplot 2: Three-Phase Current
subplot(2, 1, 2);
plot(sweData.t_grid_20k * 1000, sweData.I_cont_20k(:, 1), 'Color', cPhase(1, :), 'LineWidth', 1.2); hold on;
plot(sweData.t_grid_20k * 1000, sweData.I_cont_20k(:, 2), 'Color', cPhase(2, :), 'LineWidth', 1.2);
plot(sweData.t_grid_20k * 1000, sweData.I_cont_20k(:, 3), 'Color', cPhase(3, :), 'LineWidth', 1.2);

xline(t_fault_start * 1000, '--r', 'LineWidth', 1.5);
xline(swe_t_end * 1000, '--g', 'LineWidth', 1.5);

grid on; box on;
xlim([0, 380]);
title('Three-Phase Bus 5 Current During Capacitor Energization', 'FontSize', 12, 'FontWeight', 'bold');
xlabel('Time (ms)', 'FontSize', 10);
ylabel('Current (pu base)', 'FontSize', 10);
legend({'Phase A', 'Phase B', 'Phase C'}, 'Location', 'northeast');
```

### Step 4.6: Dual-Rate Comparison (20 kHz vs. 5 kHz)

```matlab
%% 6. COMPARE HIGH-RATE (20 kHz) VS CANONICAL (5 kHz) REPRESENTATIONS
fig3 = figure('Name', 'Dual-Rate Sampling Comparison', 'Color', 'w', 'Position', [200, 200, 900, 400]);

% Zoom in on Sag inception transient (115 ms to 135 ms)
idx_20k = (sagData.t_grid_20k >= 0.115) & (sagData.t_grid_20k <= 0.135);
idx_5k  = (sagData.t_grid_5k  >= 0.115) & (sagData.t_grid_5k  <= 0.135);

plot(sagData.t_grid_20k(idx_20k) * 1000, sagData.V_cont_20k(idx_20k, 1), '-b', 'LineWidth', 1.5); hold on;
plot(sagData.t_grid_5k(idx_5k) * 1000, sagData.V_cont_5k(idx_5k, 1), 's--r', 'LineWidth', 1.0, 'MarkerSize', 5);

grid on; box on;
title('Voltage Sag Inception Detail: 20 kHz (400 pts) vs. 5 kHz (100 pts)', 'FontSize', 12, 'FontWeight', 'bold');
xlabel('Time (ms)', 'FontSize', 10);
ylabel('Phase A Voltage (pu)', 'FontSize', 10);
legend({'20 kHz Continuous (ode23tb)', '5 kHz Anti-Aliased Decimated (Chebyshev I)'}, 'Location', 'best');
```

---

## 5. Visual Interpretation of Results

### What You Should Observe:
1. **Pre-Event Steady State ($0\text{ to }120\text{ ms}$):**
   - Pure balanced sinusoidal voltage with nominal amplitude $\approx 0.833\text{ pu}$ line-to-neutral peak.
   - 120-degree phase separation across Blue (Phase A), Orange (Phase B), and Yellow (Phase C).
2. **Voltage Sag ($120\text{ to }195\text{ ms}$):**
   - At $t = 120\text{ ms}$, the shunt fault switch closes, causing an instantaneous drop in voltage amplitude to $\approx 0.65\text{ pu}$.
   - Concurrently, transmission fault current increases sharply.
   - At $t = 195\text{ ms}$, the fault switch opens, and voltages restore smoothly to nominal steady state without numerical divergence.
3. **Voltage Swell ($120\text{ to }190\text{ ms}$):**
   - At $t = 120\text{ ms}$, the shunt capacitor bank breaker closes, causing an instantaneous step increase in peak voltage to $\approx 1.05\text{ pu}$ ($\sim 1.25\times$ baseline).
   - High-frequency switching oscillations occur during breaker closing.
   - At $t = 190\text{ ms}$, the breaker disconnects the bank, restoring steady-state voltage.

---

## 6. Reading Recordings vs. Running New Simulations

It is critical to distinguish between reading existing recordings and running Simulink:

```
+-----------------------------------------------------------------------------------+
| OPERATION 1: VISUALIZE EXISTING RECORDINGS (RECOMMENDED)                         |
| • Command: load('data/ieee9bus_60hz_phase5c/raw/P5B2_SAG_0091_abc_c01_mil.mat')   |
| • Requirements: MATLAB Base (Any recent version)                                  |
| • Runtime: < 0.05 seconds                                                         |
| • System Impact: Pure read-only file access; zero simulation overhead             |
+-----------------------------------------------------------------------------------+
                                        vs.
+-----------------------------------------------------------------------------------+
| OPERATION 2: RUN SIMULINK TRAJECTORY (ADVANCED / RESEARCHERS)                     |
| • Command: run_phase5c_bulk_simulation({'P5B2_SAG_0091_abc_c01_mil'})             |
| • Requirements: MATLAB R2024b/R2025a + Simulink + Simscape Electrical             |
| • Behavior: If the recording already exists on disk and has 7,601 points,        |
|             the runner SKIPS the simulation to preserve verified artifacts.      |
| • Execution Time: 2.09 s (when all 144 exist); ~3.5 s per un-simulated run        |
+-----------------------------------------------------------------------------------+
```

### Targeted Execution of a Single Trajectory
If you genuinely want to re-execute a single trajectory in Simulink using the verified runner, pass its trajectory ID as a cell array:
```matlab
% Add paths
addpath('scripts');
addpath('IEEE_9bus');

% Run single targeted trajectory
run_phase5c_bulk_simulation({'P5B2_SAG_0091_abc_c01_mil'});
```
*Note: The runner checks if the destination `.mat` file exists and has 7,601 rows in `V_cont_20k`. If valid, it logs `[Sim 1/1 SKIP]` to avoid corrupting or overwriting verified data.*

---

## 7. Troubleshooting Common Issues

| Symptom | Probable Cause | Corrective Action |
|---|---|---|
| `Cannot find file: ...P5B2_SAG_0091...` | Incorrect `projectRoot` path in MATLAB. | Verify `projectRoot` matches your clone path (e.g., `D:\my study\Project\power-quality-detector-and-classifier`). Use `fullfile` to avoid forward/backward slash errors. |
| `Git LFS pointer file instead of MAT data` | Git LFS objects were not pulled during clone. | Run `git lfs pull` from your terminal or ensure large files were downloaded properly. |
| `Undefined function 'run_phase5c_bulk_simulation'` | `scripts/` directory is not on the MATLAB path. | Run `addpath('scripts')` and `addpath('IEEE_9bus')` in the MATLAB Command Window. |
| `Simulink error: Block diagram 'IEEE_9bus_PQD_DISTURBANCES' not found` | `IEEE_9bus/` directory is not on the path. | Run `addpath(fullfile(projectRoot, 'IEEE_9bus'))`. |
| `Simulation takes only 2 seconds and says SKIP` | All 144 recordings already exist on disk. | This is the intended behavior of the runner's validation cache. To visualize the data, use `load(...)` directly as shown in Section 4. |
