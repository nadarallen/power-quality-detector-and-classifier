% scripts/generate_ieee9bus_normal_dataset.m
% Generates normal operating waveforms from the authoritative IEEE 9-bus Simulink model.
% Non-destructive: modifies parameters only in memory via set_param, never saves to disk.

cur_dir = fileparts(mfilename('fullpath'));
project_root = fileparts(cur_dir);
addpath(fullfile(project_root, 'IEEE_9bus'));

out_dir = fullfile(project_root, 'data', 'ieee9bus_60hz', 'normal');
if ~exist(out_dir, 'dir')
    mkdir(out_dir);
end

mdl = 'IEEE_9bus_PQD_HIL_R2025a';
fprintf('Loading model: %s...\n', mdl);
load_system(fullfile(project_root, 'IEEE_9bus', mdl));

% Disable StopFcn callback in memory to prevent sending live frames during batch generation
set_param(mdl, 'StopFcn', '');

% Base parameter definitions
base_P_A = 125e6; base_Q_A = 50e6;
base_P_B = 90e6;  base_Q_B = 30e6;
base_P_C = 100e6; base_Q_C = 35e6;
base_V1 = 16500;
base_V2 = 18000;  base_P2 = 163e6;
base_V3 = 13800;  base_P3 = 85e6;

num_conditions = 32;
conditions = cell(num_conditions, 1);

% Helper to construct condition struct
mkcond = @(id, name, pA, qA, pB, qB, pC, qC, v1, f, v2, p2, v3, p3, cls, jst) ...
    struct('id', id, 'name', name, 'pA', pA, 'qA', qA, 'pB', pB, 'qB', qB, 'pC', pC, 'qC', qC, ...
           'v1', v1, 'f', f, 'v2', v2, 'p2', p2, 'v3', v3, 'p3', p3, ...
           'classification', cls, 'justification', jst);

% 1: Nominal Baseline
conditions{1} = mkcond(1, 'Nominal Baseline', 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 60.00, 1.0, 163e6, 1.0, 85e6, 'IEEE-based', 'Standard IEEE 9-bus benchmark operating point');

% 2-4: Light Load scenarios
conditions{2} = mkcond(2, 'Light Load 85%', 0.85, 0.85, 0.85, 0.85, 0.85, 0.85, 1.0, 60.00, 0.99, 138e6, 0.99, 72e6, 'PROJECT DESIGN CHOICE', 'Off-peak / nighttime system load reduction');
conditions{3} = mkcond(3, 'Light Load 90%', 0.90, 0.90, 0.90, 0.90, 0.90, 0.90, 1.0, 60.00, 0.995, 146e6, 0.995, 76e6, 'PROJECT DESIGN CHOICE', 'Mild off-peak normal grid loading');
conditions{4} = mkcond(4, 'Light Load 95%', 0.95, 0.95, 0.95, 0.95, 0.95, 0.95, 1.0, 60.00, 1.0, 155e6, 1.0, 80e6, 'PROJECT DESIGN CHOICE', 'Mid-morning load ramp transition');

% 5-7: Heavy Load scenarios
conditions{5} = mkcond(5, 'Heavy Load 105%', 1.05, 1.05, 1.05, 1.05, 1.05, 1.05, 1.0, 60.00, 1.0, 171e6, 1.0, 89e6, 'PROJECT DESIGN CHOICE', 'Normal daytime peak load growth');
conditions{6} = mkcond(6, 'Heavy Load 110%', 1.10, 1.10, 1.10, 1.10, 1.10, 1.10, 1.01, 60.00, 1.01, 175e6, 1.01, 93e6, 'PROJECT DESIGN CHOICE', 'Summer afternoon peak demand');
conditions{7} = mkcond(7, 'Heavy Load 115%', 1.15, 1.15, 1.15, 1.15, 1.15, 1.15, 1.01, 60.00, 1.01, 175e6, 1.01, 95e6, 'PROJECT DESIGN CHOICE', 'Maximum normal continuous system loading');

% 8-9: Power factor variations
conditions{8} = mkcond(8, 'High PF (0.98 lag)', 1.0, 0.60, 1.0, 0.60, 1.0, 0.60, 1.0, 60.00, 1.0, 163e6, 1.0, 85e6, 'PROJECT DESIGN CHOICE', 'Power factor correction shunt capacitors in service');
conditions{9} = mkcond(9, 'Low PF (0.85 lag)', 1.0, 1.25, 1.0, 1.25, 1.0, 1.25, 1.0, 60.00, 1.0, 163e6, 1.0, 85e6, 'PROJECT DESIGN CHOICE', 'Highly inductive industrial motor loading');

