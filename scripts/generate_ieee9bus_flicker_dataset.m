% scripts/generate_ieee9bus_flicker_dataset.m
% Generates 1,152 unique Flicker frames across 36 distinct physical simulation scenarios
% in the IEEE 9-bus 60-Hz domain using the approved Bus 5 Controlled Dynamic Load mechanism.

cur_dir = fileparts(mfilename('fullpath'));
project_root = fileparts(cur_dir);
addpath(fullfile(project_root, 'IEEE_9bus'));

out_dir = fullfile(project_root, 'data', 'ieee9bus_60hz', 'flicker');
if ~exist(out_dir, 'dir')
    mkdir(out_dir);
end

% 1. Model Setup
mdl = 'IEEE_9bus_PQD_DISTURBANCES';
fprintf('[FlickerBatch] Loading disturbance model: %s...\n', mdl);
load_system(mdl);
set_param(mdl, 'StopFcn', '');
set_param(mdl, 'Solver', 'ode23tb');
set_param(mdl, 'RelTol', '1e-4');

% Ensure dummy signals exist in base workspace
dummy_ts = timeseries([0 0 0; 0 0 0], [0; 1]);
assignin('base', 'harm_inj_signal', dummy_ts);
assignin('base', 'flicker_inj_signal', dummy_ts);

% Ensure other disturbances are disabled
fault_blk = [mdl '/PQD_Fault_Sag'];
if ~isempty(find_system(mdl, 'SearchDepth', 1, 'Name', 'PQD_Fault_Sag'))
    set_param(fault_blk, 'FaultA', 'off', 'FaultB', 'off', 'FaultC', 'off', ...
        'GroundFault', 'off', 'SwitchTimes', '[999 1000]');
end

swl_brk = [mdl '/PQD_Breaker_Swell'];
if ~isempty(find_system(mdl, 'SearchDepth', 1, 'Name', 'PQD_Breaker_Swell'))
    set_param(swl_brk, 'InitialState', 'open', 'SwitchA', 'off', 'SwitchB', 'off', 'SwitchC', 'off', ...
        'SwitchTimes', '[999 1000]');
end

int_brk = [mdl '/PQD_Breaker_Interruption'];
if ~isempty(find_system(mdl, 'SearchDepth', 1, 'Name', 'PQD_Breaker_Interruption'))
    set_param(int_brk, 'InitialState', 'closed', 'SwitchA', 'off', 'SwitchB', 'off', 'SwitchC', 'off', ...
        'SwitchTimes', '[999 1000]');
end

if ~isempty(find_system(mdl, 'SearchDepth', 1, 'Name', 'PQD_Harm_Enable'))
    set_param([mdl '/PQD_Harm_Enable'], 'Value', '0');
end

% 2. Base Electrical Parameters
base_P_A = 125e6; base_Q_A = 50e6;
base_P_B = 90e6;  base_Q_B = 30e6;
base_P_C = 100e6; base_Q_C = 35e6;

% Load 32 operating conditions from JSON
cond_path = fullfile(project_root, 'data', 'ieee9bus_60hz', 'normal', 'operating_conditions.json');
raw_conds = jsondecode(fileread(cond_path));

% 3. Define 36 Diverse Flicker Scenarios
% Covering 32 operating conditions, diverse modulation frequencies (5.0 to 15.0 Hz, including peak sensitivity ~8.8 Hz),
% modulation depths (0.03 to 0.095, within Gate 3C range [0.02, 0.15]),
% phase configurations (3P ABC, 1P A/B/C, 2P AB/BC/CA), and modulation phase angles.
num_scenarios = 36;
scenarios = cell(num_scenarios, 1);

mk_flk = @(id, cid, ph, fm, depth, phi_rad, desc) struct(...
    'scenario_id', sprintf('FLK_%04d_%s', id, desc), ...
    'sim_id', sprintf('flk_sim_%02d', id), ...
    'cond_id', cid, ...
    'phase', ph, ...
    'fm', fm, ...
    'depth', depth, ...
    'phase_angle', phi_rad, ...
    'description', desc ...
);

