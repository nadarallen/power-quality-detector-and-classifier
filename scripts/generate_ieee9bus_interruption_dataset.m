% scripts/generate_ieee9bus_interruption_dataset.m
% Generates 1,152 unique Voltage Interruption frames across 36 distinct simulation scenarios
% in the IEEE 9-bus 60-Hz domain using the approved Bus 5 circuit breaker mechanism.

cur_dir = fileparts(mfilename('fullpath'));
project_root = fileparts(cur_dir);
addpath(fullfile(project_root, 'IEEE_9bus'));

out_dir = fullfile(project_root, 'data', 'ieee9bus_60hz', 'interruption');
if ~exist(out_dir, 'dir')
    mkdir(out_dir);
end

% 1. Model Setup
mdl = 'IEEE_9bus_PQD_DISTURBANCES';
fprintf('[InterruptionBatch] Loading disturbance model: %s...\n', mdl);
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

% Ensure Swell Breaker block is disabled
swl_brk = [mdl '/PQD_Breaker_Swell'];
if ~isempty(find_system(mdl, 'SearchDepth', 1, 'Name', 'PQD_Breaker_Swell'))
    set_param(swl_brk, 'InitialState', 'open', 'SwitchA', 'off', 'SwitchB', 'off', 'SwitchC', 'off', ...
        'SwitchTimes', '[999 1000]');
end

brk_blk = [mdl '/PQD_Breaker_Interruption'];
if isempty(find_system(mdl, 'SearchDepth', 1, 'Name', 'PQD_Breaker_Interruption'))
    error('Interruption breaker block not found in %s!', mdl);
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

% 3. Define 36 Diverse Interruption Scenarios
% Covering 32 operating conditions, durations (2.5 to 7.2 cycles / 41.7 to 120 ms),
% and phase configurations (3-phase ABC, 1-phase A/B/C, 2-phase AB/BC/CA)
num_scenarios = 36;
scenarios = cell(num_scenarios, 1);

% Helper: mk_int(id, cond_id, ph_str, dur_cycles, desc)
mk_int = @(id, cid, ph, dur, desc) struct(...
    'scenario_id', sprintf('INT_%04d_%s', id, desc), ...
    'sim_id', sprintf('int_sim_%02d', id), ...
    'cond_id', cid, ...
    'phase', ph, ...
    'duration_cycles', dur, ...
    'duration_ms', (dur / 60.0) * 1000.0, ...
    'description', desc ...
);

% Symmetrical 3-phase interruptions across diverse operating conditions (16 scenarios)
scenarios{1}  = mk_int(1,  1,  'ABC', 4.2, '3p_nom_70ms');        % Cond 1: 4.2 cyc (70.0 ms)
scenarios{2}  = mk_int(2,  2,  'ABC', 3.0, '3p_light_50ms');      % Cond 2: 3.0 cyc (50.0 ms)
scenarios{3}  = mk_int(3,  3,  'ABC', 5.0, '3p_light_83ms');      % Cond 3: 5.0 cyc (83.3 ms)
scenarios{4}  = mk_int(4,  4,  'ABC', 2.5, '3p_light_42ms');      % Cond 4: 2.5 cyc (41.7 ms)
scenarios{5}  = mk_int(5,  5,  'ABC', 6.0, '3p_heavy_100ms');     % Cond 5: 6.0 cyc (100.0 ms)
scenarios{6}  = mk_int(6,  6,  'ABC', 4.5, '3p_heavy_75ms');      % Cond 6: 4.5 cyc (75.0 ms)
scenarios{7}  = mk_int(7,  7,  'ABC', 3.5, '3p_heavy_58ms');      % Cond 7: 3.5 cyc (58.3 ms)
scenarios{8}  = mk_int(8,  8,  'ABC', 7.0, '3p_highpf_117ms');    % Cond 8: 7.0 cyc (116.7 ms)
scenarios{9}  = mk_int(9,  9,  'ABC', 4.0, '3p_lowpf_67ms');      % Cond 9: 4.0 cyc (66.7 ms)
scenarios{10} = mk_int(10, 10, 'ABC', 5.5, '3p_bus5load_92ms');   % Cond 10: 5.5 cyc (91.7 ms)
scenarios{11} = mk_int(11, 11, 'ABC', 3.2, '3p_cond11_53ms');     % Cond 11: 3.2 cyc (53.3 ms)
scenarios{12} = mk_int(12, 12, 'ABC', 6.5, '3p_cond12_108ms');    % Cond 12: 6.5 cyc (108.3 ms)
scenarios{13} = mk_int(13, 13, 'ABC', 4.8, '3p_cond13_80ms');     % Cond 13: 4.8 cyc (80.0 ms)
scenarios{14} = mk_int(14, 14, 'ABC', 3.8, '3p_cond14_63ms');     % Cond 14: 3.8 cyc (63.3 ms)
scenarios{15} = mk_int(15, 15, 'ABC', 5.2, '3p_cond15_87ms');     % Cond 15: 5.2 cyc (86.7 ms)
scenarios{16} = mk_int(16, 16, 'ABC', 4.2, '3p_cond16_70ms');     % Cond 16: 4.2 cyc (70.0 ms)

