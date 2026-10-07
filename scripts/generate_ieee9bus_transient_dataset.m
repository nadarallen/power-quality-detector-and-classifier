% scripts/generate_ieee9bus_transient_dataset.m
% Generates 1,152 unique Oscillatory Transient frames across 36 distinct physical simulation scenarios
% in the IEEE 9-bus 60-Hz domain using the approved Bus 5 physical capacitor bank switching mechanism.

cur_dir = fileparts(mfilename('fullpath'));
project_root = fileparts(cur_dir);
addpath(fullfile(project_root, 'IEEE_9bus'));

out_dir = fullfile(project_root, 'data', 'ieee9bus_60hz', 'transient');
if ~exist(out_dir, 'dir')
    mkdir(out_dir);
end

% 1. Model Setup
mdl = 'IEEE_9bus_PQD_DISTURBANCES';
fprintf('[TransientBatch] Loading disturbance model: %s...\n', mdl);
load_system(mdl);
set_param(mdl, 'StopFcn', '');
set_param(mdl, 'Solver', 'ode23tb');
set_param(mdl, 'RelTol', '1e-4');
set_param(mdl, 'MaxStep', '1e-4'); % 100 us max step for accurate high-frequency transient resolution

% Ensure dummy signals exist in base workspace
dummy_ts = timeseries([0 0 0; 0 0 0], [0; 1]);
assignin('base', 'harm_inj_signal', dummy_ts);
assignin('base', 'flicker_inj_signal', dummy_ts);
dummy_single = timeseries([0; 0], [0; 1]);
assignin('base', 'notch_ctrl_signal', dummy_single);

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
if ~isempty(find_system(mdl, 'SearchDepth', 1, 'Name', 'PQD_Flicker_Enable'))
    set_param([mdl '/PQD_Flicker_Enable'], 'Value', '0');
end
if ~isempty(find_system(mdl, 'SearchDepth', 1, 'Name', 'PQD_Notch_Enable'))
    set_param([mdl '/PQD_Notch_Enable'], 'Value', '0');
end

% 2. Base Electrical Parameters
base_P_A = 125e6; base_Q_A = 50e6;
base_P_B = 90e6;  base_Q_B = 30e6;
base_P_C = 100e6; base_Q_C = 35e6;

% Load 32 operating conditions from JSON
cond_path = fullfile(project_root, 'data', 'ieee9bus_60hz', 'normal', 'operating_conditions.json');
raw_conds = jsondecode(fileread(cond_path));

% 3. Define 36 Diverse Transient Scenarios
% Covering 32 operating conditions, varied L (1.0 to 6.0 mH), varied C (1.5 to 9.0 uF),
% varied damping resistance R (0.4 to 2.5 ohms), varied switching times (0.100 to 0.160 s),
% varied durations (20 to 45 ms), and phase configurations (ABC, AB, BC, CA, A, B, C).
num_scenarios = 36;
scenarios = cell(num_scenarios, 1);

mk_trn = @(id, cid, ph, l_mh, c_uf, r_ohm, t_on, dur, desc) struct(...
    'scenario_id', sprintf('TRAN_%04d_%s', id, desc), ...
    'sim_id', sprintf('tran_sim_%02d', id), ...
    'cond_id', cid, ...
    'phase', ph, ...
    'inductance_mh', l_mh, ...
    'capacitance_uf', c_uf, ...
    'damping_resistance_ohms', r_ohm, ...
    'onset_ms', t_on, ...
    'transient_duration_ms', dur, ...
    'description', desc ...
);

