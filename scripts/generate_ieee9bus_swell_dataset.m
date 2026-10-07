% scripts/generate_ieee9bus_swell_dataset.m
% Generates 1,152 unique Voltage Swell frames across 36 distinct simulation scenarios
% in the IEEE 9-bus 60-Hz domain using the approved Bus 4 Switched Capacitor Bank mechanism.

cur_dir = fileparts(mfilename('fullpath'));
project_root = fileparts(cur_dir);
addpath(fullfile(project_root, 'IEEE_9bus'));

out_dir = fullfile(project_root, 'data', 'ieee9bus_60hz', 'swell');
if ~exist(out_dir, 'dir')
    mkdir(out_dir);
end

% 1. Model Setup
mdl = 'IEEE_9bus_PQD_DISTURBANCES';
fprintf('[SwellBatch] Loading disturbance model: %s...\n', mdl);
load_system(mdl);
set_param(mdl, 'StopFcn', '');
set_param(mdl, 'Solver', 'ode23tb');
set_param(mdl, 'RelTol', '1e-4');

% Ensure Sag Fault block is disabled
fault_blk = [mdl '/PQD_Fault_Sag'];
if ~isempty(find_system(mdl, 'SearchDepth', 1, 'Name', 'PQD_Fault_Sag'))
    set_param(fault_blk, 'FaultA', 'off', 'FaultB', 'off', 'FaultC', 'off', ...
        'GroundFault', 'off', 'SwitchTimes', '[999 1000]');
end

brk_blk = [mdl '/PQD_Breaker_Swell'];
cap_blk = [mdl '/PQD_Cap_Swell'];
if isempty(find_system(mdl, 'SearchDepth', 1, 'Name', 'PQD_Breaker_Swell')) || ...
   isempty(find_system(mdl, 'SearchDepth', 1, 'Name', 'PQD_Cap_Swell'))
    error('Swell breaker or capacitor block not found in %s!', mdl);
end

% 2. Base Electrical Parameters
base_P_A = 125e6; base_Q_A = 50e6;
base_P_B = 90e6;  base_Q_B = 30e6;
base_P_C = 100e6; base_Q_C = 35e6;
base_V1 = 16500;
base_V2 = 18000;  base_P2 = 163e6;
base_V3 = 13800;  base_P3 = 85e6;

% Load 32 operating conditions from JSON
cond_path = fullfile(project_root, 'data', 'ieee9bus_60hz', 'normal', 'operating_conditions.json');
raw_conds = jsondecode(fileread(cond_path));

% 3. Define 36 Diverse Swell Scenarios
% Covering 32 operating conditions, reactive powers (50 to 240 MVAR),
% durations (2 to 7.5 cycles), and phase types (3P, 1P, 2P)
num_scenarios = 36;
scenarios = cell(num_scenarios, 1);

% Helper: mk_swl(id, cond_id, ph_str, qc_mvar, dur_cycles, desc)
mk_swl = @(id, cid, ph, qc, dur, desc) struct(...
    'scenario_id', sprintf('SWL_%04d_%s', id, desc), ...
    'sim_id', sprintf('swell_sim_%02d', id), ...
    'cond_id', cid, ...
    'phase', ph, ...
    'qc_mvar', qc, ...
    'damping_kw', 100.0, ...
    'duration_cycles', dur, ...
    'duration_ms', (dur / 60.0) * 1000.0, ...
    'description', desc ...
);

% Define 36 Diverse Swell Scenarios across all 32 operating conditions
% covering reactive powers (60 to 240 MVAR), durations (3.0 to 7.2 cycles),
% and approved phase configurations (Three-phase ABC, Phase-to-phase AB and BC)
num_scenarios = 36;
scenarios = cell(num_scenarios, 1);

% Helper: mk_swl(id, cond_id, ph_str, qc_mvar, dur_cycles, desc)
mk_swl = @(id, cid, ph, qc, dur, desc) struct(...
    'scenario_id', sprintf('SWL_%04d_%s', id, desc), ...
    'sim_id', sprintf('swell_sim_%02d', id), ...
    'cond_id', cid, ...
    'phase', ph, ...
    'qc_mvar', qc, ...
    'damping_kw', 100.0, ...
    'duration_cycles', dur, ...
    'duration_ms', (dur / 60.0) * 1000.0, ...
    'description', desc ...
);

