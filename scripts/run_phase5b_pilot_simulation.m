% scripts/run_phase5b_pilot_simulation.m
% Executes bounded pilot simulations for Phase 5B on IEEE_9bus_PQD_DISTURBANCES.slx.
%
% Usage:
%   matlab -batch "run_phase5b_pilot_simulation()"               % Runs all 24 pilot scenarios
%   matlab -batch "run_phase5b_pilot_simulation(1)"              % Runs only pilot scenario #1
%   matlab -batch "run_phase5b_pilot_simulation([1, 4, 7])"      % Runs specific pilots

function run_phase5b_pilot_simulation(target_pilot_ids)
    cur_dir = fileparts(mfilename('fullpath'));
    project_root = fileparts(cur_dir);
    addpath(fullfile(project_root, 'IEEE_9bus'));
    addpath(cur_dir);

    matrix_file = fullfile(project_root, 'scenarios', 'phase5b_simulation_matrix.json');
    if ~exist(matrix_file, 'file')
        error('Simulation matrix not found at: %s', matrix_file);
    end

    raw_text = fileread(matrix_file);
    catalog = jsondecode(raw_text);
    all_scenarios = catalog.scenarios;

    % Filter pilot scenarios
    pilot_scenarios = {};
    for k = 1:length(all_scenarios)
        sc = all_scenarios(k);
        if isfield(sc, 'in_pilot') && sc.in_pilot
            pilot_scenarios{end+1} = sc;
        end
    end

    num_pilots = length(pilot_scenarios);
    fprintf('Loaded %d pilot scenarios from matrix.\n', num_pilots);

    % Filter by target IDs if specified
    if nargin >= 1 && ~isempty(target_pilot_ids)
        filtered = {};
        for k = 1:num_pilots
            sc = pilot_scenarios{k};
            if ismember(sc.pilot_id, target_pilot_ids)
                filtered{end+1} = sc;
            end
        end
        pilot_scenarios = filtered;
        num_pilots = length(pilot_scenarios);
        fprintf('Executing targeted subset of %d pilot scenarios.\n', num_pilots);
    end

    out_dir = fullfile(project_root, 'data', 'ieee9bus_60hz_phase5b_pilot', 'raw');
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

    % Operating conditions catalog from JSON
    op_catalog = catalog.operating_condition_catalog;

    % Load working model in memory
    mdl = 'IEEE_9bus_PQD_DISTURBANCES';
    fprintf('[PilotRunner] Loading disturbance model: %s...\n', mdl);
    load_system(mdl);
    set_param(mdl, 'StopFcn', '');
    set_param(mdl, 'Solver', 'ode23tb');
    set_param(mdl, 'RelTol', '1e-4');

    % Base block names
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

    % Ensure dummy signals exist in base workspace
    dummy_ts = timeseries([0 0 0; 0 0 0], [0; 1]);
    assignin('base', 'harm_inj_signal', dummy_ts);
    assignin('base', 'flicker_inj_signal', dummy_ts);
    dummy_single = timeseries([0; 0], [0; 1]);
    assignin('base', 'notch_ctrl_signal', dummy_single);

    failure_log = {};
    total_tic = tic;

    for i = 1:num_pilots
        sc = pilot_scenarios{i};
        sc_id = sc.scenario_id;
        p_id = sc.pilot_id;
        cls = sc.class;
        cond_id = sc.operating_condition_id;
        ph_str = sc.phase;
        mat_path = fullfile(out_dir, [sc_id '.mat']);

        fprintf('\n-----------------------------------------------------------------\n');
        fprintf('[Pilot %d/%d] ID: %s | Class: %s | Cond: %d (%s) | Phase: %s\n', ...
            p_id, num_pilots, sc_id, cls, cond_id, sc.operating_condition_name, ph_str);
        fprintf('-----------------------------------------------------------------\n');

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
            set_param(mdl, 'MaxStep', 'auto');

            % 3. Configure Disturbance Specifics
            t_fault_start = 0.12;
            duration_s = 0.0833;
            if isfield(sc.parameters, 'duration_ms')
                duration_s = sc.parameters.duration_ms / 1000.0;
            end
            t_fault_end = t_fault_start + duration_s;

            switch cls
                case 'Normal'
                    % Pure steady-state operation: all dormant
                    t_frame_start = 0.080;
                    t_frame_end   = 0.280;

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

                    onset_s = 0.040;
                    t_frame_start = t_fault_start - onset_s;
                    t_frame_end   = t_frame_start + 0.200;

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

                    onset_s = 0.040;
                    t_frame_start = t_fault_start - onset_s;
                    t_frame_end   = t_frame_start + 0.200;

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

                    onset_s = 0.040;
                    t_frame_start = t_fault_start - onset_s;
                    t_frame_end   = t_frame_start + 0.200;

                case 'Harmonics'
                    set_param([mdl '/PQD_Harm_Enable'], 'Value', '1');
                    t_vec = (0:1e-4:0.38)';
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
                    t_frame_start = 0.090;
                    t_frame_end   = 0.290;

                case 'Flicker'
                    set_param([mdl '/PQD_Flicker_Enable'], 'Value', '1');
                    t_vec = (0:1e-4:0.38)';
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
                    t_frame_start = 0.090;
                    t_frame_end   = 0.290;

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

                    t_vec = (0:1e-5:0.38)';
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
                    set_param(mdl, 'MaxStep', '1e-4');

                    t_frame_start = 0.090;
                    t_frame_end   = 0.290;

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
                    set_param(mdl, 'MaxStep', '1e-4');

                    t_frame_start = max(0.0, t_sw_start - 0.040);
                    t_frame_end   = t_frame_start + 0.200;

                otherwise
                    error('Unknown class: %s', cls);
            end

            % 4. Run Simulink Simulation
            t_sim_start = tic;
            simOut = sim(mdl, 'StopTime', '0.38');
            t_wall = toc(t_sim_start);

            % 5. Extract and Anti-Alias Resample to 5000 Hz
            Vts = simOut.PQD_Vabc;
            [Vres, tres] = resample(Vts.Data, Vts.Time, 5000);

            Ires = zeros(size(Vres));
            if isprop(simOut, 'PQD_Iabc') || isfield(simOut, 'PQD_Iabc')
                Its = simOut.PQD_Iabc;
                [Ires, ~] = resample(Its.Data, Its.Time, 5000);
            end

            % 6. Slice Exactly 1000 Samples (200 ms)
            frame_mask = (tres >= (t_frame_start - 1e-6) & tres < (t_frame_end - 1e-6));
            V_frame = Vres(frame_mask, :);
            I_frame = Ires(frame_mask, :);
            t_frame = tres(frame_mask) - t_frame_start;

            if size(V_frame, 1) > 1000
                V_frame = V_frame(1:1000, :);
                I_frame = I_frame(1:1000, :);
                t_frame = t_frame(1:1000);
            elseif size(V_frame, 1) < 1000
                error('Frame sample count %d < 1000', size(V_frame, 1));
            end

            % Check for NaNs or Infs
            if any(isnan(V_frame(:))) || any(isinf(V_frame(:)))
                error('V_frame contains NaNs or Infs!');
            end

            % 7. Save MAT Artifact
            save(mat_path, 'V_frame', 'I_frame', 't_frame', 'sc', 't_wall', ...
                 't_frame_start', 't_frame_end', '-v7');

            fprintf('[Pilot %d Success] Wall-clock: %.2f s | Sliced: %d samples | Max V: %.3f pu | Min V: %.3f pu\n', ...
                p_id, t_wall, size(V_frame, 1), max(V_frame(:)), min(V_frame(:)));

        catch ME
            fprintf('[Pilot %d FAILURE] %s: %s\n', p_id, sc_id, ME.message);
            fail_entry = struct('pilot_id', p_id, 'scenario_id', sc_id, 'class', cls, 'error', ME.message);
            failure_log{end+1} = fail_entry;
        end
    end

    total_time = toc(total_tic);
    fprintf('\n=================================================================\n');
    fprintf('PHASE 5B PILOT GENERATION COMPLETE\n');
    fprintf('Total Pilots Attempted: %d\n', num_pilots);
    fprintf('Failures:               %d\n', length(failure_log));
    fprintf('Total Wall-Clock Time:  %.2f s (avg %.2f s/pilot)\n', total_time, total_time / max(1, num_pilots));
    fprintf('=================================================================\n');

    % Save failure log if any
    fail_file = fullfile(project_root, 'data', 'ieee9bus_60hz_phase5b_pilot', 'simulation_failure_log.json');
    if ~isempty(failure_log)
        fail_json = jsonencode(failure_log, 'PrettyPrint', true);
        fid = fopen(fail_file, 'w');
        fwrite(fid, fail_json);
        fclose(fid);
        fprintf('[Warning] Saved failure log to %s\n', fail_file);
    else
        % Empty failure log
        fid = fopen(fail_file, 'w');
        fwrite(fid, '[]');
        fclose(fid);
        fprintf('[Success] Zero simulation failures. Log recorded to %s\n', fail_file);
    end

    close_system(mdl, 0);
end
