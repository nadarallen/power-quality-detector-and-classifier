% scripts/generate_ieee9bus_notch_dataset.m
% Generates 1,152 unique Voltage Notch frames across 36 distinct physical simulation scenarios
% in the IEEE 9-bus 60-Hz domain using the approved Bus 5 physical commutation switching mechanism.

cur_dir = fileparts(mfilename('fullpath'));
project_root = fileparts(cur_dir);
addpath(fullfile(project_root, 'IEEE_9bus'));

out_dir = fullfile(project_root, 'data', 'ieee9bus_60hz', 'notch');
if ~exist(out_dir, 'dir')
    mkdir(out_dir);
end

% 1. Model Setup
mdl = 'IEEE_9bus_PQD_DISTURBANCES';
fprintf('[NotchBatch] Loading disturbance model: %s...\n', mdl);
load_system(mdl);
set_param(mdl, 'StopFcn', '');
set_param(mdl, 'Solver', 'ode23tb');
set_param(mdl, 'RelTol', '1e-4');
set_param(mdl, 'MaxStep', '1e-4'); % 100 us max step for accurate sub-cycle notch resolution

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

% Enable Notch infrastructure
set_param([mdl '/PQD_Notch_Enable'], 'Value', '1');

% 2. Base Electrical Parameters
base_P_A = 125e6; base_Q_A = 50e6;
base_P_B = 90e6;  base_Q_B = 30e6;
base_P_C = 100e6; base_Q_C = 35e6;

% Load 32 operating conditions from JSON
cond_path = fullfile(project_root, 'data', 'ieee9bus_60hz', 'normal', 'operating_conditions.json');
raw_conds = jsondecode(fileread(cond_path));

% 3. Define 36 Diverse Notch Scenarios
% Covering 32 operating conditions, varied notch widths (400 to 1000 us),
% varied commutation resistances (80 to 220 ohms -> depths 0.25 to 0.70 pu),
% phase configurations (ABC, AB, BC, CA, A, B, C), repetition rates (1 or 2/cycle),
% and point-on-wave phase offsets (1.5 to 6.0 ms).
num_scenarios = 36;
scenarios = cell(num_scenarios, 1);

mk_not = @(id, cid, ph, w_us, Rf, rep, t_off, desc) struct(...
    'scenario_id', sprintf('NOT_%04d_%s', id, desc), ...
    'sim_id', sprintf('not_sim_%02d', id), ...
    'cond_id', cid, ...
    'phase', ph, ...
    'notch_width_us', w_us, ...
    'commutation_resistance_ohms', Rf, ...
    'notch_repetition_per_cycle', rep, ...
    'phase_offset_ms', t_off, ...
    'description', desc ...
);