% 10-13: Local load shifts
conditions{10} = mkcond(10, 'Bus 5 Heavy Local Load', 1.15, 1.15, 1.0, 1.0, 1.0, 1.0, 1.0, 60.00, 1.0, 168e6, 1.0, 87e6, 'PROJECT DESIGN CHOICE', 'Bus 5 local industrial load increase');
conditions{11} = mkcond(11, 'Bus 5 Light Local Load', 0.85, 0.85, 1.0, 1.0, 1.0, 1.0, 1.0, 60.00, 1.0, 158e6, 1.0, 83e6, 'PROJECT DESIGN CHOICE', 'Bus 5 local industrial shutdown / weekend drop');
conditions{12} = mkcond(12, 'Bus 6 Heavy Local Load', 1.0, 1.0, 1.20, 1.20, 1.0, 1.0, 1.0, 60.00, 1.01, 170e6, 1.0, 85e6, 'PROJECT DESIGN CHOICE', 'Bus 6 regional load expansion');
conditions{13} = mkcond(13, 'Bus 8 Heavy Local Load', 1.0, 1.0, 1.0, 1.0, 1.20, 1.20, 1.0, 60.00, 1.0, 163e6, 1.01, 92e6, 'PROJECT DESIGN CHOICE', 'Bus 8 regional commercial load peak');

% 14-15: Spatial diversity
conditions{14} = mkcond(14, 'Cross-Bus Diversity A', 1.10, 1.10, 0.90, 0.90, 1.05, 1.05, 1.0, 60.00, 1.0, 163e6, 1.0, 85e6, 'PROJECT DESIGN CHOICE', 'Non-coincident load diversity pattern A');
conditions{15} = mkcond(15, 'Cross-Bus Diversity B', 0.90, 0.90, 1.10, 1.10, 0.95, 0.95, 1.0, 60.00, 1.0, 163e6, 1.0, 85e6, 'PROJECT DESIGN CHOICE', 'Non-coincident load diversity pattern B');

% 16-17: Generator redispatch
conditions{16} = mkcond(16, 'Gen 2 Heavy Dispatch', 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 60.00, 1.0, 175e6, 1.0, 75e6, 'PROJECT DESIGN CHOICE', 'Economic generation redispatch favoring Gen 2');
conditions{17} = mkcond(17, 'Gen 3 Heavy Dispatch', 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 60.00, 1.0, 150e6, 1.0, 95e6, 'PROJECT DESIGN CHOICE', 'Economic generation redispatch favoring Gen 3');

% 18-21: Voltage schedule adjustments
conditions{18} = mkcond(18, 'High Voltage Schedule (+2%)', 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.02, 60.00, 1.02, 163e6, 1.02, 85e6, 'PROJECT DESIGN CHOICE', 'Utility upper-voltage schedule for heavy-load readiness');
conditions{19} = mkcond(19, 'Low Voltage Schedule (-2%)', 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.98, 60.00, 0.98, 163e6, 0.98, 85e6, 'PROJECT DESIGN CHOICE', 'Utility lower-voltage schedule during light loading');
conditions{20} = mkcond(20, 'Gen 2 High V, Gen 3 Low V', 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 60.00, 1.015, 163e6, 0.985, 85e6, 'PROJECT DESIGN CHOICE', 'Local reactive power voltage coordination');
conditions{21} = mkcond(21, 'Gen 2 Low V, Gen 3 High V', 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 60.00, 0.985, 163e6, 1.015, 85e6, 'PROJECT DESIGN CHOICE', 'Complementary reactive power voltage coordination');

% 22-27: NERC normal frequency deadband variations (+-0.05 Hz)
conditions{22} = mkcond(22, 'Frequency Lower Bound (59.95 Hz)', 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 59.95, 1.0, 163e6, 1.0, 85e6, 'IEEE / NERC standard', 'NERC standard governor deadband lower boundary (-0.05 Hz)');
conditions{23} = mkcond(23, 'Frequency Upper Bound (60.05 Hz)', 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 60.05, 1.0, 163e6, 1.0, 85e6, 'IEEE / NERC standard', 'NERC standard governor deadband upper boundary (+0.05 Hz)');
conditions{24} = mkcond(24, 'Frequency Excursion -0.03 Hz', 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 59.97, 1.0, 163e6, 1.0, 85e6, 'IEEE / NERC standard', 'Normal continuous grid frequency regulation excursion (-0.03 Hz)');
conditions{25} = mkcond(25, 'Frequency Excursion +0.03 Hz', 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 60.03, 1.0, 163e6, 1.0, 85e6, 'IEEE / NERC standard', 'Normal continuous grid frequency regulation excursion (+0.03 Hz)');
conditions{26} = mkcond(26, 'Frequency Excursion -0.01 Hz', 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 59.99, 1.0, 163e6, 1.0, 85e6, 'IEEE / NERC standard', 'Subtle normal governor regulation deadband (-0.01 Hz)');
conditions{27} = mkcond(27, 'Frequency Excursion +0.01 Hz', 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 60.01, 1.0, 163e6, 1.0, 85e6, 'IEEE / NERC standard', 'Subtle normal governor regulation deadband (+0.01 Hz)');