% Category 1: Three-Phase Capacitor Switching (20 scenarios covering Cond 1-20)
scenarios{1}  = mk_trn(1,   1, 'ABC', 2.0, 8.0, 0.8, 104.2, 30.0, '3p_l2_c8_r08_cond01');
scenarios{2}  = mk_trn(2,   2, 'ABC', 2.5, 7.0, 0.9, 110.0, 32.0, '3p_l25_c7_r09_cond02');
scenarios{3}  = mk_trn(3,   3, 'ABC', 1.5, 6.0, 0.7, 102.5, 28.0, '3p_l15_c6_r07_cond03');
scenarios{4}  = mk_trn(4,   4, 'ABC', 3.0, 5.0, 1.2, 115.0, 35.0, '3p_l3_c5_r12_cond04');
scenarios{5}  = mk_trn(5,   5, 'ABC', 1.2, 8.5, 0.6, 108.3, 26.0, '3p_l12_c85_r06_cond05');
scenarios{6}  = mk_trn(6,   6, 'ABC', 2.2, 4.5, 1.0, 120.0, 30.0, '3p_l22_c45_r10_cond06');
scenarios{7}  = mk_trn(7,   7, 'ABC', 1.8, 7.5, 0.8, 105.0, 32.0, '3p_l18_c75_r08_cond07');
scenarios{8}  = mk_trn(8,   8, 'ABC', 2.8, 6.5, 1.1, 112.5, 34.0, '3p_l28_c65_r11_cond08');
scenarios{9}  = mk_trn(9,   9, 'ABC', 1.5, 5.5, 0.7, 101.8, 28.0, '3p_l15_c55_r07_cond09');
scenarios{10} = mk_trn(10, 10, 'ABC', 3.2, 4.0, 1.3, 118.0, 36.0, '3p_l32_c4_r13_cond10');
scenarios{11} = mk_trn(11, 11, 'ABC', 2.0, 7.0, 0.8, 106.7, 30.0, '3p_l2_c7_r08_cond11');
scenarios{12} = mk_trn(12, 12, 'ABC', 2.4, 5.0, 1.0, 114.2, 33.0, '3p_l24_c5_r10_cond12');
scenarios{13} = mk_trn(13, 13, 'ABC', 1.6, 8.0, 0.7, 103.3, 29.0, '3p_l16_c8_r07_cond13');
scenarios{14} = mk_trn(14, 14, 'ABC', 2.6, 6.0, 1.1, 111.0, 35.0, '3p_l26_c6_r11_cond14');
scenarios{15} = mk_trn(15, 15, 'ABC', 1.4, 4.5, 0.6, 122.5, 25.0, '3p_l14_c45_r06_cond15');
scenarios{16} = mk_trn(16, 16, 'ABC', 3.5, 3.5, 1.5, 116.7, 38.0, '3p_l35_c35_r15_cond16');
scenarios{17} = mk_trn(17, 17, 'ABC', 1.9, 7.8, 0.8, 107.5, 31.0, '3p_l19_c78_r08_cond17');
scenarios{18} = mk_trn(18, 18, 'ABC', 2.7, 5.2, 1.2, 113.3, 34.0, '3p_l27_c52_r12_cond18');
scenarios{19} = mk_trn(19, 19, 'ABC', 1.7, 6.8, 0.8, 104.0, 29.0, '3p_l17_c68_r08_cond19');
scenarios{20} = mk_trn(20, 20, 'ABC', 3.0, 4.2, 1.4, 119.2, 36.0, '3p_l3_c42_r14_cond20');

% Category 2: Two-Phase Switching (8 scenarios covering Cond 21-28)
scenarios{21} = mk_trn(21, 21, 'AB',  2.0, 7.5, 0.9, 105.0, 30.0, '2p_ab_l2_c75_r09_cond21');
scenarios{22} = mk_trn(22, 22, 'BC',  2.2, 6.5, 1.0, 110.5, 32.0, '2p_bc_l22_c65_r10_cond22');
scenarios{23} = mk_trn(23, 23, 'CA',  1.8, 8.0, 0.8, 103.0, 28.0, '2p_ca_l18_c8_r08_cond23');
scenarios{24} = mk_trn(24, 24, 'AB',  2.5, 5.5, 1.1, 115.0, 34.0, '2p_ab_l25_c55_r11_cond24');
scenarios{25} = mk_trn(25, 25, 'BC',  1.5, 7.0, 0.7, 108.0, 27.0, '2p_bc_l15_c7_r07_cond25');
scenarios{26} = mk_trn(26, 26, 'CA',  2.8, 4.8, 1.2, 118.5, 35.0, '2p_ca_l28_c48_r12_cond26');
scenarios{27} = mk_trn(27, 27, 'AB',  1.6, 8.2, 0.8, 104.5, 30.0, '2p_ab_l16_c82_r08_cond27');
scenarios{28} = mk_trn(28, 28, 'BC',  2.4, 5.8, 1.0, 112.0, 33.0, '2p_bc_l24_c58_r10_cond28');

% Category 3: Single-Phase Switching (8 scenarios covering Cond 29-32 plus 4 additional)
scenarios{29} = mk_trn(29, 29, 'A',   2.0, 8.0, 0.8, 104.2, 30.0, '1p_a_l2_c8_r08_cond29');
scenarios{30} = mk_trn(30, 30, 'B',   2.2, 7.2, 0.9, 109.8, 32.0, '1p_b_l22_c72_r09_cond30');
scenarios{31} = mk_trn(31, 31, 'C',   1.8, 6.8, 0.8, 106.0, 29.0, '1p_c_l18_c68_r08_cond31');
scenarios{32} = mk_trn(32, 32, 'A',   2.6, 5.0, 1.1, 116.0, 35.0, '1p_a_l26_c5_r11_cond32');
scenarios{33} = mk_trn(33,  1, 'B',   1.5, 8.5, 0.7, 102.0, 28.0, '1p_b_l15_c85_r07_cond01b');
scenarios{34} = mk_trn(34,  5, 'C',   2.4, 6.0, 1.0, 111.5, 33.0, '1p_c_l24_c6_r10_cond05b');
scenarios{35} = mk_trn(35, 12, 'A',   1.7, 7.5, 0.8, 107.2, 31.0, '1p_a_l17_c75_r08_cond12b');
scenarios{36} = mk_trn(36, 18, 'B',   2.8, 4.5, 1.2, 117.5, 34.0, '1p_b_l28_c45_r12_cond18b');