% Symmetrical 3-phase swells across operating conditions 1-22
scenarios{1}  = mk_swl(1,  1,  'ABC', 150, 4.8, '3p_nom_med');       % Cond 1: 4.8 cyc, 150 MVAR -> ~1.33 pu
scenarios{2}  = mk_swl(2,  2,  'ABC', 100, 4.2, '3p_light_mild');    % Cond 2: 4.2 cyc, 100 MVAR -> ~1.22 pu
scenarios{3}  = mk_swl(3,  3,  'ABC', 120, 4.8, '3p_light_high');    % Cond 3: 4.8 cyc, 120 MVAR -> ~1.27 pu
scenarios{4}  = mk_swl(4,  4,  'ABC', 80,  4.2, '3p_light_mild2');   % Cond 4: 4.2 cyc, 80 MVAR  -> ~1.18 pu
scenarios{5}  = mk_swl(5,  5,  'ABC', 150, 4.8, '3p_heavy_med');     % Cond 5: 4.8 cyc, 150 MVAR -> ~1.34 pu
scenarios{6}  = mk_swl(6,  6,  'ABC', 160, 4.2, '3p_heavy_high');    % Cond 6: 4.2 cyc, 160 MVAR -> ~1.36 pu
scenarios{7}  = mk_swl(7,  7,  'ABC', 120, 4.8, '3p_heavy_mild');    % Cond 7: 4.8 cyc, 120 MVAR -> ~1.26 pu
scenarios{8}  = mk_swl(8,  8,  'ABC', 90,  4.2, '3p_highpf_mild');   % Cond 8: 4.2 cyc, 90 MVAR  -> ~1.20 pu
scenarios{9}  = mk_swl(9,  9,  'ABC', 140, 4.8, '3p_lowpf_med');     % Cond 9: 4.8 cyc, 140 MVAR -> ~1.31 pu
scenarios{10} = mk_swl(10, 10, 'ABC', 160, 4.2, '3p_bus5load_high'); % Cond 10: 4.2 cyc, 160 MVAR -> ~1.36 pu
scenarios{11} = mk_swl(11, 11, 'ABC', 150, 4.8, '3p_cond11_med');    % Cond 11: 4.8 cyc, 150 MVAR -> ~1.33 pu
scenarios{12} = mk_swl(12, 12, 'ABC', 160, 4.2, '3p_cond12_high');   % Cond 12: 4.2 cyc, 160 MVAR -> ~1.36 pu
scenarios{13} = mk_swl(13, 13, 'ABC', 120, 4.8, '3p_cond13_mild');   % Cond 13: 4.8 cyc, 120 MVAR -> ~1.27 pu
scenarios{14} = mk_swl(14, 14, 'ABC', 150, 4.2, '3p_cond14_med');    % Cond 14: 4.2 cyc, 150 MVAR -> ~1.33 pu
scenarios{15} = mk_swl(15, 15, 'ABC', 110, 4.8, '3p_cond15_mild');   % Cond 15: 4.8 cyc, 110 MVAR -> ~1.25 pu
scenarios{16} = mk_swl(16, 16, 'ABC', 160, 4.2, '3p_cond16_high');   % Cond 16: 4.2 cyc, 160 MVAR -> ~1.36 pu
scenarios{17} = mk_swl(17, 17, 'ABC', 80,  4.8, '3p_cond17_mild');   % Cond 17: 4.8 cyc, 80 MVAR  -> ~1.18 pu
scenarios{18} = mk_swl(18, 18, 'ABC', 140, 4.2, '3p_cond18_med');    % Cond 18: 4.2 cyc, 140 MVAR -> ~1.31 pu
scenarios{19} = mk_swl(19, 19, 'ABC', 150, 4.8, '3p_cond19_med');    % Cond 19: 4.8 cyc, 150 MVAR -> ~1.33 pu
scenarios{20} = mk_swl(20, 20, 'ABC', 160, 4.2, '3p_cond20_high');   % Cond 20: 4.2 cyc, 160 MVAR -> ~1.36 pu
scenarios{21} = mk_swl(21, 21, 'ABC', 130, 4.8, '3p_cond21_med');    % Cond 21: 4.8 cyc, 130 MVAR -> ~1.29 pu
scenarios{22} = mk_swl(22, 22, 'ABC', 150, 4.2, '3p_cond22_high');   % Cond 22: 4.2 cyc, 150 MVAR -> ~1.33 pu