% 28-32: Combined realistic operating conditions
conditions{28} = mkcond(28, 'Combined: Heavy Load + 59.97 Hz', 1.10, 1.10, 1.10, 1.10, 1.10, 1.10, 1.01, 59.97, 1.01, 175e6, 1.01, 92e6, 'PROJECT DESIGN CHOICE', 'Peak load coincident with minor grid frequency droop');
conditions{29} = mkcond(29, 'Combined: Light Load + 60.03 Hz', 0.90, 0.90, 0.90, 0.90, 0.90, 0.90, 0.99, 60.03, 0.99, 145e6, 0.99, 75e6, 'PROJECT DESIGN CHOICE', 'Off-peak load coincident with minor grid frequency rise');
conditions{30} = mkcond(30, 'Combined: Bus 5 Peak + 59.98 Hz', 1.12, 1.12, 1.0, 1.0, 1.0, 1.0, 1.0, 59.98, 1.0, 166e6, 1.0, 86e6, 'PROJECT DESIGN CHOICE', 'Local Bus 5 peak loading with slight grid frequency dip');
conditions{31} = mkcond(31, 'Combined: High Reactive + 60.02 Hz', 1.0, 1.15, 1.0, 1.15, 1.0, 1.15, 1.01, 60.02, 1.01, 163e6, 1.01, 85e6, 'PROJECT DESIGN CHOICE', 'Inductive motor loading with generator voltage support and slight frequency rise');
conditions{32} = mkcond(32, 'Combined: Gen 2 Dispatch + 59.96 Hz', 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 59.96, 1.0, 170e6, 1.0, 80e6, 'PROJECT DESIGN CHOICE', 'Generation redispatch coincident with low frequency excursion');

fprintf('Total operating conditions defined: %d\n', num_conditions);

% Preallocate results struct array
sim_results = repmat(struct(...
    'condition_id', 0, ...
    'name', '', ...
    'classification', '', ...
    'justification', '', ...
    'pA', 0, 'qA', 0, 'pB', 0, 'qB', 0, 'pC', 0, 'qC', 0, ...
    'v1', 0, 'f1', 0, 'v2', 0, 'p2', 0, 'v3', 0, 'p3', 0, ...
    't_resampled', [], ...
    'Vabc_resampled', [], ...
    'Iabc_resampled', [], ...
    'v_rms', 0, 'v_peak', 0, 'crest_factor', 0, 'sim_wall_time', 0 ...
), num_conditions, 1);

t_batch_start = tic;

