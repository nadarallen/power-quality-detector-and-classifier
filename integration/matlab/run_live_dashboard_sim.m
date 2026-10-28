function run_live_dashboard_sim(config_json_path)
% run_live_dashboard_sim  —  Live dashboard single-run driver
%
% Reads a validated JSON config written by simulation_bridge.py,
% configures IEEE_9bus_PQD_DISTURBANCES.slx, runs sim(), resamples
% to 5 kHz, and POSTs results in 1 000-sample chunks to the Python
% backend via /api/ingest/simulink.
%
% Usage (called by Python via subprocess):
%   matlab -batch "addpath('integration/matlab'); addpath('IEEE_9bus'); \
%                  run_live_dashboard_sim('path/to/config.json');"
%
% The function NEVER saves the model.  It calls close_system(mdl, 0).

    fprintf('[LiveSim] Starting — reading config: %s\n', config_json_path);

    %% 1. Read and validate config
    if ~exist(config_json_path, 'file')
        error('[LiveSim] Config JSON not found: %s', config_json_path);
    end
    raw   = fileread(config_json_path);
    cfg   = jsondecode(raw);

    run_id     = cfg.run_id;
    cls        = cfg.class;
    ph_str     = cfg.phase;           % e.g. 'ABC', 'A', 'BC'
    stop_time  = cfg.stop_time;       % default 0.38
    onset      = cfg.onset_time;      % default 0.12
    server_url = cfg.server_url;      % e.g. 'http://127.0.0.1:8500'
    model_dir  = cfg.model_dir;

    if isfield(cfg, 'class_params')
        cp = cfg.class_params;
    else
        cp = struct();
    end

    fprintf('[LiveSim] run_id=%s  class=%s  phase=%s  stop=%.3fs\n', ...
            run_id, cls, ph_str, stop_time);

    %% 2. Add model directory and load model (no save)
    addpath(model_dir);
    mdl = 'IEEE_9bus_PQD_DISTURBANCES';

    fprintf('[LiveSim] Loading model %s ...\n', mdl);
    load_system(mdl);
    cleanupObj = onCleanup(@() cleanup_sim(mdl));
    set_param(mdl, 'StopFcn', '');
    set_param(mdl, 'Solver',  'ode23tb');
    set_param(mdl, 'RelTol',  '1e-4');
    set_param(mdl, 'MaxStep', '2.5e-5');
    fprintf('[LiveSim] Model loaded.\n');

    %% 3. Block handles (exact names confirmed from model inspection)
    fault_blk = [mdl '/PQD_Fault_Sag'];
    swl_brk   = [mdl '/PQD_Breaker_Swell'];
    swl_cap   = [mdl '/PQD_Cap_Swell'];
    int_brk   = [mdl '/PQD_Breaker_Interruption'];
    trn_brk   = [mdl '/PQD_Breaker_Transient'];
    trn_rlc   = [mdl '/PQD_RLC_Transient'];
    notch_blk = [mdl '/PQD_Notch_Bus5'];

    %% 4. Ensure required workspace signals exist (prevent sim errors)
    dummy_ts     = timeseries([0 0 0; 0 0 0], [0; 1]);
    dummy_single = timeseries([0; 0],          [0; 1]);
    assignin('base', 'harm_inj_signal',    dummy_ts);
    assignin('base', 'flicker_inj_signal', dummy_ts);
    assignin('base', 'notch_ctrl_signal',  dummy_single);

    %% 5. Reset ALL disturbance blocks to dormant
    set_param(fault_blk, 'FaultA', 'off', 'FaultB', 'off', 'FaultC', 'off', ...
              'GroundFault', 'off', 'SwitchTimes', '[999 1000]');
    set_param(swl_brk, 'InitialState', 'open', ...
              'SwitchA', 'off', 'SwitchB', 'off', 'SwitchC', 'off', ...
              'SwitchTimes', '[999 1000]');
    set_param(int_brk, 'InitialState', 'closed', ...
              'SwitchA', 'off', 'SwitchB', 'off', 'SwitchC', 'off', ...
              'SwitchTimes', '[999 1000]');
    set_param([mdl '/PQD_Harm_Enable'],   'Value', '0');
    set_param([mdl '/PQD_Flicker_Enable'],'Value', '0');
    set_param(notch_blk, 'FaultA', 'off', 'FaultB', 'off', 'FaultC', 'off', ...
              'GroundFault', 'off');
    set_param([mdl '/PQD_Notch_Enable'],  'Value', '0');
    set_param(trn_brk, 'InitialState', 'open', ...
              'SwitchA', 'off', 'SwitchB', 'off', 'SwitchC', 'off', ...
              'SwitchTimes', '[999 1000]');

    %% 6. Configure disturbance-specific blocks
    fa = phase_flag(ph_str, 'A');
    fb = phase_flag(ph_str, 'B');
    fc = phase_flag(ph_str, 'C');

    % Duration
    duration_s = param_or_default(cp, 'duration_ms', 100.0) / 1000.0;
    t_end      = onset + duration_s;

    switch cls

        case 'Normal'
            % All blocks already dormant — nothing extra to do.
            fprintf('[LiveSim] Normal scenario — all disturbances disabled.\n');

        case 'Sag'
            fault_r  = param_or_default(cp, 'fault_resistance_ohms',  5.0);
            ground_r = param_or_default(cp, 'ground_resistance_ohms', 0.1);

            set_param(fault_blk, 'FaultA', fa, 'FaultB', fb, 'FaultC', fc);
            set_param(fault_blk, 'GroundFault', 'on');
            set_param(fault_blk, 'SwitchTimes', ...
                      sprintf('[%.6f %.6f]', onset, t_end));
            set_param(fault_blk, 'FaultResistance',  num2str(fault_r));
            set_param(fault_blk, 'GroundResistance', num2str(ground_r));
            fprintf('[LibeSim] Sag: R_fault=%.2f ohm, R_gnd=%.4f ohm, dur=%.0f ms, ph=%s\n', ...
                    fault_r, ground_r, duration_s*1000, ph_str);

        case 'Swell'
            qc_mvar   = param_or_default(cp, 'capacitive_power_mvar', 50.0);
            p_damp_kw = param_or_default(cp, 'damping_power_kw',       5.0);

            set_param(swl_brk, 'InitialState', 'open');
            set_param(swl_brk, 'SwitchTimes', ...
                      sprintf('[%.6f %.6f]', onset, t_end));
            set_param(swl_brk, 'SwitchA', fa, 'SwitchB', fb, 'SwitchC', fc);
            set_param(swl_brk, 'BreakerResistance', '0.001');
            set_param(swl_brk, 'SnubberResistance', '1e6');
            set_param(swl_brk, 'SnubberCapacitance', 'inf');

            set_param(swl_cap, 'NominalVoltage',    '230e3');
            set_param(swl_cap, 'NominalFrequency',  '60');
            set_param(swl_cap, 'ActivePower',       num2str(p_damp_kw * 1e3));
            set_param(swl_cap, 'InductivePower',    '0');
            set_param(swl_cap, 'CapacitivePower',   num2str(qc_mvar * 1e6));
            fprintf('[LiveSim] Swell: Qc=%.0f MVAr, P_damp=%.1f kW, dur=%.0f ms, ph=%s\n', ...
                    qc_mvar, p_damp_kw, duration_s*1000, ph_str);

        case 'Interruption'
            set_param(int_brk, 'InitialState', 'closed');
            set_param(int_brk, 'SwitchTimes', ...
                      sprintf('[%.6f %.6f]', onset, t_end));
            set_param(int_brk, 'SwitchA', fa, 'SwitchB', fb, 'SwitchC', fc);
            set_param(int_brk, 'BreakerResistance', '0.001');
            set_param(int_brk, 'SnubberResistance', '1e6');
            set_param(int_brk, 'SnubberCapacitance', 'inf');
            fprintf('[LiveSim] Interruption: dur=%.0f ms, ph=%s\n', ...
                    duration_s*1000, ph_str);

        case 'Harmonics'
            set_param([mdl '/PQD_Harm_Enable'], 'Value', '1');
            t_vec = (0:2.5e-5:stop_time)';
            w0    = 2 * pi * 60;
            t_h_start = onset - 0.05; if t_h_start < 0, t_h_start = 0; end
            t_h_end   = t_end + 0.05; if t_h_end > stop_time, t_h_end = stop_time; end
            env   = double(t_vec >= t_h_start & t_vec <= t_h_end);

            h3 = param_or_default(cp, 'h3_amplitude', 0.15);
            h5 = param_or_default(cp, 'h5_amplitude', 0.10);
            h7 = param_or_default(cp, 'h7_amplitude', 0.05);

            ia = (h3*sin(3*w0*t_vec) + h5*sin(5*w0*t_vec) + h7*sin(7*w0*t_vec)) .* env;
            ib = (h3*sin(3*w0*t_vec-2*pi/3) + h5*sin(5*w0*t_vec-2*pi/3) + h7*sin(7*w0*t_vec-2*pi/3)) .* env;
            ic = (h3*sin(3*w0*t_vec+2*pi/3) + h5*sin(5*w0*t_vec+2*pi/3) + h7*sin(7*w0*t_vec+2*pi/3)) .* env;

            if ~contains(ph_str,'A'), ia = zeros(size(t_vec)); end
            if ~contains(ph_str,'B'), ib = zeros(size(t_vec)); end
            if ~contains(ph_str,'C'), ic = zeros(size(t_vec)); end

            assignin('base', 'harm_inj_signal', timeseries([ia, ib, ic], t_vec));
            fprintf('[LiveSim] Harmonics: h3=%.2f h5=%.2f h7=%.2f ph=%s\n', h3, h5, h7, ph_str);

        case 'Flicker'
            set_param([mdl '/PQD_Flicker_Enable'], 'Value', '1');
            t_vec = (0:2.5e-5:stop_time)';
            w0    = 2 * pi * 60;
            fm    = param_or_default(cp, 'modulation_freq_hz', 8.8);
            Im    = param_or_default(cp, 'modulation_depth',   0.1);

            ia = Im * sin(2*pi*fm*t_vec) .* sin(w0*t_vec);
            ib = Im * sin(2*pi*fm*t_vec) .* sin(w0*t_vec - 2*pi/3);
            ic = Im * sin(2*pi*fm*t_vec) .* sin(w0*t_vec + 2*pi/3);

            if ~contains(ph_str,'A'), ia = zeros(size(t_vec)); end
            if ~contains(ph_str,'B'), ib = zeros(size(t_vec)); end
            if ~contains(ph_str,'C'), ic = zeros(size(t_vec)); end

            assignin('base', 'flicker_inj_signal', timeseries([ia, ib, ic], t_vec));
            fprintf('[LiveSim] Flicker: fm=%.1f Hz, depth=%.2f, ph=%s\n', fm, Im, ph_str);

        case 'Notch'
            R_comm  = param_or_default(cp, 'commutation_resistance_ohms', 0.5);
            width_s = param_or_default(cp, 'notch_width_us', 500.0) * 1e-6;

            f0     = 60.0;
            T0     = 1.0 / f0;
            dt_rep = T0 / 6;          % 6 notches per cycle (typical)

            t_vec    = (0:5e-6:stop_time)';
            u_notch  = zeros(size(t_vec));
            t_cur    = 0.05;
            while t_cur + width_s <= (stop_time - 0.03)
                u_notch((t_vec >= t_cur) & (t_vec < (t_cur + width_s))) = 1.0;
                t_cur = t_cur + dt_rep;
            end
            assignin('base', 'notch_ctrl_signal', timeseries(u_notch, t_vec));
            set_param(notch_blk, 'FaultA', fa, 'FaultB', fb, 'FaultC', fc);
            if isscalar(ph_str)
                set_param(notch_blk, 'GroundFault', 'on');
            else
                set_param(notch_blk, 'GroundFault', 'off');
            end
            set_param(notch_blk, 'FaultResistance', num2str(R_comm));
            set_param([mdl '/PQD_Notch_Enable'], 'Value', '1');
            fprintf('[LiveSim] Notch: R=%.3f, width=%.0f us, ph=%s\n', ...
                    R_comm, width_s*1e6, ph_str);

        case 'Transient'
            L_val = param_or_default(cp, 'inductance_mh',          5.0) * 1e-3;
            C_val = param_or_default(cp, 'capacitance_uf',        50.0) * 1e-6;
            R_val = param_or_default(cp, 'damping_resistance_ohms', 2.0);

            t_sw_start = onset;
            t_sw_end   = t_end;

            set_param(trn_rlc, 'Resistance', num2str(R_val), ...
                               'Inductance', num2str(L_val), ...
                               'Capacitance', num2str(C_val));
            set_param(trn_brk, 'InitialState', 'open');
            set_param(trn_brk, 'SwitchTimes', ...
                      sprintf('[%.6f %.6f]', t_sw_start, t_sw_end));
            set_param(trn_brk, 'SwitchA', fa, 'SwitchB', fb, 'SwitchC', fc);
            set_param(trn_brk, 'BreakerResistance', '0.001');
            set_param(trn_brk, 'SnubberResistance', '1e5');
            set_param(trn_brk, 'SnubberCapacitance', '1e-9');
            fprintf('[LiveSim] Transient: L=%.1f mH, C=%.1f uF, R=%.2f ohm, ph=%s\n', ...
                    L_val*1e3, C_val*1e6, R_val, ph_str);

        otherwise
            error('[LiveSim] Unknown disturbance class: %s', cls);
    end

    %% 7. Run simulation
    fprintf('[LiveSim] Running sim (StopTime=%.3f s) ...\n', stop_time);
    t_sim = tic;
    simOut = sim(mdl, 'StopTime', num2str(stop_time));
    t_wall = toc(t_sim);
    fprintf('[LiveSim] sim() completed in %.1f s\n', t_wall);

    %% 8. Extract logged signals
    Vts = simOut.PQD_Vabc;
    has_I = isprop(simOut, 'PQD_Iabc') || isfield(simOut, 'PQD_Iabc');
    if has_I
        Its = simOut.PQD_Iabc;
    else
        Its = [];
        fprintf('[LiveSim] Warning: PQD_Iabc not found in simOut — current will be zero.\n');
    end

    %% 9. Resample to 5 kHz grid
    t_grid = (0:(1/5000):stop_time)';
    V_5k   = interp1(Vts.Time, Vts.Data, t_grid, 'linear', 'extrap');
    if ~isempty(Its)
        I_5k = interp1(Its.Time, Its.Data, t_grid, 'linear', 'extrap');
    else
        I_5k = zeros(size(V_5k));
    end

    if any(isnan(V_5k(:)))
        fprintf('[LiveSim] Warning: NaN values in resampled voltage — replacing with 0.\n');
        V_5k(isnan(V_5k)) = 0;
    end

    N = length(t_grid);
    fprintf('[LiveSim] Resampled to 5 kHz: %d samples\n', N);

    %% 10. POST in 1 000-sample chunks to Python backend
    chunk_size = 1000;
    num_chunks = ceil(N / chunk_size);
    ingest_url = [server_url '/api/ingest/simulink'];
    % POSIX timestamp for chunk timing — time() is not a MATLAB function
    t_post_start = posixtime(datetime('now', 'TimeZone', 'UTC'));

    for k = 1:num_chunks
        i_start = (k-1)*chunk_size + 1;
        i_end   = min(k*chunk_size, N);

        V_chunk = V_5k(i_start:i_end, :);   % Nx3
        I_chunk = I_5k(i_start:i_end, :);   % Nx3

        payload = struct();
        payload.source           = 'simulink';
        payload.run_id           = run_id;
        payload.device_id        = 'SIMULINK_IEEE9BUS_BUS5';
        payload.sampling_rate_hz = 5000;
        payload.nominal_frequency_hz = 60;
        payload.chunk_index      = k;
        payload.total_chunks     = num_chunks;
        payload.timestamp_utc    = t_post_start + (i_start-1)/5000;
        payload.sequence_number  = k;
        payload.channels         = struct( ...
            'L1', V_chunk(:,1)', ...
            'L2', V_chunk(:,2)', ...
            'L3', V_chunk(:,3)' );
        payload.current_channels = struct( ...
            'L1', I_chunk(:,1)', ...
            'L2', I_chunk(:,2)', ...
            'L3', I_chunk(:,3)' );

        payload_json = jsonencode(payload);

        try
            options = weboptions('MediaType','application/json','Timeout',30);
            webwrite(ingest_url, payload_json, options);
            fprintf('[LiveSim] Chunk %d/%d posted (%d samples)\n', ...
                    k, num_chunks, i_end - i_start + 1);
        catch ME
            fprintf('[LiveSim] Warning: chunk %d POST failed: %s\n', k, ME.message);
        end

        % Small delay so frontend can update progressively
        if k < num_chunks
            pause(0.05);
        end
    end

    %% 11. Notify backend of completion
    complete_url = [server_url '/api/live/simulation/complete'];
    try
        done_payload  = struct('run_id', run_id, 'status', 'completed', ...
                               'chunks_posted', num_chunks, ...
                               'wall_time_s', t_wall);
        options2 = weboptions('MediaType','application/json','Timeout',15);
        webwrite(complete_url, jsonencode(done_payload), options2);
        fprintf('[LiveSim] Completion notification sent.\n');
    catch ME
        fprintf('[LiveSim] Warning: completion POST failed: %s\n', ME.message);
    end

    %% 12. Close model WITHOUT saving
    set_param(mdl, 'Dirty', 'off');
    close_system(mdl, 0);
    fprintf('[LiveSim] Done — model closed (not saved).\n');
end


% -------------------------------------------------------------------------
% Helper: resolve parameter from struct, falling back to default
% -------------------------------------------------------------------------
function val = param_or_default(cp, key, default_val)
    if isstruct(cp) && isfield(cp, key)
        val = double(cp.(key));
    else
        val = default_val;
    end
end

% -------------------------------------------------------------------------
% Helper: 'on' if phase letter appears in phase string
% -------------------------------------------------------------------------
function flag = phase_flag(ph_str, letter)
    if contains(ph_str, letter)
        flag = 'on';
    else
        flag = 'off';
    end
end

% -------------------------------------------------------------------------
% Helper: ensure model is safely closed without saving changes
% -------------------------------------------------------------------------
function cleanup_sim(mdl)
    try
        if bdIsLoaded(mdl)
            set_param(mdl, 'Dirty', 'off');
            close_system(mdl, 0);
            fprintf('[LiveSim] Cleanup: model %s closed cleanly without save.\n', mdl);
        end
    catch
    end
end

