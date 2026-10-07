% scripts/generate_ieee9bus_harmonics_dataset.m
% Generates 1,152 unique Harmonics frames across 36 distinct physical simulation scenarios
% in the IEEE 9-bus 60-Hz domain using the approved Bus 5 Controlled Current Source mechanism.

cur_dir = fileparts(mfilename('fullpath'));
project_root = fileparts(cur_dir);
addpath(fullfile(project_root, 'IEEE_9bus'));

out_dir = fullfile(project_root, 'data', 'ieee9bus_60hz', 'harmonics');
if ~exist(out_dir, 'dir')
    mkdir(out_dir);
end

% 1. Model Setup
mdl = 'IEEE_9bus_PQD_DISTURBANCES';
fprintf('[HarmonicsBatch] Loading disturbance model: %s...\n', mdl);
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

% Ensure Interruption Breaker is closed (normal conduction)
int_brk = [mdl '/PQD_Breaker_Interruption'];
if ~isempty(find_system(mdl, 'SearchDepth', 1, 'Name', 'PQD_Breaker_Interruption'))
    set_param(int_brk, 'InitialState', 'closed', 'SwitchA', 'off', 'SwitchB', 'off', 'SwitchC', 'off', ...
        'SwitchTimes', '[999 1000]');
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

% 3. Define 36 Diverse Harmonics Scenarios
% Covering 32 operating conditions, diverse harmonic combinations (H2, H3, H5, H7, H9, H11),
% phase configurations (3P ABC, 1P A/B/C, 2P AB/BC/CA), severity (THD 5.5% to 17.5%), and phase angles.
num_scenarios = 36;
scenarios = cell(num_scenarios, 1);

% Helper to create harmonic scenario definition
% mk_har(id, cond_id, phase, orders, currents, phases_rad, desc)
mk_har = @(id, cid, ph, orders, currs, phs, desc) struct(...
    'scenario_id', sprintf('HAR_%04d_%s', id, desc), ...
    'sim_id', sprintf('har_sim_%02d', id), ...
    'cond_id', cid, ...
    'phase', ph, ...
    'orders', orders, ...
    'currents', currs, ...
    'phases_rad', phs, ...
    'description', desc ...
);

% Category 1: Standard 6-pulse spectrum (H3, H5, H7) - 3-phase symmetrical (12 scenarios)
scenarios{1}  = mk_har(1,  1,  'ABC', [3,5,7],    [45.0, 28.0, 16.0],       [0, 0, 0],             '3p_h3h5h7_typical_cond01');
scenarios{2}  = mk_har(2,  2,  'ABC', [3,5,7],    [32.0, 20.0, 12.0],       [0, pi/6, pi/3],       '3p_h3h5h7_mild_cond02');
scenarios{3}  = mk_har(3,  3,  'ABC', [3,5,7],    [60.0, 38.0, 22.0],       [pi/4, 0, pi/2],       '3p_h3h5h7_heavy_cond03');
scenarios{4}  = mk_har(4,  4,  'ABC', [3,5,7],    [40.0, 25.0, 15.0],       [pi/3, pi/4, 0],       '3p_h3h5h7_typical_cond04');
scenarios{5}  = mk_har(5,  5,  'ABC', [3,5,7],    [55.0, 35.0, 20.0],       [0, pi/3, pi/6],       '3p_h3h5h7_heavy_cond05');
scenarios{6}  = mk_har(6,  6,  'ABC', [3,5,7],    [35.0, 22.0, 14.0],       [pi/6, 0, pi/4],       '3p_h3h5h7_mild_cond06');
scenarios{7}  = mk_har(7,  7,  'ABC', [3,5,7],    [65.0, 42.0, 25.0],       [pi/2, pi/3, 0],       '3p_h3h5h7_heavy_cond07');
scenarios{8}  = mk_har(8,  8,  'ABC', [3,5,7],    [48.0, 30.0, 18.0],       [0, pi/2, pi/4],       '3p_h3h5h7_typical_cond08');
scenarios{9}  = mk_har(9,  9,  'ABC', [3,5,7],    [52.0, 32.0, 19.0],       [pi/4, pi/6, 0],       '3p_h3h5h7_typical_cond09');
scenarios{10} = mk_har(10, 10, 'ABC', [3,5,7],    [70.0, 45.0, 28.0],       [0, 0, pi/3],          '3p_h3h5h7_heavy_cond10');
scenarios{11} = mk_har(11, 11, 'ABC', [3,5,7],    [38.0, 24.0, 14.0],       [pi/3, 0, pi/6],       '3p_h3h5h7_mild_cond11');
scenarios{12} = mk_har(12, 12, 'ABC', [3,5,7],    [46.0, 29.0, 17.0],       [pi/6, pi/4, 0],       '3p_h3h5h7_typical_cond12');