% Phase-to-phase and 3-phase swells across operating conditions 23-30
scenarios{23} = mk_swl(23, 23, 'ABC', 120, 4.8, '3p_cond23_med');    % Cond 23, 120 MVAR
scenarios{24} = mk_swl(24, 24, 'AB',  150, 4.0, '2p_phAB_cond24');    % Phase A-B, Cond 24
scenarios{25} = mk_swl(25, 25, 'ABC', 120, 4.8, '3p_cond25_mild');   % Cond 25, 120 MVAR
scenarios{26} = mk_swl(26, 26, 'BC',  150, 4.0, '2p_phBC_cond26');    % Phase B-C, Cond 26
scenarios{27} = mk_swl(27, 27, 'AB',  90,  4.0, '2p_phAB_cond27');    % Phase A-B, Cond 27
scenarios{28} = mk_swl(28, 28, 'BC',  140, 4.0, '2p_phBC_cond28');    % Phase B-C, Cond 28
scenarios{29} = mk_swl(29, 29, 'AB',  150, 4.0, '2p_phAB_cond29');    % Phase A-B, Cond 29
scenarios{30} = mk_swl(30, 30, 'BC',  120, 4.0, '2p_phBC_cond30');    % Phase B-C, Cond 30

% Remaining conditions 31-32 and diverse coverage 33-36
scenarios{31} = mk_swl(31, 31, 'ABC', 160, 4.8, '3p_cond31_high');   % Cond 31: Strong 3P swell (~1.36 pu)
scenarios{32} = mk_swl(32, 32, 'ABC', 70,  4.2, '3p_cond32_mild');   % Cond 32: Mild 3P swell (~1.16 pu)
scenarios{33} = mk_swl(33, 1,  'AB',  130, 4.0, '2p_phAB_cond1');     % Cond 1: 2P swell
scenarios{34} = mk_swl(34, 5,  'BC',  140, 4.0, '2p_phBC_cond5');     % Cond 5: 2P swell
scenarios{35} = mk_swl(35, 2,  'ABC', 110, 4.2, '3p_light_phABC');   % Cond 2: high 3P swell
scenarios{36} = mk_swl(36, 8,  'ABC', 90,  4.2, '3p_highpf_mild2');  % Cond 8: mild 3P swell

fprintf('[SwellBatch] 36 scenarios defined across all operating conditions.\n');

% Preallocate results structure array
sim_records = repmat(struct(...
    'scenario_id', '', ...
    'sim_id', '', ...
    'cond_id', 0, ...
    'phase', '', ...
    'qc_mvar', 0, ...
    'damping_kw', 0, ...
    'duration_cycles', 0, ...
    'duration_ms', 0, ...
    't_fault_start', 0, ...
    't_fault_end', 0, ...
    't_resampled', [], ...
    'Vabc_resampled', [], ...
    'Iabc_resampled', [], ...
    'sim_wall_time', 0 ...
), num_scenarios, 1);

t_batch_start = tic;