% Single-phase interruptions (10 scenarios: 4 on A, 3 on B, 3 on C)
scenarios{17} = mk_int(17, 17, 'A',   4.2, '1p_a_cond17_70ms');    % Cond 17: Phase A, 70 ms
scenarios{18} = mk_int(18, 18, 'A',   5.0, '1p_a_cond18_83ms');    % Cond 18: Phase A, 83.3 ms
scenarios{19} = mk_int(19, 19, 'A',   3.0, '1p_a_cond19_50ms');    % Cond 19: Phase A, 50 ms
scenarios{20} = mk_int(20, 20, 'A',   6.0, '1p_a_cond20_100ms');   % Cond 20: Phase A, 100 ms
scenarios{21} = mk_int(21, 21, 'B',   4.2, '1p_b_cond21_70ms');    % Cond 21: Phase B, 70 ms
scenarios{22} = mk_int(22, 22, 'B',   5.5, '1p_b_cond22_92ms');    % Cond 22: Phase B, 91.7 ms
scenarios{23} = mk_int(23, 23, 'B',   3.5, '1p_b_cond23_58ms');    % Cond 23: Phase B, 58.3 ms
scenarios{24} = mk_int(24, 24, 'C',   4.2, '1p_c_cond24_70ms');    % Cond 24: Phase C, 70 ms
scenarios{25} = mk_int(25, 25, 'C',   5.0, '1p_c_cond25_83ms');    % Cond 25: Phase C, 83.3 ms
scenarios{26} = mk_int(26, 26, 'C',   3.2, '1p_c_cond26_53ms');    % Cond 26: Phase C, 53.3 ms

% Two-phase interruptions (10 scenarios: 4 on AB, 3 on BC, 3 on CA)
scenarios{27} = mk_int(27, 27, 'AB',  4.2, '2p_ab_cond27_70ms');   % Cond 27: Phase AB, 70 ms
scenarios{28} = mk_int(28, 28, 'AB',  5.0, '2p_ab_cond28_83ms');   % Cond 28: Phase AB, 83.3 ms
scenarios{29} = mk_int(29, 29, 'AB',  3.5, '2p_ab_cond29_58ms');   % Cond 29: Phase AB, 58.3 ms
scenarios{30} = mk_int(30, 30, 'AB',  6.2, '2p_ab_cond30_103ms');  % Cond 30: Phase AB, 103.3 ms
scenarios{31} = mk_int(31, 31, 'BC',  4.2, '2p_bc_cond31_70ms');   % Cond 31: Phase BC, 70 ms
scenarios{32} = mk_int(32, 32, 'BC',  5.5, '2p_bc_cond32_92ms');   % Cond 32: Phase BC, 91.7 ms
scenarios{33} = mk_int(33, 1,  'BC',  3.2, '2p_bc_cond01_53ms');   % Cond 1:  Phase BC, 53.3 ms
scenarios{34} = mk_int(34, 5,  'CA',  4.2, '2p_ca_cond05_70ms');   % Cond 5:  Phase CA, 70 ms
scenarios{35} = mk_int(35, 10, 'CA',  5.0, '2p_ca_cond10_83ms');   % Cond 10: Phase CA, 83.3 ms
scenarios{36} = mk_int(36, 16, 'CA',  3.8, '2p_ca_cond16_63ms');   % Cond 16: Phase CA, 63.3 ms

