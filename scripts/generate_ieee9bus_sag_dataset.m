% scripts/generate_ieee9bus_sag_dataset.m
% Generates 1,152 unique Voltage Sag frames across 36 distinct simulation scenarios
% in the IEEE 9-bus 60-Hz domain using the approved Bus 4 Fault Impedance mechanism.

cur_dir = fileparts(mfilename('fullpath'));
project_root = fileparts(cur_dir);
addpath(fullfile(project_root, 'IEEE_9bus'));

out_dir = fullfile(project_root, 'data', 'ieee9bus_60hz', 'sag');
if ~exist(out_dir, 'dir')
    mkdir(out_dir);
end

% 1. Model Setup
mdl = 'IEEE_9bus_PQD_DISTURBANCES';
fprintf('[SagBatch] Loading disturbance model: %s...\n', mdl);
load_system(mdl);
set_param(mdl, 'StopFcn', '');
set_param(mdl, 'Solver', 'ode23tb');
set_param(mdl, 'RelTol', '1e-4');

fault_blk = [mdl '/PQD_Fault_Sag'];
if isempty(find_system(mdl, 'SearchDepth', 1, 'Name', 'PQD_Fault_Sag'))
    error('Block %s not found in %s!', fault_blk, mdl);
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

% 3. Define 36 Diverse Sag Scenarios
% Covering 32 operating conditions, fault resistances (25 to 280 ohms),
% durations (2 to 7.5 cycles), and phase types (3P-G, 1P-G, 2P)
num_scenarios = 36;
scenarios = cell(num_scenarios, 1);

% Scenario configuration helper:
% mk_sag(id, cond_id, ph_str, rf, dur_cycles, desc)
mk_sag = @(id, cid, ph, rf, dur, desc) struct(...
    'scenario_id', sprintf('SAG_%04d_%s', id, desc), ...
    'sim_id', sprintf('sag_sim_%02d', id), ...
    'cond_id', cid, ...
    'phase', ph, ...
    'rf', rf, ...
    'rg', 0.01, ...
    'duration_cycles', dur, ...
    'duration_ms', (dur / 60.0) * 1000.0, ...
    'description', desc ...
);

% Symmetrical 3-phase faults (Cond 1-10)
scenarios{1}  = mk_sag(1,  1,  'ABC', 180, 5.0, '3p_nom_med');       % 5 cycles, 180 ohm -> ~0.73 pu
scenarios{2}  = mk_sag(2,  2,  'ABC', 120, 4.0, '3p_light_deep');    % 4 cycles, 120 ohm -> ~0.63 pu
scenarios{3}  = mk_sag(3,  3,  'ABC', 220, 6.0, '3p_light_shallow'); % 6 cycles, 220 ohm -> ~0.78 pu
scenarios{4}  = mk_sag(4,  4,  'ABC', 80,  3.5, '3p_light_deep2');   % 3.5 cycles, 80 ohm -> ~0.52 pu
scenarios{5}  = mk_sag(5,  5,  'ABC', 150, 5.5, '3p_heavy_med');     % 5.5 cycles, 150 ohm
scenarios{6}  = mk_sag(6,  6,  'ABC', 60,  4.5, '3p_heavy_deep');    % 4.5 cycles, 60 ohm -> ~0.43 pu
scenarios{7}  = mk_sag(7,  7,  'ABC', 250, 7.0, '3p_heavy_shallow'); % 7 cycles, 250 ohm -> ~0.80 pu
scenarios{8}  = mk_sag(8,  8,  'ABC', 100, 3.0, '3p_highpf_med');    % 3 cycles, 100 ohm
scenarios{9}  = mk_sag(9,  9,  'ABC', 140, 5.0, '3p_lowpf_med');     % 5 cycles, 140 ohm
scenarios{10} = mk_sag(10, 10, 'ABC', 90,  4.0, '3p_bus5load_deep');  % 4 cycles, 90 ohm

% Single-phase-to-ground faults (Cond 11-20)
scenarios{11} = mk_sag(11, 11, 'A',   50,  4.0, '1p_phA_deep');      % Phase A to ground
scenarios{12} = mk_sag(12, 12, 'A',   100, 5.0, '1p_phA_med');
scenarios{13} = mk_sag(13, 13, 'B',   60,  4.5, '1p_phB_deep');      % Phase B to ground
scenarios{14} = mk_sag(14, 14, 'B',   120, 6.0, '1p_phB_med');
scenarios{15} = mk_sag(15, 15, 'C',   50,  3.5, '1p_phC_deep');      % Phase C to ground
scenarios{16} = mk_sag(16, 16, 'C',   110, 5.0, '1p_phC_med');
scenarios{17} = mk_sag(17, 17, 'A',   160, 6.5, '1p_phA_shallow');
scenarios{18} = mk_sag(18, 18, 'B',   80,  4.0, '1p_phB_med2');
scenarios{19} = mk_sag(19, 19, 'C',   70,  5.0, '1p_phC_med2');
scenarios{20} = mk_sag(20, 20, 'A',   40,  3.0, '1p_phA_deep2');