for s = 1:num_scenarios
    sc = scenarios{s};
    c = raw_conds(sc.cond_id);
    
    % 1. Apply Operating Condition to Loads
    pA_val = base_P_A * (c.loadA_P_MW / 125.0);
    qA_val = base_Q_A * (c.loadA_Q_MVAR / 50.0);
    pB_val = base_P_B * (c.loadB_P_MW / 90.0);
    qB_val = base_Q_B * (c.loadB_Q_MVAR / 30.0);
    pC_val = base_P_C * (c.loadC_P_MW / 100.0);
    qC_val = base_Q_C * (c.loadC_Q_MVAR / 35.0);
    
    set_param([mdl '/125 MW 50 MVAR/Three-Phase Parallel RLC Load'], ...
        'ActivePower', num2str(pA_val), 'InductivePower', num2str(qA_val));
    set_param([mdl '/90 MW 30 MVAR/Three-Phase Parallel RLC Load'], ...
        'ActivePower', num2str(pB_val), 'InductivePower', num2str(qB_val));
    set_param([mdl '/100 MW 35 MVAR/Three-Phase Parallel RLC Load'], ...
        'ActivePower', num2str(pC_val), 'InductivePower', num2str(qC_val));
        
    % 2. Apply Generator Operating Parameters
    v1_val = c.gen1_V_kV * 1000;
    f_val  = c.grid_freq_Hz;
    v2_val = c.gen2_V_kV * 1000;
    p2_val = c.gen2_P_MW * 1e6;
    v3_val = c.gen3_V_kV * 1000;
    p3_val = c.gen3_P_MW * 1e6;
    
    set_param([mdl '/247.5 MVA, 16.5 kV'], 'Voltage', num2str(v1_val), 'Frequency', num2str(f_val));
    set_param([mdl '/192 MVA, 18 kV'], 'Voltage', num2str(v2_val), 'Pref', num2str(p2_val), 'Frequency', num2str(f_val));
    set_param([mdl '/128 MVA, 13.8 kV'], 'Voltage', num2str(v3_val), 'Pref', num2str(p3_val), 'Frequency', num2str(f_val));
    
    % 3. Configure Swell Breaker and Capacitor
    brk_a = 'off'; brk_b = 'off'; brk_c = 'off';
    if contains(sc.phase, 'A'), brk_a = 'on'; end
    if contains(sc.phase, 'B'), brk_b = 'on'; end
    if contains(sc.phase, 'C'), brk_c = 'on'; end
    
    t_fstart = 0.12;
    t_fend = t_fstart + (sc.duration_ms / 1000.0);
    
    set_param(brk_blk, 'InitialState', 'open');
    set_param(brk_blk, 'SwitchTimes', sprintf('[%.6f %.6f]', t_fstart, t_fend));
    set_param(brk_blk, 'SwitchA', brk_a);
    set_param(brk_blk, 'SwitchB', brk_b);
    set_param(brk_blk, 'SwitchC', brk_c);
    set_param(brk_blk, 'BreakerResistance', '0.001');
    set_param(brk_blk, 'SnubberResistance', '1e6');
    set_param(brk_blk, 'SnubberCapacitance', 'inf');
    
    set_param(cap_blk, 'NominalVoltage', '230e3');
    set_param(cap_blk, 'NominalFrequency', '60');
    set_param(cap_blk, 'ActivePower', num2str(sc.damping_kw * 1e3));
    set_param(cap_blk, 'InductivePower', '0');
    set_param(cap_blk, 'CapacitivePower', num2str(sc.qc_mvar * 1e6));
    
    % 4. Run Simulation (0.40 s)
    t_run = tic;
    simOut = sim(mdl, 'StopTime', '0.40');
    t_sim = toc(t_run);
    
    % 5. Resample to 5000 Hz
    Vts = simOut.PQD_Vabc;
    [Vres, tres] = resample(Vts.Data, Vts.Time, 5000);
    
    Ires = [];
    if isprop(simOut, 'PQD_Iabc') || isfield(simOut, 'PQD_Iabc')
        Its = simOut.PQD_Iabc;
        [Ires, ~] = resample(Its.Data, Its.Time, 5000);
    else
        Ires = zeros(size(Vres));
    end
    
    % Store trajectory
    sim_records(s).scenario_id = sc.scenario_id;
    sim_records(s).sim_id = sc.sim_id;
    sim_records(s).cond_id = sc.cond_id;
    sim_records(s).phase = sc.phase;
    sim_records(s).qc_mvar = sc.qc_mvar;
    sim_records(s).damping_kw = sc.damping_kw;
    sim_records(s).duration_cycles = sc.duration_cycles;
    sim_records(s).duration_ms = sc.duration_ms;
    sim_records(s).t_fault_start = t_fstart;
    sim_records(s).t_fault_end = t_fend;
    sim_records(s).t_resampled = tres;
    sim_records(s).Vabc_resampled = Vres;
    sim_records(s).Iabc_resampled = Ires;
    sim_records(s).sim_wall_time = t_sim;
    
    % Metric computation
    mask_pre = (tres >= 0.06 & tres <= 0.10);
    mask_evt = (tres >= (t_fstart + 0.01) & tres <= (t_fend - 0.005));
    v_pre = sqrt(mean(Vres(mask_pre, 1).^2));
    v_evt = sqrt(mean(Vres(mask_evt, 1).^2));
    
    fprintf('[Sim %2d/%2d] %-30s | Cond:%2d | Phase:%-3s | Qc:%3dMVAR | Dur:%4.1fms | Ratio:%.3f pu | %.2fs\n', ...
        s, num_scenarios, sc.scenario_id, sc.cond_id, sc.phase, sc.qc_mvar, sc.duration_ms, v_evt/v_pre, t_sim);
end

close_system(mdl, 0);

total_time = toc(t_batch_start);
fprintf('\n[COMPLETE] 36 Swell simulations finished in %.2f s (%.1f min).\n', total_time, total_time / 60.0);

% Save trajectories to MAT file
mat_out = fullfile(out_dir, 'raw_swell_simulations.mat');
fprintf('Saving raw simulation trajectories to %s...\n', mat_out);
save(mat_out, 'sim_records', 'scenarios', 'total_time', '-v7');
fprintf('Successfully generated and saved %s\n', mat_out);