% Storage for simulation runs
sim_records = struct();
t_batch_start = tic;

trn_brk = [mdl '/PQD_Breaker_Transient'];
trn_rlc = [mdl '/PQD_RLC_Transient'];

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
    
    % 2. Configure Transient Parameters
    L_val = sc.inductance_mh * 1e-3;
    C_val = sc.capacitance_uf * 1e-6;
    R_val = sc.damping_resistance_ohms;
    t_start = sc.onset_ms * 1e-3;
    dur_s = sc.transient_duration_ms * 1e-3;
    t_end = t_start + dur_s;
    
    set_param(trn_rlc, 'Resistance', num2str(R_val), ...
                       'Inductance', num2str(L_val), ...
                       'Capacitance', num2str(C_val));
                   
    brk_a = 'off'; brk_b = 'off'; brk_c = 'off';
    if contains(sc.phase, 'A'), brk_a = 'on'; end
    if contains(sc.phase, 'B'), brk_b = 'on'; end
    if contains(sc.phase, 'C'), brk_c = 'on'; end
    
    set_param(trn_brk, 'InitialState', 'open');
    set_param(trn_brk, 'SwitchTimes', sprintf('[%.6f %.6f]', t_start, t_end));
    set_param(trn_brk, 'SwitchA', brk_a);
    set_param(trn_brk, 'SwitchB', brk_b);
    set_param(trn_brk, 'SwitchC', brk_c);
    set_param(trn_brk, 'BreakerResistance', '0.001');
    set_param(trn_brk, 'SnubberResistance', '1e5');
    set_param(trn_brk, 'SnubberCapacitance', '1e-9');
    
    % 3. Run Simulation (0.40 s)
    t_run = tic;
    simOut = sim(mdl, 'StopTime', '0.40');
    t_sim = toc(t_run);
    
    % 4. Resample to 5000 Hz
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
    sim_records(s).inductance_mh = sc.inductance_mh;
    sim_records(s).capacitance_uf = sc.capacitance_uf;
    sim_records(s).damping_resistance_ohms = sc.damping_resistance_ohms;
    sim_records(s).onset_ms = sc.onset_ms;
    sim_records(s).transient_duration_ms = sc.transient_duration_ms;
    sim_records(s).t_resampled = tres;
    sim_records(s).Vabc_resampled = Vres;
    sim_records(s).Iabc_resampled = Ires;
    sim_records(s).sim_wall_time = t_sim;
    
    % Quick peak excursion check
    meas_ph = 1;
    if strcmp(sc.phase, 'B'), meas_ph = 2; end
    if strcmp(sc.phase, 'C'), meas_ph = 3; end
    v_slice = Vres(tres >= 0.08 & tres < 0.28, meas_ph);
    v_peak = max(abs(v_slice));
    
    fprintf('[Sim %2d/%2d] %-32s | Cond:%2d | Phase:%-3s | L:%.1fmH | C:%.1fuF | R:%.1fohm | Peak:%5.3fpu | %.2fs\n', ...
        s, num_scenarios, sc.scenario_id, sc.cond_id, sc.phase, sc.inductance_mh, sc.capacitance_uf, sc.damping_resistance_ohms, v_peak, t_sim);
end

% Reset Transient Breaker to open and dormant state
set_param(trn_brk, 'SwitchTimes', '[999 1000]');
set_param(trn_brk, 'SwitchA', 'off', 'SwitchB', 'off', 'SwitchC', 'off');
set_param(mdl, 'MaxStep', 'auto');
save_system(mdl);
close_system(mdl, 0);

total_time = toc(t_batch_start);
fprintf('\n[COMPLETE] 36 Transient simulations finished in %.2f s (%.1f min).\n', total_time, total_time / 60.0);

% Save trajectories to MAT file
mat_out = fullfile(out_dir, 'raw_transient_simulations.mat');
fprintf('Saving raw simulation trajectories to %s...\n', mat_out);
save(mat_out, 'sim_records', 'scenarios', 'total_time', '-v7');
fprintf('Successfully generated and saved %s\n', mat_out);