% Phase-to-phase faults (Cond 21-28)
scenarios{21} = mk_sag(21, 21, 'AB',  70,  4.0, '2p_phAB_med');      % Phase A-B
scenarios{22} = mk_sag(22, 22, 'AB',  130, 5.5, '2p_phAB_shallow');
scenarios{23} = mk_sag(23, 23, 'BC',  60,  3.5, '2p_phBC_deep');     % Phase B-C
scenarios{24} = mk_sag(24, 24, 'BC',  110, 5.0, '2p_phBC_med');
scenarios{25} = mk_sag(25, 25, 'CA',  75,  4.5, '2p_phCA_med');      % Phase C-A
scenarios{26} = mk_sag(26, 26, 'CA',  140, 6.0, '2p_phCA_shallow');
scenarios{27} = mk_sag(27, 27, 'AB',  45,  3.0, '2p_phAB_deep');
scenarios{28} = mk_sag(28, 28, 'BC',  85,  4.0, '2p_phBC_med2');

% Boundary & Diverse operating conditions (Cond 29-36)
scenarios{29} = mk_sag(29, 29, 'ABC', 35,  2.5, '3p_very_deep');     % Deepest 3P sag (~0.30 pu)
scenarios{30} = mk_sag(30, 30, 'ABC', 280, 7.5, '3p_very_shallow');  % Very shallow sag (~0.83 pu)
scenarios{31} = mk_sag(31, 31, 'A',   30,  2.0, '1p_phA_fast');      % Fast 2-cycle sag
scenarios{32} = mk_sag(32, 32, 'BC',  160, 6.5, '2p_phBC_long');     % Long 6.5-cycle sag
scenarios{33} = mk_sag(33, 1,  'ABC', 75,  4.0, '3p_nom_deep');       % Re-sample baseline with deep sag
scenarios{34} = mk_sag(34, 5,  'A',   90,  5.0, '1p_heavy_phA');     % Heavy load phA sag
scenarios{35} = mk_sag(35, 2,  'CA',  95,  4.0, '2p_light_phCA');    % Light load phCA sag
scenarios{36} = mk_sag(36, 8,  'ABC', 200, 5.5, '3p_highpf_shallow'); % High PF shallow sag

fprintf('[SagBatch] 36 scenarios defined across all operating conditions.\n');

% Preallocate results structure array
sim_records = repmat(struct(...
    'scenario_id', '', ...
    'sim_id', '', ...
    'cond_id', 0, ...
    'phase', '', ...
    'rf', 0, ...
    'rg', 0, ...
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
    
    % 3. Configure Fault Block
    fault_a = 'off'; fault_b = 'off'; fault_c = 'off';
    if contains(sc.phase, 'A'), fault_a = 'on'; end
    if contains(sc.phase, 'B'), fault_b = 'on'; end
    if contains(sc.phase, 'C'), fault_c = 'on'; end
    
    % Ground fault is on for 3P-G and 1P-G; off for 2P (phase-to-phase)
    ground_fault = 'on';
    if length(sc.phase) == 2
        ground_fault = 'off';
    end
    
    t_fstart = 0.12;
    t_fend = t_fstart + (sc.duration_ms / 1000.0);
    
    set_param(fault_blk, 'FaultA', fault_a);
    set_param(fault_blk, 'FaultB', fault_b);
    set_param(fault_blk, 'FaultC', fault_c);
    set_param(fault_blk, 'GroundFault', ground_fault);
    set_param(fault_blk, 'SwitchTimes', sprintf('[%.6f %.6f]', t_fstart, t_fend));
    set_param(fault_blk, 'FaultResistance', num2str(sc.rf));
    set_param(fault_blk, 'GroundResistance', num2str(sc.rg));
    
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
    sim_records(s).rf = sc.rf;
    sim_records(s).rg = sc.rg;
    sim_records(s).duration_cycles = sc.duration_cycles;
    sim_records(s).duration_ms = sc.duration_ms;
    sim_records(s).t_fault_start = t_fstart;
    sim_records(s).t_fault_end = t_fend;
    sim_records(s).t_resampled = tres;
    sim_records(s).Vabc_resampled = Vres;
    sim_records(s).Iabc_resampled = Ires;
    sim_records(s).sim_wall_time = t_sim;
    
    % Quick metric computation
    mask_pre = (tres >= 0.06 & tres <= 0.10);
    mask_evt = (tres >= (t_fstart + 0.01) & tres <= (t_fend - 0.005));
    v_pre = sqrt(mean(Vres(mask_pre, 1).^2));
    v_evt = sqrt(mean(Vres(mask_evt, 1).^2));
    
    fprintf('[Sim %2d/%2d] %-30s | Cond:%2d | Phase:%-3s | Rf:%3dΩ | Dur:%4.1fms | Res:%.2f pu (%.1f%%) | %.2fs\n', ...
        s, num_scenarios, sc.scenario_id, sc.cond_id, sc.phase, sc.rf, sc.duration_ms, v_evt/v_pre, (v_evt/v_pre)*100, t_sim);
end

close_system(mdl, 0);

total_time = toc(t_batch_start);
fprintf('\n[COMPLETE] 36 simulations finished in %.2f s (%.1f min).\n', total_time, total_time / 60.0);

% Save trajectories to MAT file
mat_out = fullfile(out_dir, 'raw_sag_simulations.mat');
fprintf('Saving raw simulation trajectories to %s...\n', mat_out);
save(mat_out, 'sim_records', 'scenarios', 'total_time', '-v7');
fprintf('Successfully saved.\n');