% Category 2: Broad spectrum including H9 and H11 (8 scenarios)
scenarios{13} = mk_har(13, 13, 'ABC', [3,5,7,9,11], [42.0, 26.0, 16.0, 10.0, 8.0], [0, 0, 0, 0, 0],           '3p_full_odd_cond13');
scenarios{14} = mk_har(14, 14, 'ABC', [3,5,7,9,11], [50.0, 32.0, 20.0, 12.0, 9.0], [pi/6, 0, pi/4, 0, pi/3],  '3p_full_odd_heavy_cond14');
scenarios{15} = mk_har(15, 15, 'ABC', [5,7,11],     [35.0, 22.0, 10.0],             [0, pi/4, pi/2],           '3p_12pulse_cond15');
scenarios{16} = mk_har(16, 16, 'ABC', [5,7,11],     [45.0, 28.0, 14.0],             [pi/3, 0, pi/6],           '3p_12pulse_heavy_cond16');
scenarios{17} = mk_har(17, 17, 'ABC', [3,5,7,9,11], [36.0, 22.0, 14.0, 8.0, 6.0],  [0, pi/3, 0, pi/4, 0],     '3p_full_odd_mild_cond17');
scenarios{18} = mk_har(18, 18, 'ABC', [5,7,9,11],   [38.0, 24.0, 11.0, 8.0],        [pi/4, 0, pi/6, pi/2],     '3p_converter_cond18');
scenarios{19} = mk_har(19, 19, 'ABC', [3,7,11],     [44.0, 20.0, 9.0],              [0, pi/2, 0],              '3p_h3h7h11_cond19');
scenarios{20} = mk_har(20, 20, 'ABC', [3,5,9,11],   [46.0, 28.0, 12.0, 8.0],        [pi/6, pi/4, 0, pi/3],     '3p_h3h5h9h11_cond20');

% Category 3: Even + Odd Harmonics including H2 (4 scenarios)
scenarios{21} = mk_har(21, 21, 'ABC', [2,3,5],       [18.0, 42.0, 25.0],             [0, 0, pi/4],              '3p_even_odd_cond21');
scenarios{22} = mk_har(22, 22, 'ABC', [2,3,5,7],     [22.0, 48.0, 30.0, 18.0],       [pi/6, 0, pi/3, 0],        '3p_even_odd_heavy_cond22');
scenarios{23} = mk_har(23, 23, 'ABC', [2,5,7],       [16.0, 34.0, 22.0],             [0, pi/4, 0],              '3p_even_h5h7_cond23');
scenarios{24} = mk_har(24, 24, 'ABC', [2,3,5,11],    [15.0, 38.0, 24.0, 8.0],        [pi/3, 0, pi/6, 0],        '3p_even_h11_cond24');

% Category 4: Single-Phase Asymmetric Harmonics (6 scenarios: 2 on A, 2 on B, 2 on C)
scenarios{25} = mk_har(25, 25, 'A',   [3,5,7],       [50.0, 30.0, 18.0],             [0, 0, 0],                 '1p_a_h3h5h7_cond25');
scenarios{26} = mk_har(26, 26, 'A',   [3,5,7,9,11],  [44.0, 26.0, 16.0, 10.0, 7.0],  [pi/4, 0, pi/6, 0, pi/3],  '1p_a_full_odd_cond26');
scenarios{27} = mk_har(27, 27, 'B',   [3,5,7],       [52.0, 32.0, 20.0],             [0, pi/3, 0],              '1p_b_h3h5h7_cond27');
scenarios{28} = mk_har(28, 28, 'B',   [2,3,5],       [20.0, 45.0, 28.0],             [pi/6, 0, pi/4],           '1p_b_even_odd_cond28');
scenarios{29} = mk_har(29, 29, 'C',   [3,5,7],       [48.0, 30.0, 18.0],             [0, 0, pi/6],              '1p_c_h3h5h7_cond29');
scenarios{30} = mk_har(30, 30, 'C',   [5,7,11],      [42.0, 26.0, 12.0],             [pi/3, pi/4, 0],           '1p_c_12pulse_cond30');

% Category 5: Two-Phase Asymmetric Harmonics (6 scenarios: 2 on AB, 2 on BC, 2 on CA)
scenarios{31} = mk_har(31, 31, 'AB',  [3,5,7],       [46.0, 28.0, 16.0],             [0, pi/6, 0],              '2p_ab_h3h5h7_cond31');
scenarios{32} = mk_har(32, 32, 'AB',  [3,5,7,9,11],  [42.0, 26.0, 15.0, 9.0, 7.0],   [pi/4, 0, pi/3, 0, pi/6],  '2p_ab_full_odd_cond32');
scenarios{33} = mk_har(33, 1,  'BC',  [3,5,7],       [50.0, 32.0, 19.0],             [0, 0, pi/4],              '2p_bc_h3h5h7_cond01');
scenarios{34} = mk_har(34, 5,  'BC',  [2,3,5,7],     [18.0, 44.0, 28.0, 16.0],       [pi/6, pi/3, 0, 0],        '2p_bc_even_odd_cond05');
scenarios{35} = mk_har(35, 10, 'CA',  [3,5,7],       [48.0, 30.0, 18.0],             [pi/3, 0, pi/6],           '2p_ca_h3h5h7_cond10');
scenarios{36} = mk_har(36, 16, 'CA',  [5,7,11],      [40.0, 25.0, 12.0],             [0, pi/4, pi/2],           '2p_ca_12pulse_cond16');