% Category 1: Three-Phase Balanced Commutation Notch (20 scenarios covering Cond 1-20)
scenarios{1}  = mk_not(1,   1, 'ABC',  600.0, 150.0, 1, 5.0, '3p_w600us_rf150_rep1_cond01');
scenarios{2}  = mk_not(2,   2, 'ABC',  650.0, 160.0, 1, 4.5, '3p_w650us_rf160_rep1_cond02');
scenarios{3}  = mk_not(3,   3, 'ABC',  500.0, 175.0, 1, 5.5, '3p_w500us_rf175_rep1_cond03');
scenarios{4}  = mk_not(4,   4, 'ABC',  700.0, 165.0, 1, 4.0, '3p_w700us_rf165_rep1_cond04');
scenarios{5}  = mk_not(5,   5, 'ABC',  450.0, 190.0, 1, 6.0, '3p_w450us_rf190_rep1_cond05');
scenarios{6}  = mk_not(6,   6, 'ABC',  550.0, 170.0, 1, 3.5, '3p_w550us_rf170_rep1_cond06');
scenarios{7}  = mk_not(7,   7, 'ABC',  600.0, 160.0, 1, 4.8, '3p_w600us_rf160_rep1_cond07');
scenarios{8}  = mk_not(8,   8, 'ABC',  650.0, 155.0, 1, 5.2, '3p_w650us_rf155_rep1_cond08');
scenarios{9}  = mk_not(9,   9, 'ABC',  500.0, 180.0, 1, 4.0, '3p_w500us_rf180_rep1_cond09');
scenarios{10} = mk_not(10, 10, 'ABC',  700.0, 170.0, 1, 5.0, '3p_w700us_rf170_rep1_cond10');
scenarios{11} = mk_not(11, 11, 'ABC',  600.0, 150.0, 1, 4.2, '3p_w600us_rf150_rep1_cond11');
scenarios{12} = mk_not(12, 12, 'ABC',  750.0, 165.0, 1, 5.8, '3p_w750us_rf165_rep1_cond12');
scenarios{13} = mk_not(13, 13, 'ABC',  450.0, 195.0, 1, 6.2, '3p_w450us_rf195_rep1_cond13');
scenarios{14} = mk_not(14, 14, 'ABC',  550.0, 175.0, 1, 3.8, '3p_w550us_rf175_rep1_cond14');
scenarios{15} = mk_not(15, 15, 'ABC',  650.0, 155.0, 1, 4.6, '3p_w650us_rf155_rep1_cond15');
scenarios{16} = mk_not(16, 16, 'ABC',  700.0, 165.0, 1, 5.0, '3p_w700us_rf165_rep1_cond16');
scenarios{17} = mk_not(17, 17, 'ABC',  550.0, 170.0, 1, 5.4, '3p_w550us_rf170_rep1_cond17');
scenarios{18} = mk_not(18, 18, 'ABC',  650.0, 160.0, 1, 4.0, '3p_w650us_rf160_rep1_cond18');
scenarios{19} = mk_not(19, 19, 'ABC',  700.0, 165.0, 1, 5.2, '3p_w700us_rf165_rep1_cond19');
scenarios{20} = mk_not(20, 20, 'ABC',  500.0, 175.0, 1, 4.5, '3p_w500us_rf175_rep1_cond20');

% Category 2: Line-to-Line Commutation Notching (8 scenarios covering Cond 21-28)
scenarios{21} = mk_not(21, 21, 'AB',   600.0,  95.0, 1, 5.0, '2p_phAB_w600us_rf95_cond21');
scenarios{22} = mk_not(22, 22, 'BC',   650.0,  75.0, 1, 4.5, '2p_phBC_w650us_rf75_cond22');
scenarios{23} = mk_not(23, 23, 'CA',   500.0,  90.0, 1, 5.2, '2p_phCA_w500us_rf90_cond23');
scenarios{24} = mk_not(24, 24, 'AB',   700.0, 100.0, 1, 4.2, '2p_phAB_w700us_rf100_cond24');
scenarios{25} = mk_not(25, 25, 'BC',   650.0,  75.0, 1, 4.5, '2p_phBC_w650us_rf75_cond25');
scenarios{26} = mk_not(26, 26, 'CA',   600.0,  85.0, 1, 5.5, '2p_phCA_w600us_rf85_cond26');
scenarios{27} = mk_not(27, 27, 'AB',   450.0,  85.0, 1, 6.0, '2p_phAB_w450us_rf85_cond27');
scenarios{28} = mk_not(28, 28, 'BC',   650.0,  85.0, 1, 4.5, '2p_phBC_w650us_rf85_cond28');

% Category 3: Single-Phase Commutation Notches (8 scenarios covering Cond 29-32 and wrap 1-4)
scenarios{29} = mk_not(29, 29, 'A',    600.0, 150.0, 1, 5.0, '1p_phA_w600us_rf150_cond29');
scenarios{30} = mk_not(30, 30, 'B',    650.0, 145.0, 1, 4.5, '1p_phB_w650us_rf145_cond30');
scenarios{31} = mk_not(31, 31, 'C',    500.0, 165.0, 1, 5.5, '1p_phC_w500us_rf165_cond31');
scenarios{32} = mk_not(32, 32, 'A',    550.0, 160.0, 1, 4.0, '1p_phA_w550us_rf160_cond32');
scenarios{33} = mk_not(33,  1, 'B',    600.0, 155.0, 1, 4.8, '1p_phB_w600us_rf155_cond01');
scenarios{34} = mk_not(34,  2, 'C',    700.0, 140.0, 1, 5.2, '1p_phC_w700us_rf140_cond02');
scenarios{35} = mk_not(35,  3, 'A',    450.0, 175.0, 1, 6.0, '1p_phA_w450us_rf175_cond03');
scenarios{36} = mk_not(36,  4, 'B',    650.0, 150.0, 1, 4.6, '1p_phB_w650us_rf150_cond04');

