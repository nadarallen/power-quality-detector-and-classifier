% scripts/run_phase5c_bulk_simulation.m
% Executes the 144 core trajectories for Phase 5C bulk dataset generation
% on IEEE_9bus_PQD_DISTURBANCES.slx with genuine dual-rate acquisition:
% - Continuous 20 kHz (7,601 points across 0.38s)
% - Continuous 5 kHz (1,901 points across 0.38s)
%
% Usage:
%   matlab -batch "addpath('scripts'); addpath('IEEE_9bus'); run_phase5c_bulk_simulation()"

function run_phase5c_bulk_simulation(target_trajectory_ids)
    cur_dir = fileparts(mfilename('fullpath'));
    project_root = fileparts(cur_dir);
    addpath(fullfile(project_root, 'IEEE_9bus'));
    addpath(cur_dir);

    matrix_file = fullfile(project_root, 'scenarios', 'phase5b2_simulation_matrix.json');
    if ~exist(matrix_file, 'file')
        error('Simulation matrix not found at: %s', matrix_file);
    end

    raw_text = fileread(matrix_file);
    catalog = jsondecode(raw_text);
    all_trajectories = catalog.trajectories;
    num_trajectories = length(all_trajectories);

    if nargin >= 1 && ~isempty(target_trajectory_ids)
        filtered = {};
        for k = 1:num_trajectories
            tr = all_trajectories(k);
            if ismember(tr.trajectory_id, target_trajectory_ids)
                filtered{end+1} = tr;
            end
        end
        all_trajectories = [filtered{:}];
        num_trajectories = length(all_trajectories);
        fprintf('Executing targeted subset of %d trajectories.\n', num_trajectories);
    else
        fprintf('Executing all %d core trajectories from matrix.\n', num_trajectories);
    end

    out_dir = fullfile(project_root, 'data', 'ieee9bus_60hz_phase5c', 'raw');
    if ~exist(out_dir, 'dir')
        mkdir(out_dir);
    end

    % Base Electrical Constants for IEEE 9-bus
    base_P_A = 125e6; base_Q_A = 50e6;
    base_P_B = 90e6;  base_Q_B = 30e6;
    base_P_C = 100e6; base_Q_C = 35e6;
    base_V1  = 16500;
    base_V2  = 18000; base_P2 = 163e6;
    base_V3  = 13800; base_P3 = 85e6;

    op_catalog = catalog.operating_condition_catalog;

    % Load working model in memory
    mdl = 'IEEE_9bus_PQD_DISTURBANCES';
    fprintf('[BulkRunner] Loading disturbance model: %s...\n', mdl);
    load_system(mdl);
    set_param(mdl, 'StopFcn', '');
    set_param(mdl, 'Solver', 'ode23tb');
    set_param(mdl, 'RelTol', '1e-4');
    set_param(mdl, 'MaxStep', '2.5e-5');

    % Block handles
    fault_blk = [mdl '/PQD_Fault_Sag'];
    swl_brk   = [mdl '/PQD_Breaker_Swell'];
    swl_cap   = [mdl '/PQD_Cap_Swell'];
    int_brk   = [mdl '/PQD_Breaker_Interruption'];
    trn_brk   = [mdl '/PQD_Breaker_Transient'];
    trn_rlc   = [mdl '/PQD_RLC_Transient'];
    notch_blk = [mdl '/PQD_Notch_Bus5'];

    loadA_blk = [mdl '/125 MW 50 MVAR/Three-Phase Parallel RLC Load'];
    loadB_blk = [mdl '/90 MW 30 MVAR/Three-Phase Parallel RLC Load'];
    loadC_blk = [mdl '/100 MW 35 MVAR/Three-Phase Parallel RLC Load'];
    gen1_blk  = [mdl '/247.5 MVA, 16.5 kV'];
    gen2_blk  = [mdl '/192 MVA, 18 kV'];
    gen3_blk  = [mdl '/128 MVA, 13.8 kV'];

    % Ensure dummy workspace signals exist
    dummy_ts = timeseries([0 0 0; 0 0 0], [0; 1]);
    assignin('base', 'harm_inj_signal', dummy_ts);
    assignin('base', 'flicker_inj_signal', dummy_ts);
    dummy_single = timeseries([0; 0], [0; 1]);
    assignin('base', 'notch_ctrl_signal', dummy_single);

    failure_log = {};
    total_tic = tic;
    skipped_count = 0;
    completed_count = 0;

    for i = 1:num_trajectories
        sc = all_trajectories(i);
        traj_id = sc.trajectory_id;
        cls = sc.class;
        cond_id = sc.operating_condition_id;
        ph_str = sc.phase;
        mat_path = fullfile(out_dir, [traj_id '.mat']);

        % Check if already exists and valid
        if exist(mat_path, 'file')
            try
                test_mat = load(mat_path, 'V_cont_20k');
                if isfield(test_mat, 'V_cont_20k') && size(test_mat.V_cont_20k, 1) == 7601
                    fprintf('[Sim %d/%d SKIP] %s already completed.\n', i, num_trajectories, traj_id);
                    skipped_count = skipped_count + 1;
                    continue;
                end
            catch
                % Corrupted, will re-simulate
            end
        end

        fprintf('[Sim %d/%d RUN] %s | Class: %s | Cond: %d | Phase: %s\n', ...
            i, num_trajectories, traj_id, cls, cond_id, ph_str);

        try
            % 1. Configure Operating Condition Loads and Generators
            cond_field = sprintf('x%d', cond_id);
            if isfield(op_catalog, cond_field)
                c_info = op_catalog.(cond_field);
            else
                error('Operating condition %d not found in catalog', cond_id);
            end

            pA_val = base_P_A * c_info.pA; qA_val = base_Q_A * c_info.qA;
            pB_val = base_P_B * c_info.pB; qB_val = base_Q_B * c_info.qB;
            pC_val = base_P_C * c_info.pC; qC_val = base_Q_C * c_info.qC;
            v1_val = base_V1 * c_info.v1;  f_val  = c_info.f;
            v2_val = base_V2 * c_info.v2;  p2_val = c_info.p2;
            v3_val = base_V3 * c_info.v3;  p3_val = c_info.p3;

            set_param(loadA_blk, 'ActivePower', num2str(pA_val), 'InductivePower', num2str(qA_val));
            set_param(loadB_blk, 'ActivePower', num2str(pB_val), 'InductivePower', num2str(qB_val));
            set_param(loadC_blk, 'ActivePower', num2str(pC_val), 'InductivePower', num2str(qC_val));

            set_param(gen1_blk, 'Voltage', num2str(v1_val), 'Frequency', num2str(f_val));
            set_param(gen2_blk, 'Voltage', num2str(v2_val), 'Pref', num2str(p2_val), 'Frequency', num2str(f_val));
            set_param(gen3_blk, 'Voltage', num2str(v3_val), 'Pref', num2str(p3_val), 'Frequency', num2str(f_val));

            % 2. Reset All Disturbance Blocks to Dormant State
            set_param(fault_blk, 'FaultA', 'off', 'FaultB', 'off', 'FaultC', 'off', ...
                'GroundFault', 'off', 'SwitchTimes', '[999 1000]');
            set_param(swl_brk, 'InitialState', 'open', 'SwitchA', 'off', 'SwitchB', 'off', 'SwitchC', 'off', ...
                'SwitchTimes', '[999 1000]');
            set_param(int_brk, 'InitialState', 'closed', 'SwitchA', 'off', 'SwitchB', 'off', 'SwitchC', 'off', ...
                'SwitchTimes', '[999 1000]');
            set_param([mdl '/PQD_Harm_Enable'], 'Value', '0');
            set_param([mdl '/PQD_Flicker_Enable'], 'Value', '0');
            set_param(notch_blk, 'FaultA', 'off', 'FaultB', 'off', 'FaultC', 'off', 'GroundFault', 'off');
            set_param([mdl '/PQD_Notch_Enable'], 'Value', '0');
            set_param(trn_brk, 'InitialState', 'open', 'SwitchA', 'off', 'SwitchB', 'off', 'SwitchC', 'off', ...
                'SwitchTimes', '[999 1000]');

            % 3. Configure Disturbance Specifics
            t_fault_start = 0.12;
            duration_s = 0.0833;
            if isfield(sc.parameters, 'duration_ms')
                duration_s = sc.parameters.duration_ms / 1000.0;
            end
            t_fault_end = t_fault_start + duration_s;

            switch cls
                case 'Normal'
                    % Dormant disturbance blocks

                case 'Sag'
                    fa = 'off'; fb = 'off'; fc = 'off';
                    if contains(ph_str, 'A'), fa = 'on'; end
                    if contains(ph_str, 'B'), fb = 'on'; end
                    if contains(ph_str, 'C'), fc = 'on'; end

                    set_param(fault_blk, 'FaultA', fa, 'FaultB', fb, 'FaultC', fc);
                    set_param(fault_blk, 'GroundFault', 'on');
                    set_param(fault_blk, 'SwitchTimes', sprintf('[%.6f %.6f]', t_fault_start, t_fault_end));
                    set_param(fault_blk, 'FaultResistance', num2str(sc.parameters.fault_resistance_ohms));
                    set_param(fault_blk, 'GroundResistance', num2str(sc.parameters.ground_resistance_ohms));

                case 'Swell'
                    ba = 'off'; bb = 'off'; bc = 'off';
                    if contains(ph_str, 'A'), ba = 'on'; end
                    if contains(ph_str, 'B'), bb = 'on'; end
                    if contains(ph_str, 'C'), bc = 'on'; end

                    set_param(swl_brk, 'InitialState', 'open');
                    set_param(swl_brk, 'SwitchTimes', sprintf('[%.6f %.6f]', t_fault_start, t_fault_end));
                    set_param(swl_brk, 'SwitchA', ba, 'SwitchB', bb, 'SwitchC', bc);
                    set_param(swl_brk, 'BreakerResistance', '0.001');
                    set_param(swl_brk, 'SnubberResistance', '1e6');
                    set_param(swl_brk, 'SnubberCapacitance', 'inf');

                    qc_mvar = sc.parameters.capacitive_power_mvar;
                    p_damping = sc.parameters.damping_power_kw * 1e3;
                    set_param(swl_cap, 'NominalVoltage', '230e3', 'NominalFrequency', '60');
                    set_param(swl_cap, 'ActivePower', num2str(p_damping));
                    set_param(swl_cap, 'InductivePower', '0');
                    set_param(swl_cap, 'CapacitivePower', num2str(qc_mvar * 1e6));

                case 'Interruption'
                    ba = 'off'; bb = 'off'; bc = 'off';
                    if contains(ph_str, 'A'), ba = 'on'; end
                    if contains(ph_str, 'B'), bb = 'on'; end
                    if contains(ph_str, 'C'), bc = 'on'; end

                    set_param(int_brk, 'InitialState', 'closed');
                    set_param(int_brk, 'SwitchTimes', sprintf('[%.6f %.6f]', t_fault_start, t_fault_end));
                    set_param(int_brk, 'SwitchA', ba, 'SwitchB', bb, 'SwitchC', bc);
                    set_param(int_brk, 'BreakerResistance', '0.001');
                    set_param(int_brk, 'SnubberResistance', '1e6');
                    set_param(int_brk, 'SnubberCapacitance', 'inf');

                case 'Harmonics'
                    set_param([mdl '/PQD_Harm_Enable'], 'Value', '1');
                    t_vec = (0:2.5e-5:0.38)';
                    w0 = 2 * pi * 60;
                    t_harm_start = 0.07;
                    t_harm_end   = 0.31;
                    env = double(t_vec >= t_harm_start & t_vec <= t_harm_end);

                    orders = sc.parameters.harmonic_orders;
                    ia_tot = zeros(size(t_vec));
                    ib_tot = zeros(size(t_vec));
                    ic_tot = zeros(size(t_vec));

                    for ok = 1:length(orders)
                        h = orders(ok);
                        h_key = sprintf('h%d', h);
                        I_mag = sc.parameters.harmonic_currents_amps.(h_key);
                        phi = sc.parameters.harmonic_phases_rad.(h_key);

                        shift_b = -h * (2*pi/3);
                        shift_c = +h * (2*pi/3);

                        ia_tot = ia_tot + I_mag * sin(h * w0 * t_vec + phi);
                        ib_tot = ib_tot + I_mag * sin(h * w0 * t_vec + phi + shift_b);
                        ic_tot = ic_tot + I_mag * sin(h * w0 * t_vec + phi + shift_c);
                    end

                    ia = ia_tot .* env;
                    ib = ib_tot .* env;
                    ic = ic_tot .* env;
                    if ~contains(ph_str, 'A'), ia = zeros(size(t_vec)); end
                    if ~contains(ph_str, 'B'), ib = zeros(size(t_vec)); end
                    if ~contains(ph_str, 'C'), ic = zeros(size(t_vec)); end

                    assignin('base', 'harm_inj_signal', timeseries([ia, ib, ic], t_vec));

                case 'Flicker'
                    set_param([mdl '/PQD_Flicker_Enable'], 'Value', '1');
                    t_vec = (0:2.5e-5:0.38)';
                    w0 = 2 * pi * 60;
                    fm = sc.parameters.modulation_freq_hz;
                    Im = sc.parameters.flicker_current_amps;
                    phi_m = sc.parameters.modulation_phase_rad;

                    ia = Im * sin(2 * pi * fm * t_vec + phi_m) .* sin(w0 * t_vec);
                    ib = Im * sin(2 * pi * fm * t_vec + phi_m) .* sin(w0 * t_vec - 2*pi/3);
                    ic = Im * sin(2 * pi * fm * t_vec + phi_m) .* sin(w0 * t_vec + 2*pi/3);
                    if ~contains(ph_str, 'A'), ia = zeros(size(t_vec)); end
                    if ~contains(ph_str, 'B'), ib = zeros(size(t_vec)); end
                    if ~contains(ph_str, 'C'), ic = zeros(size(t_vec)); end

                    assignin('base', 'flicker_inj_signal', timeseries([ia, ib, ic], t_vec));

                case 'Notch'
                    fa = 'off'; fb = 'off'; fc = 'off';
                    if contains(ph_str, 'A'), fa = 'on'; end
                    if contains(ph_str, 'B'), fb = 'on'; end
                    if contains(ph_str, 'C'), fc = 'on'; end

                    R_comm = sc.parameters.commutation_resistance_ohms;
                    width_s = sc.parameters.notch_width_us * 1e-6;
                    rep_per_cycle = sc.parameters.notch_repetition_per_cycle;
                    t_offset = sc.parameters.phase_offset_ms * 1e-3;

                    f0 = 60.0;
                    T0 = 1.0 / f0;
                    dt_rep = T0 / rep_per_cycle;

                    t_vec = (0:5e-6:0.38)';
                    u_notch = zeros(size(t_vec));
                    t_cur = 0.05 + t_offset;
                    while t_cur + width_s <= 0.35
                        u_notch((t_vec >= t_cur) & (t_vec < (t_cur + width_s))) = 1.0;
                        t_cur = t_cur + dt_rep;
                    end

                    assignin('base', 'notch_ctrl_signal', timeseries(u_notch, t_vec));
                    set_param(notch_blk, 'FaultA', fa, 'FaultB', fb, 'FaultC', fc);
                    if length(ph_str) == 1
                        set_param(notch_blk, 'GroundFault', 'on');
                    else
                        set_param(notch_blk, 'GroundFault', 'off');
                    end
                    set_param(notch_blk, 'FaultResistance', num2str(R_comm));
                    set_param([mdl '/PQD_Notch_Enable'], 'Value', '1');

                case 'Transient'
                    t_sw_start = sc.parameters.onset_ms / 1000.0;
                    dur_s = sc.parameters.duration_ms / 1000.0;
                    t_sw_end = t_sw_start + dur_s;

                    L_val = sc.parameters.inductance_mh * 1e-3;
                    C_val = sc.parameters.capacitance_uf * 1e-6;
                    R_val = sc.parameters.damping_resistance_ohms;

                    ba = 'off'; bb = 'off'; bc = 'off';
                    if contains(ph_str, 'A'), ba = 'on'; end
                    if contains(ph_str, 'B'), bb = 'on'; end
                    if contains(ph_str, 'C'), bc = 'on'; end

                    set_param(trn_rlc, 'Resistance', num2str(R_val), ...
                                       'Inductance', num2str(L_val), ...
                                       'Capacitance', num2str(C_val));
                    set_param(trn_brk, 'InitialState', 'open');
                    set_param(trn_brk, 'SwitchTimes', sprintf('[%.6f %.6f]', t_sw_start, t_sw_end));
                    set_param(trn_brk, 'SwitchA', ba, 'SwitchB', bb, 'SwitchC', bc);
                    set_param(trn_brk, 'BreakerResistance', '0.001');
                    set_param(trn_brk, 'SnubberResistance', '1e5');
                    set_param(trn_brk, 'SnubberCapacitance', '1e-9');

                otherwise
                    error('Unknown class: %s', cls);
            end

            % 4. Execute Simulink Simulation (0.38 s with MaxStep = 25 us)
            t_sim_start = tic;
            simOut = sim(mdl, 'StopTime', '0.38');
            t_wall = toc(t_sim_start);

            Vts = simOut.PQD_Vabc;
            has_I = isprop(simOut, 'PQD_Iabc') || isfield(simOut, 'PQD_Iabc');
            if has_I
                Its = simOut.PQD_Iabc;
            end

            diff_t = diff(Vts.Time);
            solver_stats = struct(...
                'total_solver_steps', length(Vts.Time), ...
                'min_step_us', min(diff_t) * 1e6, ...
                'max_step_us', max(diff_t) * 1e6, ...
                'mean_step_us', mean(diff_t) * 1e6, ...
                'solver_name', 'ode23tb', ...
                'configured_max_step_us', 25.0 ...
            );

            % 5. Continuous 20 kHz Resampling across full 0.38s (7,601 points)
            t_grid_20k = (0:(1/20000):0.38)';
            V_cont_20k = interp1(Vts.Time, Vts.Data, t_grid_20k, 'linear');
            if has_I
                I_cont_20k = interp1(Its.Time, Its.Data, t_grid_20k, 'linear');
            else
                I_cont_20k = zeros(size(V_cont_20k));
            end

            % 6. Continuous 5 kHz Resampling across full 0.38s (1,901 points)
            t_grid_5k = (0:(1/5000):0.38)';
            V_cont_5k = interp1(Vts.Time, Vts.Data, t_grid_5k, 'linear');
            if has_I
                I_cont_5k = interp1(Its.Time, Its.Data, t_grid_5k, 'linear');
            else
                I_cont_5k = zeros(size(V_cont_5k));
            end

            % Integrity checks
            if any(isnan(V_cont_20k(:))) || any(isinf(V_cont_20k(:)))
                error('NaN or Inf in V_cont_20k');
            end
            if any(isnan(V_cont_5k(:))) || any(isinf(V_cont_5k(:)))
                error('NaN or Inf in V_cont_5k');
            end

            % 7. Save MAT Artifact with continuous dual-rate representations
            save(mat_path, 'V_cont_20k', 'I_cont_20k', 't_grid_20k', ...
                 'V_cont_5k', 'I_cont_5k', 't_grid_5k', ...
                 'sc', 'solver_stats', 't_wall', '-v7');

            completed_count = completed_count + 1;
            fprintf(' -> [Done in %.2f s] Steps: %d (max dt: %.2f us) | Saved to %s\n', ...
                t_wall, solver_stats.total_solver_steps, solver_stats.max_step_us, traj_id);

        catch ME
            fprintf(' -> [FAILURE] %s: %s\n', traj_id, ME.message);
            fail_entry = struct('trajectory_id', traj_id, 'class', cls, 'error', ME.message);
            failure_log{end+1} = fail_entry;
        end
    end

    total_time = toc(total_tic);
    fprintf('\n=================================================================\n');
    fprintf('PHASE 5C BULK SIMULATION SUMMARY\n');
    fprintf('Total Trajectories:    %d\n', num_trajectories);
    fprintf('Newly Simulated:       %d\n', completed_count);
    fprintf('Skipped (Existing):    %d\n', skipped_count);
    fprintf('Failures:              %d\n', length(failure_log));
    fprintf('Total Wall-Clock Time: %.2f s\n', total_time);
    fprintf('=================================================================\n');

    fail_file = fullfile(project_root, 'data', 'ieee9bus_60hz_phase5c', 'simulation_failure_log.json');
    if ~isempty(failure_log)
        fail_json = jsonencode(failure_log, 'PrettyPrint', true);
        fid = fopen(fail_file, 'w');
        fwrite(fid, fail_json);
        fclose(fid);
        fprintf('[Warning] Saved failure log to %s\n', fail_file);
    else
        fid = fopen(fail_file, 'w');
        fwrite(fid, '[]');
        fclose(fid);
        fprintf('[Success] Zero simulation failures. Log recorded to %s\n', fail_file);
    end

    close_system(mdl, 0);
end