fprintf('Defined %d Harmonics scenarios:\n', num_scenarios);
fprintf(' - Three-phase (ABC): 24 scenarios\n');
fprintf(' - Single-phase (A, B, C): 6 scenarios\n');
fprintf(' - Two-phase (AB, BC, CA): 6 scenarios\n');
fprintf(' - Harmonic orders covered: H2, H3, H5, H7, H9, H11\n');
fprintf(' - Operating conditions: all 32 covered (max dominance = 5.56%%)\n');

% 4. Simulation Execution Loop
sim_records = repmat(struct(...
    'scenario_id', '', ...
    'sim_id', '', ...
    'cond_id', 0, ...
    'phase', '', ...
    'orders', [], ...
    'currents', [], ...
    'phases_rad', [], ...
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
    
    % 3. Configure Harmonic Current Injection
    t_vec = (0:1e-4:0.40)';
    w0 = 2 * pi * f_val;
    env = double(t_vec >= 0.05); % 50 ms settling, continuous steady-state thereafter
    
    ia_tot = zeros(size(t_vec));
    ib_tot = zeros(size(t_vec));
    ic_tot = zeros(size(t_vec));
    
    for k = 1:length(sc.orders)
        h = sc.orders(k);
        I_mag = sc.currents(k);
        phi   = sc.phases_rad(k);
        
        shift_b = -h * (2*pi/3);
        shift_c = +h * (2*pi/3);
        
        ia_tot = ia_tot + I_mag * sin(h * w0 * t_vec + phi);
        ib_tot = ib_tot + I_mag * sin(h * w0 * t_vec + phi + shift_b);
        ic_tot = ic_tot + I_mag * sin(h * w0 * t_vec + phi + shift_c);
    end
    
    ia = ia_tot .* env;
    ib = ib_tot .* env;
    ic = ic_tot .* env;
    
    if ~contains(sc.phase, 'A'), ia = zeros(size(t_vec)); end
    if ~contains(sc.phase, 'B'), ib = zeros(size(t_vec)); end
    if ~contains(sc.phase, 'C'), ic = zeros(size(t_vec)); end
    
    harm_inj_signal = timeseries([ia, ib, ic], t_vec);
    assignin('base', 'harm_inj_signal', harm_inj_signal);
    set_param([mdl '/PQD_Harm_Enable'], 'Value', '1');
    
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
    sim_records(s).orders = sc.orders;
    sim_records(s).currents = sc.currents;
    sim_records(s).phases_rad = sc.phases_rad;
    sim_records(s).t_resampled = tres;
    sim_records(s).Vabc_resampled = Vres;
    sim_records(s).Iabc_resampled = Ires;
    sim_records(s).sim_wall_time = t_sim;
    
    % Measure THD on Phase A
    v_a = Vres(tres >= 0.10 & tres < 0.30, 1);
    v_a = v_a(1:1000);
    fft_a = abs(fft(v_a)) * (2/1000);
    h1 = fft_a(round(60/5)+1);
    h_sum_sq = sum(fft_a(round((2:11)*60/5)+1).^2);
    thd = sqrt(h_sum_sq) / h1 * 100;
    
    fprintf('[Sim %2d/%2d] %-32s | Cond:%2d | Phase:%-3s | Orders:[%s] | THD:%5.2f%% | %.2fs\n', ...
        s, num_scenarios, sc.scenario_id, sc.cond_id, sc.phase, num2str(sc.orders), thd, t_sim);
end

% Reset Harmonics Enable to 0 (dormant default state)
set_param([mdl '/PQD_Harm_Enable'], 'Value', '0');
close_system(mdl, 0);

total_time = toc(t_batch_start);
fprintf('\n[COMPLETE] 36 Harmonics simulations finished in %.2f s (%.1f min).\n', total_time, total_time / 60.0);

% Save trajectories to MAT file
mat_out = fullfile(out_dir, 'raw_harmonics_simulations.mat');
fprintf('Saving raw simulation trajectories to %s...\n', mat_out);
save(mat_out, 'sim_records', 'scenarios', 'total_time', '-v7');
fprintf('Successfully generated and saved %s\n', mat_out);
