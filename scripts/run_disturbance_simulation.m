% scripts/run_disturbance_simulation.m
% Executes a single disturbance scenario on IEEE_9bus_PQD_DISTURBANCES.slx
% Usage: matlab -batch "run_disturbance_simulation('scenarios/definitions/SAG_0001_three_phase_symmetric.json', 'data/ieee9bus_60hz/sag/raw_sim_sag_0001.mat')"

function run_disturbance_simulation(scenario_json_path, output_mat_path)
    if nargin < 1
        scenario_json_path = 'scenarios/definitions/SAG_0001_three_phase_symmetric.json';
    end
    if nargin < 2
        output_mat_path = 'data/ieee9bus_60hz/sag/raw_sim_sag_0001.mat';
    end

    cur_dir = fileparts(mfilename('fullpath'));
    project_root = fileparts(cur_dir);
    addpath(fullfile(project_root, 'IEEE_9bus'));

    % Ensure output directory exists
    out_dir = fileparts(output_mat_path);
    if ~exist(out_dir, 'dir')
        mkdir(out_dir);
    end

    fprintf('[SimRunner] Reading scenario: %s\n', scenario_json_path);
    raw_text = fileread(scenario_json_path);
    scen = jsondecode(raw_text);

    mdl = 'IEEE_9bus_PQD_DISTURBANCES';
    load_system(mdl);
    set_param(mdl, 'StopFcn', '');
    set_param(mdl, 'Solver', 'ode23tb');
    set_param(mdl, 'RelTol', '1e-4');

    % Ensure dummy workspace signals exist for FromWorkspace blocks
    dummy_ts = timeseries([0 0 0; 0 0 0], [0; 1]);
    try evalin('base', 'harm_inj_signal;'); catch, assignin('base', 'harm_inj_signal', dummy_ts); end
    try evalin('base', 'flicker_inj_signal;'); catch, assignin('base', 'flicker_inj_signal', dummy_ts); end
    dummy_single = timeseries([0; 0], [0; 1]);
    try evalin('base', 'notch_ctrl_signal;'); catch, assignin('base', 'notch_ctrl_signal', dummy_single); end

    % Set base loads / generator operating point if specified
    cond_id = 1;
    if isfield(scen, 'operating_condition_id')
        cond_id = scen.operating_condition_id;
    end
    fprintf('[SimRunner] Operating condition ID: %d\n', cond_id);

    % Configure Disturbance Injectors
    fault_blk = [mdl '/PQD_Fault_Sag'];
    brk_blk   = [mdl '/PQD_Breaker_Swell'];
    cap_blk   = [mdl '/PQD_Cap_Swell'];

    % Determine timing
    % Nominal simulation stop time: 0.38 s
    t_fault_start = 0.12;
    duration_s = 0.10;
    if isfield(scen.parameters, 'duration_ms')
        duration_s = scen.parameters.duration_ms / 1000.0;
    end
    t_fault_end = t_fault_start + duration_s;
    ph_str = scen.injection_location.phase;

    if strcmp(scen.class, 'Sag')
        % Disable Swell
        if ~isempty(find_system(mdl, 'SearchDepth', 1, 'Name', 'PQD_Breaker_Swell'))
            set_param(brk_blk, 'InitialState', 'open', 'SwitchTimes', '[999 1000]', ...
                'SwitchA', 'off', 'SwitchB', 'off', 'SwitchC', 'off');
        end

        % Configure Sag Fault
        fault_a = 'off'; fault_b = 'off'; fault_c = 'off';
        if contains(ph_str, 'A'), fault_a = 'on'; end
        if contains(ph_str, 'B'), fault_b = 'on'; end
        if contains(ph_str, 'C'), fault_c = 'on'; end

        set_param(fault_blk, 'FaultA', fault_a);
        set_param(fault_blk, 'FaultB', fault_b);
        set_param(fault_blk, 'FaultC', fault_c);
        set_param(fault_blk, 'GroundFault', 'on');
        set_param(fault_blk, 'SwitchTimes', sprintf('[%.6f %.6f]', t_fault_start, t_fault_end));
        set_param(fault_blk, 'FaultResistance', num2str(scen.parameters.fault_resistance_ohms));
        set_param(fault_blk, 'GroundResistance', num2str(scen.parameters.ground_resistance_ohms));

        fprintf('[SimRunner] Sag Fault Config: Phase=%s, Rf=%.1f ohm, t=[%.4f, %.4f] s\n', ...
            ph_str, scen.parameters.fault_resistance_ohms, t_fault_start, t_fault_end);

    elseif strcmp(scen.class, 'Swell')
        % Disable Sag Fault
        if ~isempty(find_system(mdl, 'SearchDepth', 1, 'Name', 'PQD_Fault_Sag'))
            set_param(fault_blk, 'FaultA', 'off', 'FaultB', 'off', 'FaultC', 'off', ...
                'GroundFault', 'off', 'SwitchTimes', '[999 1000]');
        end

        % Configure Swell Breaker and Capacitor
        brk_a = 'off'; brk_b = 'off'; brk_c = 'off';
        if contains(ph_str, 'A'), brk_a = 'on'; end
        if contains(ph_str, 'B'), brk_b = 'on'; end
        if contains(ph_str, 'C'), brk_c = 'on'; end

        set_param(brk_blk, 'InitialState', 'open');
        set_param(brk_blk, 'SwitchTimes', sprintf('[%.6f %.6f]', t_fault_start, t_fault_end));
        set_param(brk_blk, 'SwitchA', brk_a);
        set_param(brk_blk, 'SwitchB', brk_b);
        set_param(brk_blk, 'SwitchC', brk_c);
        set_param(brk_blk, 'BreakerResistance', '0.001');
        set_param(brk_blk, 'SnubberResistance', '1e6');
        set_param(brk_blk, 'SnubberCapacitance', '0');

        qc_mvar = 150.0;
        if isfield(scen.parameters, 'capacitive_power_mvar')
            qc_mvar = scen.parameters.capacitive_power_mvar;
        end
        p_damping = 100e3;
        if isfield(scen.parameters, 'damping_power_kw')
            p_damping = scen.parameters.damping_power_kw * 1e3;
        end

        set_param(cap_blk, 'NominalVoltage', '230e3');
        set_param(cap_blk, 'NominalFrequency', '60');
        set_param(cap_blk, 'ActivePower', num2str(p_damping));
        set_param(cap_blk, 'InductivePower', '0');
        set_param(cap_blk, 'CapacitivePower', num2str(qc_mvar * 1e6));

        fprintf('[SimRunner] Swell Cap Config: Phase=%s, Qc=%.1f MVAR, t=[%.4f, %.4f] s\n', ...
            ph_str, qc_mvar, t_fault_start, t_fault_end);

    elseif strcmp(scen.class, 'Interruption')
        % Disable Sag Fault
        if ~isempty(find_system(mdl, 'SearchDepth', 1, 'Name', 'PQD_Fault_Sag'))
            set_param(fault_blk, 'FaultA', 'off', 'FaultB', 'off', 'FaultC', 'off', ...
                'GroundFault', 'off', 'SwitchTimes', '[999 1000]');
        end

        % Disable Swell
        if ~isempty(find_system(mdl, 'SearchDepth', 1, 'Name', 'PQD_Breaker_Swell'))
            set_param(brk_blk, 'InitialState', 'open', 'SwitchTimes', '[999 1000]', ...
                'SwitchA', 'off', 'SwitchB', 'off', 'SwitchC', 'off');
        end

        % Configure Interruption Breaker
        int_blk = [mdl '/PQD_Breaker_Interruption'];
        brk_a = 'off'; brk_b = 'off'; brk_c = 'off';
        if contains(ph_str, 'A'), brk_a = 'on'; end
        if contains(ph_str, 'B'), brk_b = 'on'; end
        if contains(ph_str, 'C'), brk_c = 'on'; end

        set_param(int_blk, 'InitialState', 'closed');
        set_param(int_blk, 'SwitchTimes', sprintf('[%.6f %.6f]', t_fault_start, t_fault_end));
        set_param(int_blk, 'SwitchA', brk_a);
        set_param(int_blk, 'SwitchB', brk_b);
        set_param(int_blk, 'SwitchC', brk_c);
        set_param(int_blk, 'BreakerResistance', '0.001');
        set_param(int_blk, 'SnubberResistance', '1e6');
        set_param(int_blk, 'SnubberCapacitance', 'inf');

        fprintf('[SimRunner] Interruption Breaker Config: Phase=%s, t=[%.4f, %.4f] s (duration=%.1f ms)\n', ...
            ph_str, t_fault_start, t_fault_end, scen.parameters.duration_ms);

    elseif strcmp(scen.class, 'Harmonics')
        % Disable Sag Fault
        if ~isempty(find_system(mdl, 'SearchDepth', 1, 'Name', 'PQD_Fault_Sag'))
            set_param(fault_blk, 'FaultA', 'off', 'FaultB', 'off', 'FaultC', 'off', ...
                'GroundFault', 'off', 'SwitchTimes', '[999 1000]');
        end

        % Disable Swell
        if ~isempty(find_system(mdl, 'SearchDepth', 1, 'Name', 'PQD_Breaker_Swell'))
            set_param(brk_blk, 'InitialState', 'open', 'SwitchTimes', '[999 1000]', ...
                'SwitchA', 'off', 'SwitchB', 'off', 'SwitchC', 'off');
        end

        % Ensure Interruption Breaker is closed
        int_blk = [mdl '/PQD_Breaker_Interruption'];
        if ~isempty(find_system(mdl, 'SearchDepth', 1, 'Name', 'PQD_Breaker_Interruption'))
            set_param(int_blk, 'InitialState', 'closed', 'SwitchTimes', '[999 1000]', ...
                'SwitchA', 'off', 'SwitchB', 'off', 'SwitchC', 'off');
        end

        % Enable Harmonics injection
        set_param([mdl '/PQD_Harm_Enable'], 'Value', '1');

        % Synthesize harmonic current signal
        t_vec = (0:1e-4:0.38)';
        w0 = 2 * pi * 60;
        t_fault_start = 0.07;
        t_fault_end   = 0.31;
        env = double(t_vec >= t_fault_start & t_vec <= t_fault_end);

        % Parse harmonic currents
        I_orders = scen.parameters.harmonic_orders;
        ia_tot = zeros(size(t_vec));
        ib_tot = zeros(size(t_vec));
        ic_tot = zeros(size(t_vec));

        for k = 1:length(I_orders)
            h = I_orders(k);
            h_key = sprintf('h%d', h);
            % Determine current amplitude
            I_mag = 0;
            if isfield(scen.parameters, 'harmonic_currents_amps') && isfield(scen.parameters.harmonic_currents_amps, h_key)
                I_mag = scen.parameters.harmonic_currents_amps.(h_key);
            elseif isfield(scen.parameters, 'harmonic_magnitudes_pu') && isfield(scen.parameters.harmonic_magnitudes_pu, h_key)
                % Calibration: approx current in Amps for Bus 5 impedance
                v_pu = scen.parameters.harmonic_magnitudes_pu.(h_key);
                scale = 750.0;
                if h == 3, scale = 780.0; end
                if h == 5, scale = 1080.0; end
                if h == 7, scale = 600.0; end
                I_mag = v_pu * scale;
            else
                % Default fallback for common orders
                if h == 3, I_mag = 45.0; end
                if h == 5, I_mag = 28.0; end
                if h == 7, I_mag = 16.0; end
            end

            phi = 0;
            if isfield(scen.parameters, 'harmonic_phases_rad') && isfield(scen.parameters.harmonic_phases_rad, h_key)
                phi = scen.parameters.harmonic_phases_rad.(h_key);
            end

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

        harm_inj_signal = timeseries([ia, ib, ic], t_vec);
        assignin('base', 'harm_inj_signal', harm_inj_signal);

        fprintf('[SimRunner] Harmonics Config: Orders=[%s], Phase=%s, t=[%.4f, %.4f] s\n', ...
            num2str(I_orders), ph_str, t_fault_start, t_fault_end);

    elseif strcmp(scen.class, 'Flicker')
        % Disable Sag Fault
        if ~isempty(find_system(mdl, 'SearchDepth', 1, 'Name', 'PQD_Fault_Sag'))
            set_param(fault_blk, 'FaultA', 'off', 'FaultB', 'off', 'FaultC', 'off', ...
                'GroundFault', 'off', 'SwitchTimes', '[999 1000]');
        end

        % Disable Swell
        if ~isempty(find_system(mdl, 'SearchDepth', 1, 'Name', 'PQD_Breaker_Swell'))
            set_param(brk_blk, 'InitialState', 'open', 'SwitchTimes', '[999 1000]', ...
                'SwitchA', 'off', 'SwitchB', 'off', 'SwitchC', 'off');
        end

        % Ensure Interruption Breaker is closed
        int_blk = [mdl '/PQD_Breaker_Interruption'];
        if ~isempty(find_system(mdl, 'SearchDepth', 1, 'Name', 'PQD_Breaker_Interruption'))
            set_param(int_blk, 'InitialState', 'closed', 'SwitchTimes', '[999 1000]', ...
                'SwitchA', 'off', 'SwitchB', 'off', 'SwitchC', 'off');
        end

        % Ensure Harmonics is disabled
        if ~isempty(find_system(mdl, 'SearchDepth', 1, 'Name', 'PQD_Harm_Enable'))
            set_param([mdl '/PQD_Harm_Enable'], 'Value', '0');
        end

        % Enable Flicker injection
        set_param([mdl '/PQD_Flicker_Enable'], 'Value', '1');

        % Synthesize flicker current signal
        t_vec = (0:1e-4:0.38)';
        w0 = 2 * pi * 60;
        fm = scen.parameters.modulation_freq_hz;
        m_depth = scen.parameters.modulation_depth;

        I_m = m_depth * 5560.0; % Calibration for Bus 5 impedance
        if isfield(scen.parameters, 'flicker_current_amps')
            I_m = scen.parameters.flicker_current_amps;
        end

        phi_m = 0;
        if isfield(scen.parameters, 'modulation_phase_rad')
            phi_m = scen.parameters.modulation_phase_rad;
        end

        ia = I_m * sin(2 * pi * fm * t_vec + phi_m) .* sin(w0 * t_vec);
        ib = I_m * sin(2 * pi * fm * t_vec + phi_m) .* sin(w0 * t_vec - 2*pi/3);
        ic = I_m * sin(2 * pi * fm * t_vec + phi_m) .* sin(w0 * t_vec + 2*pi/3);

        if ~contains(ph_str, 'A'), ia = zeros(size(t_vec)); end
        if ~contains(ph_str, 'B'), ib = zeros(size(t_vec)); end
        if ~contains(ph_str, 'C'), ic = zeros(size(t_vec)); end

        flicker_inj_signal = timeseries([ia, ib, ic], t_vec);
        assignin('base', 'flicker_inj_signal', flicker_inj_signal);

        fprintf('[SimRunner] Flicker Config: fm=%.2f Hz, m=%.4f (Im=%.1f A), Phase=%s\n', ...
            fm, m_depth, I_m, ph_str);

    elseif strcmp(scen.class, 'Notch')
        % Disable Sag Fault
        if ~isempty(find_system(mdl, 'SearchDepth', 1, 'Name', 'PQD_Fault_Sag'))
            set_param(fault_blk, 'FaultA', 'off', 'FaultB', 'off', 'FaultC', 'off', ...
                'GroundFault', 'off', 'SwitchTimes', '[999 1000]');
        end

        % Disable Swell
        if ~isempty(find_system(mdl, 'SearchDepth', 1, 'Name', 'PQD_Breaker_Swell'))
            set_param(brk_blk, 'InitialState', 'open', 'SwitchTimes', '[999 1000]', ...
                'SwitchA', 'off', 'SwitchB', 'off', 'SwitchC', 'off');
        end

        % Ensure Interruption Breaker is closed
        int_blk = [mdl '/PQD_Breaker_Interruption'];
        if ~isempty(find_system(mdl, 'SearchDepth', 1, 'Name', 'PQD_Breaker_Interruption'))
            set_param(int_blk, 'InitialState', 'closed', 'SwitchTimes', '[999 1000]', ...
                'SwitchA', 'off', 'SwitchB', 'off', 'SwitchC', 'off');
        end

        % Ensure Harmonics is disabled
        if ~isempty(find_system(mdl, 'SearchDepth', 1, 'Name', 'PQD_Harm_Enable'))
            set_param([mdl '/PQD_Harm_Enable'], 'Value', '0');
        end

        % Ensure Flicker is disabled
        if ~isempty(find_system(mdl, 'SearchDepth', 1, 'Name', 'PQD_Flicker_Enable'))
            set_param([mdl '/PQD_Flicker_Enable'], 'Value', '0');
        end

        % Configure Notch Commutation Switching Block
        notch_blk = [mdl '/PQD_Notch_Bus5'];
        fa = 'off'; fb = 'off'; fc = 'off';
        if contains(ph_str, 'A'), fa = 'on'; end
        if contains(ph_str, 'B'), fb = 'on'; end
        if contains(ph_str, 'C'), fc = 'on'; end

        % Ground fault setting
        gf = 'off';
        if isfield(scen.parameters, 'ground_fault') && scen.parameters.ground_fault
            gf = 'on';
        end

        % Commutation resistance
        R_comm = 150.0;
        if isfield(scen.parameters, 'commutation_resistance_ohms')
            R_comm = scen.parameters.commutation_resistance_ohms;
        elseif isfield(scen.parameters, 'notch_depth_pu')
            % Map desired depth [0.20, 0.80] to Rf
            d_target = scen.parameters.notch_depth_pu;
            R_comm = max(15.0, 100.0 * (1.0 - d_target) / max(0.1, d_target));
        end

        % Notch width
        width_s = 0.0006; % 600 us default
        if isfield(scen.parameters, 'notch_width_us')
            width_s = scen.parameters.notch_width_us * 1e-6;
        elseif isfield(scen.parameters, 'notch_width_ms')
            width_s = scen.parameters.notch_width_ms * 1e-3;
        end

        % Repetition: 1 notch/cycle or 6 notches/cycle
        rep_per_cycle = 1;
        if isfield(scen.parameters, 'notch_repetition_per_cycle')
            rep_per_cycle = scen.parameters.notch_repetition_per_cycle;
        end

        % Phase offset within fundamental cycle (60 Hz)
        t_offset = 0.005; % 5 ms default
        if isfield(scen.parameters, 'phase_offset_ms')
            t_offset = scen.parameters.phase_offset_ms * 1e-3;
        end

        % Build switching transitions from t = 0.05 to 0.35 s
        f0 = 60.0;
        T0 = 1.0 / f0;
        dt_rep = T0 / rep_per_cycle;

        t_vec = (0:1e-5:0.38)';
        u_notch = zeros(size(t_vec));
        t_cur = 0.05 + t_offset;
        n_pulses = 0;
        while t_cur + width_s <= 0.35
            u_notch((t_vec >= t_cur) & (t_vec < (t_cur + width_s))) = 1.0;
            n_pulses = n_pulses + 1;
            t_cur = t_cur + dt_rep;
        end

        assignin('base', 'notch_ctrl_signal', timeseries(u_notch, t_vec));

        set_param(notch_blk, 'FaultA', fa);
        set_param(notch_blk, 'FaultB', fb);
        set_param(notch_blk, 'FaultC', fc);
        set_param(notch_blk, 'GroundFault', gf);
        set_param(notch_blk, 'FaultResistance', num2str(R_comm));
        set_param([mdl '/PQD_Notch_Enable'], 'Value', '1');
        set_param(mdl, 'MaxStep', '1e-4');

        fprintf('[SimRunner] Notch Config: Phase=%s, Width=%.1f us, Rf=%.1f ohm, Rep=%d/cyc, Pulses=%d\n', ...
            ph_str, width_s * 1e6, R_comm, rep_per_cycle, n_pulses);

    elseif strcmp(scen.class, 'Transient')
        % Disable Sag Fault
        if ~isempty(find_system(mdl, 'SearchDepth', 1, 'Name', 'PQD_Fault_Sag'))
            set_param(fault_blk, 'FaultA', 'off', 'FaultB', 'off', 'FaultC', 'off', ...
                'GroundFault', 'off', 'SwitchTimes', '[999 1000]');
        end

        % Disable Swell
        if ~isempty(find_system(mdl, 'SearchDepth', 1, 'Name', 'PQD_Breaker_Swell'))
            set_param(brk_blk, 'InitialState', 'open', 'SwitchTimes', '[999 1000]', ...
                'SwitchA', 'off', 'SwitchB', 'off', 'SwitchC', 'off');
        end

        % Ensure Interruption Breaker is closed
        int_blk = [mdl '/PQD_Breaker_Interruption'];
        if ~isempty(find_system(mdl, 'SearchDepth', 1, 'Name', 'PQD_Breaker_Interruption'))
            set_param(int_blk, 'InitialState', 'closed', 'SwitchTimes', '[999 1000]', ...
                'SwitchA', 'off', 'SwitchB', 'off', 'SwitchC', 'off');
        end

        % Ensure Harmonics is disabled
        if ~isempty(find_system(mdl, 'SearchDepth', 1, 'Name', 'PQD_Harm_Enable'))
            set_param([mdl '/PQD_Harm_Enable'], 'Value', '0');
        end

        % Ensure Flicker is disabled
        if ~isempty(find_system(mdl, 'SearchDepth', 1, 'Name', 'PQD_Flicker_Enable'))
            set_param([mdl '/PQD_Flicker_Enable'], 'Value', '0');
        end

        % Ensure Notch is disabled
        if ~isempty(find_system(mdl, 'SearchDepth', 1, 'Name', 'PQD_Notch_Enable'))
            set_param([mdl '/PQD_Notch_Enable'], 'Value', '0');
        end

        % Configure Transient Breaker and RLC Branch
        t_brk_blk = [mdl '/PQD_Breaker_Transient'];
        t_rlc_blk = [mdl '/PQD_RLC_Transient'];

        t_sw_start = 0.1042;
        if isfield(scen.parameters, 'switching_instant_s')
            t_sw_start = scen.parameters.switching_instant_s;
        elseif isfield(scen.parameters, 'onset_ms')
            t_sw_start = scen.parameters.onset_ms / 1000.0;
        end

        dur_s = 0.030;
        if isfield(scen.parameters, 'transient_duration_ms')
            dur_s = max(0.015, scen.parameters.transient_duration_ms / 1000.0);
        elseif isfield(scen.parameters, 'duration_ms')
            dur_s = max(0.015, scen.parameters.duration_ms / 1000.0);
        end
        t_sw_end = t_sw_start + dur_s;

        R_val = 1.0;
        if isfield(scen.parameters, 'damping_resistance_ohms')
            R_val = scen.parameters.damping_resistance_ohms;
        elseif isfield(scen.parameters, 'resistance_ohms')
            R_val = scen.parameters.resistance_ohms;
        end

        L_val = 2.0e-3;
        if isfield(scen.parameters, 'inductance_henries')
            L_val = scen.parameters.inductance_henries;
        elseif isfield(scen.parameters, 'inductance_mh')
            L_val = scen.parameters.inductance_mh * 1e-3;
        end

        C_val = 5.0e-6;
        if isfield(scen.parameters, 'capacitance_farads')
            C_val = scen.parameters.capacitance_farads;
        elseif isfield(scen.parameters, 'capacitance_uf')
            C_val = scen.parameters.capacitance_uf * 1e-6;
        end

        brk_a = 'off'; brk_b = 'off'; brk_c = 'off';
        if contains(ph_str, 'A'), brk_a = 'on'; end
        if contains(ph_str, 'B'), brk_b = 'on'; end
        if contains(ph_str, 'C'), brk_c = 'on'; end

        set_param(t_rlc_blk, 'Resistance', num2str(R_val), ...
                             'Inductance', num2str(L_val), ...
                             'Capacitance', num2str(C_val));

        set_param(t_brk_blk, 'InitialState', 'open');
        set_param(t_brk_blk, 'SwitchTimes', sprintf('[%.6f %.6f]', t_sw_start, t_sw_end));
        set_param(t_brk_blk, 'SwitchA', brk_a);
        set_param(t_brk_blk, 'SwitchB', brk_b);
        set_param(t_brk_blk, 'SwitchC', brk_c);
        set_param(t_brk_blk, 'BreakerResistance', '0.001');
        set_param(t_brk_blk, 'SnubberResistance', '1e5');
        set_param(t_brk_blk, 'SnubberCapacitance', '1e-9');

        fprintf('[SimRunner] Transient Config: Phase=%s, L=%.2f mH, C=%.2f uF, R=%.2f ohm, t=[%.4f, %.4f] s\n', ...
            ph_str, L_val*1e3, C_val*1e6, R_val, t_sw_start, t_sw_end);

    else
        error('Unsupported disturbance class: %s', scen.class);
    end

    % Ensure dormant state for interruption breaker if not Interruption class
    if ~strcmp(scen.class, 'Interruption')
        int_blk = [mdl '/PQD_Breaker_Interruption'];
        if ~isempty(find_system(mdl, 'SearchDepth', 1, 'Name', 'PQD_Breaker_Interruption'))
            set_param(int_blk, 'InitialState', 'closed', 'SwitchTimes', '[999 1000]', ...
                'SwitchA', 'off', 'SwitchB', 'off', 'SwitchC', 'off');
        end
    end

    % Ensure dormant state for harmonics injection if not Harmonics class
    if ~strcmp(scen.class, 'Harmonics')
        if ~isempty(find_system(mdl, 'SearchDepth', 1, 'Name', 'PQD_Harm_Enable'))
            set_param([mdl '/PQD_Harm_Enable'], 'Value', '0');
        end
    end

    % Ensure dormant state for flicker injection if not Flicker class
    if ~strcmp(scen.class, 'Flicker')
        if ~isempty(find_system(mdl, 'SearchDepth', 1, 'Name', 'PQD_Flicker_Enable'))
            set_param([mdl '/PQD_Flicker_Enable'], 'Value', '0');
        end
    end

    % Ensure dormant state for notch injection if not Notch class
    if ~strcmp(scen.class, 'Notch')
        notch_blk = [mdl '/PQD_Notch_Bus5'];
        if ~isempty(find_system(mdl, 'SearchDepth', 1, 'Name', 'PQD_Notch_Bus5'))
            set_param(notch_blk, 'FaultA', 'off', 'FaultB', 'off', 'FaultC', 'off', ...
                'GroundFault', 'off');
        end
        if ~isempty(find_system(mdl, 'SearchDepth', 1, 'Name', 'PQD_Notch_Enable'))
            set_param([mdl '/PQD_Notch_Enable'], 'Value', '0');
        end
        set_param(mdl, 'MaxStep', 'auto');
    end

    % Ensure dormant state for transient breaker if not Transient class
    if ~strcmp(scen.class, 'Transient')
        t_brk_blk = [mdl '/PQD_Breaker_Transient'];
        if ~isempty(find_system(mdl, 'SearchDepth', 1, 'Name', 'PQD_Breaker_Transient'))
            set_param(t_brk_blk, 'InitialState', 'open', 'SwitchTimes', '[999 1000]', ...
                'SwitchA', 'off', 'SwitchB', 'off', 'SwitchC', 'off');
        end
    end

    t_start = tic;
    simOut = sim(mdl, 'StopTime', '0.38');
    t_wall = toc(t_start);
    fprintf('[SimRunner] Simulation completed in %.2f s\n', t_wall);

    % Resample to 5000 Hz
    Vts = simOut.PQD_Vabc;
    [Vres, tres] = resample(Vts.Data, Vts.Time, 5000);

    Ires = [];
    if isprop(simOut, 'PQD_Iabc') || isfield(simOut, 'PQD_Iabc')
        Its = simOut.PQD_Iabc;
        [Ires, ~] = resample(Its.Data, Its.Time, 5000);
    else
        Ires = zeros(size(Vres));
    end

    % Slice 200 ms (1000 samples) window
    if strcmp(scen.class, 'Harmonics') || strcmp(scen.class, 'Flicker') || strcmp(scen.class, 'Notch')
        t_frame_start = 0.09;
        t_frame_end   = 0.29;
    elseif strcmp(scen.class, 'Transient')
        t_frame_start = max(0.0, t_sw_start - 0.050);
        t_frame_end   = t_frame_start + 0.200;
    else
        onset_s = 0.030;
        if isfield(scen.parameters, 'onset_time_ms')
            onset_s = scen.parameters.onset_time_ms / 1000.0;
        elseif isfield(scen.parameters, 'onset_ms')
            onset_s = scen.parameters.onset_ms / 1000.0;
        end
        t_frame_start = t_fault_start - onset_s;
        t_frame_end = t_frame_start + 0.200;
    end

    frame_mask = (tres >= (t_frame_start - 1e-6) & tres < (t_frame_end - 1e-6));
    V_frame = Vres(frame_mask, :);
    I_frame = Ires(frame_mask, :);
    t_frame = tres(frame_mask) - t_frame_start; % 0 to 0.200 s

    % Trim to exactly 1000 samples if rounding produced 1001
    if size(V_frame, 1) > 1000
        V_frame = V_frame(1:1000, :);
        I_frame = I_frame(1:1000, :);
        t_frame = t_frame(1:1000);
    elseif size(V_frame, 1) < 1000
        error('Frame sample count %d < 1000', size(V_frame, 1));
    end

    fprintf('[SimRunner] Extracted frame: %d samples, t=[0, %.3f] s\n', ...
        size(V_frame, 1), t_frame(end));

    % Save results
    save(output_mat_path, 'V_frame', 'I_frame', 't_frame', 'scen', 't_wall', ...
         't_fault_start', 't_fault_end', 't_frame_start', 't_frame_end', '-v7');
    fprintf('[SimRunner] Successfully saved to %s\n', output_mat_path);

    close_system(mdl, 0);
end