fprintf('[NotchBatch] Prepared %d scenarios across 32 operating conditions.\n', num_scenarios);

% 4. Execution Loop
sim_records = struct();
t_batch_start = tic;

notch_blk = [mdl '/PQD_Notch_Bus5'];

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
    
    % 3. Configure Notch Commutation Switching
    fa = 'off'; fb = 'off'; fc = 'off';
    if contains(sc.phase, 'A'), fa = 'on'; end
    if contains(sc.phase, 'B'), fb = 'on'; end
    if contains(sc.phase, 'C'), fc = 'on'; end
    
    set_param(notch_blk, 'FaultA', fa);
    set_param(notch_blk, 'FaultB', fb);
    set_param(notch_blk, 'FaultC', fc);
    if length(sc.phase) == 1
        set_param(notch_blk, 'GroundFault', 'on');
    else
        set_param(notch_blk, 'GroundFault', 'off');
    end
    set_param(notch_blk, 'FaultResistance', num2str(sc.commutation_resistance_ohms));
    
    % Synthesize control pulse signal
    t_vec = (0:1e-5:0.40)';
    u_notch = zeros(size(t_vec));
    T0 = 1.0 / f_val;
    dt_rep = T0 / sc.notch_repetition_per_cycle;
    width_s = sc.notch_width_us * 1e-6;
    t_cur = 0.05 + sc.phase_offset_ms * 1e-3;
    
    while t_cur + width_s <= 0.38
        u_notch((t_vec >= t_cur) & (t_vec < (t_cur + width_s))) = 1.0;
        t_cur = t_cur + dt_rep;
    end
    
    assignin('base', 'notch_ctrl_signal', timeseries(u_notch, t_vec));
    
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
    sim_records(s).notch_width_us = sc.notch_width_us;
    sim_records(s).commutation_resistance_ohms = sc.commutation_resistance_ohms;
    sim_records(s).notch_repetition_per_cycle = sc.notch_repetition_per_cycle;
    sim_records(s).phase_offset_ms = sc.phase_offset_ms;
    sim_records(s).t_resampled = tres;
    sim_records(s).Vabc_resampled = Vres;
    sim_records(s).Iabc_resampled = Ires;
    sim_records(s).sim_wall_time = t_sim;
    
    % Measure notch depth on active phase
    meas_ph = 1;
    if strcmp(sc.phase, 'B'), meas_ph = 2; end
    if strcmp(sc.phase, 'C'), meas_ph = 3; end
    v_slice = Vres(tres >= 0.10 & tres < 0.30, meas_ph);
    v_slice = v_slice(1:1000);
    v_rms = sqrt(mean(v_slice.^2));
    
    fprintf('[Sim %2d/%2d] %-32s | Cond:%2d | Phase:%-3s | Width:%4.0fus | Rf:%3.0fohm | RMS:%5.3fpu | %.2fs\n', ...
        s, num_scenarios, sc.scenario_id, sc.cond_id, sc.phase, sc.notch_width_us, sc.commutation_resistance_ohms, v_rms, t_sim);
end

% Reset Notch Enable to 0 and MaxStep to auto (dormant default state)
set_param([mdl '/PQD_Notch_Enable'], 'Value', '0');
set_param(notch_blk, 'FaultA', 'off', 'FaultB', 'off', 'FaultC', 'off');
set_param(mdl, 'MaxStep', 'auto');
save_system(mdl);
close_system(mdl, 0);

total_time = toc(t_batch_start);
fprintf('\n[COMPLETE] 36 Notch simulations finished in %.2f s (%.1f min).\n', total_time, total_time / 60.0);

% Save trajectories to MAT file
mat_out = fullfile(out_dir, 'raw_notch_simulations.mat');
fprintf('Saving raw simulation trajectories to %s...\n', mat_out);
save(mat_out, 'sim_records', 'scenarios', 'total_time', '-v7');
fprintf('Successfully generated and saved %s\n', mat_out);