for i = 1:num_conditions
    c = conditions{i};
    
    % Update Load Parameters (in memory)
    pA_val = base_P_A * c.pA; qA_val = base_Q_A * c.qA;
    pB_val = base_P_B * c.pB; qB_val = base_Q_B * c.qB;
    pC_val = base_P_C * c.pC; qC_val = base_Q_C * c.qC;
    
    set_param([mdl '/125 MW 50 MVAR/Three-Phase Parallel RLC Load'], ...
        'ActivePower', num2str(pA_val), 'InductivePower', num2str(qA_val));
    set_param([mdl '/90 MW 30 MVAR/Three-Phase Parallel RLC Load'], ...
        'ActivePower', num2str(pB_val), 'InductivePower', num2str(qB_val));
    set_param([mdl '/100 MW 35 MVAR/Three-Phase Parallel RLC Load'], ...
        'ActivePower', num2str(pC_val), 'InductivePower', num2str(qC_val));
        
    % Update Generator Parameters (in memory)
    v1_val = base_V1 * c.v1; f_val = c.f;
    v2_val = base_V2 * c.v2; p2_val = c.p2;
    v3_val = base_V3 * c.v3; p3_val = c.p3;
    
    set_param([mdl '/247.5 MVA, 16.5 kV'], 'Voltage', num2str(v1_val), 'Frequency', num2str(f_val));
    set_param([mdl '/192 MVA, 18 kV'], 'Voltage', num2str(v2_val), 'Pref', num2str(p2_val), 'Frequency', num2str(f_val));
    set_param([mdl '/128 MVA, 13.8 kV'], 'Voltage', num2str(v3_val), 'Pref', num2str(p3_val), 'Frequency', num2str(f_val));
    
    % Execute Simulation for 0.38 seconds
    t_run_start = tic;
    simOut = sim(mdl, 'StopTime', '0.38');
    t_sim = toc(t_run_start);
    
    % Extract continuous timeseries
    Vts = simOut.PQD_Vabc;
    t_raw = Vts.Time;
    V_raw = Vts.Data;
    
    I_raw = [];
    if isprop(simOut, 'PQD_Iabc') || isfield(simOut, 'PQD_Iabc')
        Its = simOut.PQD_Iabc;
        I_raw = Its.Data;
    end
    
    % Resample to uniform 5000 Hz with anti-aliasing
    target_fs = 5000;
    [Vres, tres] = resample(V_raw, t_raw, target_fs);
    if ~isempty(I_raw)
        [Ires, ~] = resample(I_raw, t_raw, target_fs);
    else
        Ires = zeros(size(Vres));
    end
    
    % Discard filter initialization transient (keep t >= 0.05 s)
    steady_mask = (tres >= 0.05);
    V_steady = Vres(steady_mask, :);
    I_steady = Ires(steady_mask, :);
    t_steady = tres(steady_mask);
    
    v_rms = sqrt(mean(V_steady(:, 1).^2));
    v_peak = max(abs(V_steady(:, 1)));
    cf = v_peak / v_rms;
    
    % Store entry
    sim_results(i).condition_id = c.id;
    sim_results(i).name = c.name;
    sim_results(i).classification = c.classification;
    sim_results(i).justification = c.justification;
    sim_results(i).pA = pA_val;
    sim_results(i).qA = qA_val;
    sim_results(i).pB = pB_val;
    sim_results(i).qB = qB_val;
    sim_results(i).pC = pC_val;
    sim_results(i).qC = qC_val;
    sim_results(i).v1 = v1_val;
    sim_results(i).f1 = f_val;
    sim_results(i).v2 = v2_val;
    sim_results(i).p2 = p2_val;
    sim_results(i).v3 = v3_val;
    sim_results(i).p3 = p3_val;
    sim_results(i).t_resampled = t_steady;
    sim_results(i).Vabc_resampled = V_steady;
    sim_results(i).Iabc_resampled = I_steady;
    sim_results(i).v_rms = v_rms;
    sim_results(i).v_peak = v_peak;
    sim_results(i).crest_factor = cf;
    sim_results(i).sim_wall_time = t_sim;
    
    fprintf('[Cond %2d/%2d] %-35s | Vrms: %.4f | Vpeak: %.4f | CF: %.4f | SimTime: %.2fs\n', ...
        i, num_conditions, c.name, v_rms, v_peak, cf, t_sim);
end

% Discard changes in memory without saving to disk
close_system(mdl, 0);
total_batch_time = toc(t_batch_start);
fprintf('\n[COMPLETE] 32 simulations finished in %.2f s (%.1f min).\n', ...
    total_batch_time, total_batch_time / 60.0);

% Save .mat file
out_mat = fullfile(out_dir, 'raw_normal_simulations.mat');
save(out_mat, 'sim_results', '-v7.3');
fprintf('[SUCCESS] Saved simulation trajectories to: %s\n', out_mat);

% Save JSON metadata
json_entries = cell(num_conditions, 1);
for i = 1:num_conditions
    e = struct();
    e.id = sim_results(i).condition_id;
    e.name = sim_results(i).name;
    e.classification = sim_results(i).classification;
    e.justification = sim_results(i).justification;
    e.loadA_P_MW = sim_results(i).pA / 1e6;
    e.loadA_Q_MVAR = sim_results(i).qA / 1e6;
    e.loadB_P_MW = sim_results(i).pB / 1e6;
    e.loadB_Q_MVAR = sim_results(i).qB / 1e6;
    e.loadC_P_MW = sim_results(i).pC / 1e6;
    e.loadC_Q_MVAR = sim_results(i).qC / 1e6;
    e.gen1_V_kV = sim_results(i).v1 / 1e3;
    e.grid_freq_Hz = sim_results(i).f1;
    e.gen2_V_kV = sim_results(i).v2 / 1e3;
    e.gen2_P_MW = sim_results(i).p2 / 1e6;
    e.gen3_V_kV = sim_results(i).v3 / 1e3;
    e.gen3_P_MW = sim_results(i).p3 / 1e6;
    e.bus5_v_rms_pu = sim_results(i).v_rms;
    e.bus5_v_peak_pu = sim_results(i).v_peak;
    e.bus5_crest_factor = sim_results(i).crest_factor;
    e.steady_samples = size(sim_results(i).Vabc_resampled, 1);
    json_entries{i} = e;
end

json_str = jsonencode(json_entries, 'PrettyPrint', true);
out_json = fullfile(out_dir, 'operating_conditions.json');
fid = fopen(out_json, 'w');
fwrite(fid, json_str);
fclose(fid);
fprintf('[SUCCESS] Saved operating conditions metadata to: %s\n', out_json);

exit(0);