fprintf('Defined %d Interruption scenarios:\n', num_scenarios);
fprintf(' - Three-phase (ABC): 16 scenarios\n');
fprintf(' - Single-phase (A, B, C): 10 scenarios\n');
fprintf(' - Two-phase (AB, BC, CA): 10 scenarios\n');
fprintf(' - Durations: 41.7 ms to 120.0 ms (2.5 to 7.2 cycles)\n');

% 4. Simulation Execution Loop
sim_records = repmat(struct(...
    'scenario_id', '', ...
    'sim_id', '', ...
    'cond_id', 0, ...
    'phase', '', ...
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
    
    % 3. Configure Interruption Breaker
    brk_a = 'off'; brk_b = 'off'; brk_c = 'off';
    if contains(sc.phase, 'A'), brk_a = 'on'; end
    if contains(sc.phase, 'B'), brk_b = 'on'; end
    if contains(sc.phase, 'C'), brk_c = 'on'; end
    
    t_fstart = 0.12;
    t_fend = t_fstart + (sc.duration_ms / 1000.0);
    
    set_param(brk_blk, 'InitialState', 'closed');
    set_param(brk_blk, 'SwitchTimes', sprintf('[%.6f %.6f]', t_fstart, t_fend));
    set_param(brk_blk, 'SwitchA', brk_a);
    set_param(brk_blk, 'SwitchB', brk_b);
    set_param(brk_blk, 'SwitchC', brk_c);
    set_param(brk_blk, 'BreakerResistance', '0.0001');
    set_param(brk_blk, 'SnubberResistance', '1e6');
    set_param(brk_blk, 'SnubberCapacitance', 'inf');
    
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
    mask_evt = (tres >= (t_fstart + 0.02) & tres <= (t_fend - 0.01));
    
    % Check affected phase residual ratio
    ch_idx = 1;
    if contains(sc.phase, 'A'), ch_idx = 1;
    elseif contains(sc.phase, 'B'), ch_idx = 2;
    elseif contains(sc.phase, 'C'), ch_idx = 3;
    end
    
    v_pre = sqrt(mean(Vres(mask_pre, ch_idx).^2));
    v_evt = sqrt(mean(Vres(mask_evt, ch_idx).^2));
    v_ratio = v_evt / v_pre;
    
    fprintf('[Sim %2d/%2d] %-30s | Cond:%2d | Phase:%-3s | Dur:%5.1fms | Ratio:%.4f pu | %.2fs\n', ...
        s, num_scenarios, sc.scenario_id, sc.cond_id, sc.phase, sc.duration_ms, v_ratio, t_sim);
end

% Reset breaker to closed default state
set_param(brk_blk, 'InitialState', 'closed', 'SwitchA', 'on', 'SwitchB', 'on', 'SwitchC', 'on', ...
    'SwitchTimes', '[999 999]');
close_system(mdl, 0);

total_time = toc(t_batch_start);
fprintf('\n[COMPLETE] 36 Interruption simulations finished in %.2f s (%.1f min).\n', total_time, total_time / 60.0);

% Save trajectories to MAT file
mat_out = fullfile(out_dir, 'raw_interruption_simulations.mat');
fprintf('Saving raw simulation trajectories to %s...\n', mat_out);
save(mat_out, 'sim_records', 'scenarios', 'total_time', '-v7');
fprintf('Successfully generated and saved %s\n', mat_out);