% Category 1: Three-Phase Balanced Flicker (24 scenarios covering Cond 1-24)
% Spanning modulation frequency band 6.0 to 15.0 Hz, depths 3.5% to 6.5%
scenarios{1}  = mk_flk(1,   1, 'ABC', 10.0, 0.050, 0.0,       '3p_fm10hz_m05_cond01');
scenarios{2}  = mk_flk(2,   2, 'ABC',  8.8, 0.060, pi/6,      '3p_fm8p8hz_m06_cond02');
scenarios{3}  = mk_flk(3,   3, 'ABC',  6.0, 0.055, pi/4,      '3p_fm6hz_m055_cond03');
scenarios{4}  = mk_flk(4,   4, 'ABC', 12.5, 0.040, pi/3,      '3p_fm12p5hz_m04_cond04');
scenarios{5}  = mk_flk(5,   5, 'ABC',  7.0, 0.060, 0.0,       '3p_fm7hz_m06_cond05');
scenarios{6}  = mk_flk(6,   6, 'ABC', 15.0, 0.035, pi/2,      '3p_fm15hz_m035_cond06');
scenarios{7}  = mk_flk(7,   7, 'ABC',  8.8, 0.065, pi/4,      '3p_fm8p8hz_m065_cond07');
scenarios{8}  = mk_flk(8,   8, 'ABC', 11.0, 0.055, pi/6,      '3p_fm11hz_m055_cond08');
scenarios{9}  = mk_flk(9,   9, 'ABC',  6.0, 0.050, 0.0,       '3p_fm6hz_m05_cond09');
scenarios{10} = mk_flk(10, 10, 'ABC', 13.0, 0.045, pi/3,      '3p_fm13hz_m045_cond10');
scenarios{11} = mk_flk(11, 11, 'ABC',  9.5, 0.060, pi/4,      '3p_fm9p5hz_m06_cond11');
scenarios{12} = mk_flk(12, 12, 'ABC',  8.8, 0.065, 0.0,       '3p_fm8p8hz_m065_cond12');
scenarios{13} = mk_flk(13, 13, 'ABC',  6.5, 0.050, pi/6,      '3p_fm6p5hz_m05_cond13');
scenarios{14} = mk_flk(14, 14, 'ABC', 14.0, 0.038, pi/2,      '3p_fm14hz_m038_cond14');
scenarios{15} = mk_flk(15, 15, 'ABC',  7.5, 0.060, pi/4,      '3p_fm7p5hz_m06_cond15');
scenarios{16} = mk_flk(16, 16, 'ABC', 10.5, 0.055, 0.0,       '3p_fm10p5hz_m055_cond16');
scenarios{17} = mk_flk(17, 17, 'ABC',  8.8, 0.045, pi/3,      '3p_fm8p8hz_m045_cond17');
scenarios{18} = mk_flk(18, 18, 'ABC', 12.0, 0.060, pi/6,      '3p_fm12hz_m06_cond18');
scenarios{19} = mk_flk(19, 19, 'ABC',  6.5, 0.055, pi/4,      '3p_fm6p5hz_m055_cond19');
scenarios{20} = mk_flk(20, 20, 'ABC', 15.0, 0.050, 0.0,       '3p_fm15hz_m05_cond20');
scenarios{21} = mk_flk(21, 21, 'ABC',  8.0, 0.065, pi/2,      '3p_fm8hz_m065_cond21');
scenarios{22} = mk_flk(22, 22, 'ABC', 11.5, 0.040, pi/3,      '3p_fm11p5hz_m04_cond22');
scenarios{23} = mk_flk(23, 23, 'ABC',  9.0, 0.060, pi/6,      '3p_fm9hz_m06_cond23');
scenarios{24} = mk_flk(24, 24, 'ABC',  8.8, 0.055, 0.0,       '3p_fm8p8hz_m055_cond24');

% Category 2: Single-Phase Flicker (6 scenarios covering Cond 25-30)
scenarios{25} = mk_flk(25, 25, 'A',   10.0, 0.065, 0.0,       '1p_phA_fm10hz_m065_cond25');
scenarios{26} = mk_flk(26, 26, 'B',    8.8, 0.060, pi/4,      '1p_phB_fm8p8hz_m06_cond26');
scenarios{27} = mk_flk(27, 27, 'C',    7.5, 0.065, pi/3,      '1p_phC_fm7p5hz_m065_cond27');
scenarios{28} = mk_flk(28, 28, 'A',   12.0, 0.055, pi/6,      '1p_phA_fm12hz_m055_cond28');
scenarios{29} = mk_flk(29, 29, 'B',    9.0, 0.060, 0.0,       '1p_phB_fm9hz_m06_cond29');
scenarios{30} = mk_flk(30, 30, 'C',    8.8, 0.065, pi/2,      '1p_phC_fm8p8hz_m065_cond30');

% Category 3: Two-Phase Flicker (6 scenarios covering Cond 31-32, and wrap-around 1-4)
scenarios{31} = mk_flk(31, 31, 'AB',  10.0, 0.060, 0.0,       '2p_phAB_fm10hz_m06_cond31');
scenarios{32} = mk_flk(32, 32, 'BC',   8.8, 0.065, pi/4,      '2p_phBC_fm8p8hz_m065_cond32');
scenarios{33} = mk_flk(33,  1, 'CA',   7.0, 0.060, pi/3,      '2p_phCA_fm7hz_m06_cond01');
scenarios{34} = mk_flk(34,  2, 'AB',  12.5, 0.050, pi/6,      '2p_phAB_fm12p5hz_m05_cond02');
scenarios{35} = mk_flk(35,  3, 'BC',   9.5, 0.060, 0.0,       '2p_phBC_fm9p5hz_m06_cond03');
scenarios{36} = mk_flk(36,  4, 'CA',   8.8, 0.060, pi/2,      '2p_phCA_fm8p8hz_m06_cond04');

fprintf('[FlickerBatch] Prepared %d scenarios across 32 operating conditions.\n', num_scenarios);

% 4. Execution Loop
sim_records = struct();
t_batch_start = tic;

for s = 1:num_scenarios
    sc = scenarios{s};
    
    % 1. Set Operating Condition Loads
    c = raw_conds(sc.cond_id);
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
        
    % 2. Set Generator Operating Parameters
    v1_val = c.gen1_V_kV * 1000;
    f_val  = c.grid_freq_Hz;
    v2_val = c.gen2_V_kV * 1000;
    p2_val = c.gen2_P_MW * 1e6;
    v3_val = c.gen3_V_kV * 1000;
    p3_val = c.gen3_P_MW * 1e6;
    
    set_param([mdl '/247.5 MVA, 16.5 kV'], 'Voltage', num2str(v1_val), 'Frequency', num2str(f_val));
    set_param([mdl '/192 MVA, 18 kV'], 'Voltage', num2str(v2_val), 'Pref', num2str(p2_val), 'Frequency', num2str(f_val));
    set_param([mdl '/128 MVA, 13.8 kV'], 'Voltage', num2str(v3_val), 'Pref', num2str(p3_val), 'Frequency', num2str(f_val));
    
    % 3. Configure Flicker Current Injection
    t_vec = (0:1e-4:0.40)';
    w0 = 2 * pi * f_val;
    fm = sc.fm;
    depth = sc.depth;
    Im = depth * 5560.0; % Calibration for Bus 5 Thevenin impedance
    phi_m = sc.phase_angle;
    
    ia = Im * sin(2 * pi * fm * t_vec + phi_m) .* sin(w0 * t_vec);
    ib = Im * sin(2 * pi * fm * t_vec + phi_m) .* sin(w0 * t_vec - 2*pi/3);
    ic = Im * sin(2 * pi * fm * t_vec + phi_m) .* sin(w0 * t_vec + 2*pi/3);
    
    if ~contains(sc.phase, 'A'), ia = zeros(size(t_vec)); end
    if ~contains(sc.phase, 'B'), ib = zeros(size(t_vec)); end
    if ~contains(sc.phase, 'C'), ic = zeros(size(t_vec)); end
    
    flicker_inj_signal = timeseries([ia, ib, ic], t_vec);
    assignin('base', 'flicker_inj_signal', flicker_inj_signal);
    set_param([mdl '/PQD_Flicker_Enable'], 'Value', '1');
    
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
    sim_records(s).fm = sc.fm;
    sim_records(s).depth = sc.depth;
    sim_records(s).phase_angle = sc.phase_angle;
    sim_records(s).t_resampled = tres;
    sim_records(s).Vabc_resampled = Vres;
    sim_records(s).Iabc_resampled = Ires;
    sim_records(s).sim_wall_time = t_sim;
    
    % Measure envelope modulation on Phase A (or B if single-phase B)
    meas_ph = 1;
    if strcmp(sc.phase, 'B'), meas_ph = 2; end
    if strcmp(sc.phase, 'C'), meas_ph = 3; end
    v_meas = Vres(tres >= 0.10 & tres < 0.30, meas_ph);
    v_meas = v_meas(1:1000);
    env = abs(hilbert(v_meas));
    env_depth_meas = (max(env(25:end-25)) - min(env(25:end-25))) / (2 * mean(env(25:end-25)));
    
    fprintf('[Sim %2d/%2d] %-32s | Cond:%2d | Phase:%-3s | fm:%4.1fHz | depth:%4.1f%% (meas:%4.1f%%) | %.2fs\n', ...
        s, num_scenarios, sc.scenario_id, sc.cond_id, sc.phase, sc.fm, sc.depth*100, env_depth_meas*100, t_sim);
end

% Reset Flicker Enable to 0 (dormant default state)
set_param([mdl '/PQD_Flicker_Enable'], 'Value', '0');
save_system(mdl);
close_system(mdl, 0);

total_time = toc(t_batch_start);
fprintf('\n[COMPLETE] 36 Flicker simulations finished in %.2f s (%.1f min).\n', total_time, total_time / 60.0);

% Save trajectories to MAT file
mat_out = fullfile(out_dir, 'raw_flicker_simulations.mat');
fprintf('Saving raw simulation trajectories to %s...\n', mat_out);
save(mat_out, 'sim_records', 'scenarios', 'total_time', '-v7');
fprintf('Successfully generated and saved %s\n', mat_out);
