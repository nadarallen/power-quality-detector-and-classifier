function run_live_dashboard_sim(config_json_path)
% run_live_dashboard_sim  —  Live dashboard execution driver
%
% Genuine incremental streaming and live disturbance injection during
% active MATLAB/Simulink execution of IEEE_9bus_PQD_DISTURBANCES.slx.
%
% Reads validated JSON config from simulation_bridge.py, loads the model in memory,
% dynamically attaches the pqd_live_streamer S-function to Bus 5 measurements
% and disturbance subsystems, executes sim(), streams 5 kHz samples progressively
% to Python /api/ingest/simulink, and accepts mid-run injection commands.
%
% Protected reference model is untouched. Model is NEVER saved on disk.
%
% Usage:
%   matlab -batch "addpath('integration/matlab'); addpath('IEEE_9bus'); \
%                  run_live_dashboard_sim('path/to/config.json');"

    fprintf('[LiveSim] Starting — reading config: %s\n', config_json_path);

    %% 1. Read and validate config
    if ~exist(config_json_path, 'file')
        error('[LiveSim] Config JSON not found: %s', config_json_path);
    end
    raw = fileread(config_json_path);
    cfg = jsondecode(raw);

    run_id     = cfg.run_id;
    cls        = cfg.class;
    ph_str     = cfg.phase;           % e.g. 'ABC', 'A', 'BC'
    stop_time  = cfg.stop_time;       % default 0.38
    onset      = cfg.onset_time;      % default 0.12
    server_url = cfg.server_url;      % e.g. 'http://127.0.0.1:8500'
    model_dir  = cfg.model_dir;

    mode = 'manual';
    if isfield(cfg, 'mode')
        mode = cfg.mode;
    end

    cmd_file = '';
    if isfield(cfg, 'cmd_file')
        cmd_file = cfg.cmd_file;
    end

    if isfield(cfg, 'class_params')
        cp = cfg.class_params;
    else
        cp = struct();
    end

    fprintf('[LiveSim] run_id=%s  mode=%s  class=%s  phase=%s  stop=%.3fs\n', ...
            run_id, mode, cls, ph_str, stop_time);

    %% 2. Add paths and load model (no save)
    addpath(model_dir);
    cur_dir = fileparts(mfilename('fullpath'));
    addpath(cur_dir);

    mdl = 'IEEE_9bus_PQD_DISTURBANCES';

    if bdIsLoaded(mdl)
        close_system(mdl, 0);
    end

    fprintf('[LiveSim] Loading model %s ...\n', mdl);
    load_system(mdl);
    cleanupObj = onCleanup(@() cleanup_sim(mdl));

    set_param(mdl, 'StopFcn', '');
    set_param(mdl, 'Solver',  'ode23tb');
    set_param(mdl, 'RelTol',  '1e-4');
    set_param(mdl, 'MaxStep', '2.5e-5');
    fprintf('[LiveSim] Model loaded with solver ode23tb, MaxStep=2.5e-5.\n');

    %% 3. Block handles
    fault_blk = [mdl '/PQD_Fault_Sag'];
    swl_brk   = [mdl '/PQD_Breaker_Swell'];
    swl_cap   = [mdl '/PQD_Cap_Swell'];
    int_brk   = [mdl '/PQD_Breaker_Interruption'];
    trn_brk   = [mdl '/PQD_Breaker_Transient'];
    trn_rlc   = [mdl '/PQD_RLC_Transient'];
    notch_blk = [mdl '/PQD_Notch_Bus5'];

    %% 4. Ensure required workspace signals exist
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

    %% 6. Configure disturbance parameters
    fa = phase_flag(ph_str, 'A');
    fb = phase_flag(ph_str, 'B');
    fc = phase_flag(ph_str, 'C');

    duration_s = param_or_default(cp, 'duration_ms', 100.0) / 1000.0;
    fault_r    = param_or_default(cp, 'fault_resistance_ohms',  5.0);
    ground_r   = param_or_default(cp, 'ground_resistance_ohms', 0.1);
    qc_mvar    = param_or_default(cp, 'capacitive_power_mvar', 150.0);
    p_damp_kw  = param_or_default(cp, 'damping_power_kw',      100.0);

    % Configure Sag Fault block parameters
    set_param(fault_blk, 'FaultA', fa, 'FaultB', fb, 'FaultC', fc);
    set_param(fault_blk, 'GroundFault', 'on');
    set_param(fault_blk, 'FaultResistance',  num2str(fault_r));
    set_param(fault_blk, 'GroundResistance', num2str(ground_r));

    % Configure Swell Breaker and Capacitor parameters
    set_param(swl_brk, 'InitialState', 'open');
    set_param(swl_brk, 'SwitchA', fa, 'SwitchB', fb, 'SwitchC', fc);
    set_param(swl_brk, 'BreakerResistance', '0.001');
    set_param(swl_brk, 'SnubberResistance', '1e6');
    set_param(swl_brk, 'SnubberCapacitance', '0'); % 0 avoids numerical stiffness

    set_param(swl_cap, 'NominalVoltage',    '230e3');
    set_param(swl_cap, 'NominalFrequency',  '60');
    set_param(swl_cap, 'ActivePower',       num2str(p_damp_kw * 1e3));
    set_param(swl_cap, 'InductivePower',    '0');
    set_param(swl_cap, 'CapacitivePower',   num2str(qc_mvar * 1e6));

    % Configure Interruption Breaker parameters
    set_param(int_brk, 'InitialState', 'closed');
    set_param(int_brk, 'SwitchA', fa, 'SwitchB', fb, 'SwitchC', fc);
    set_param(int_brk, 'BreakerResistance', '0.001');
    set_param(int_brk, 'SnubberResistance', '1e6');
    set_param(int_brk, 'SnubberCapacitance', '0');

    %% 7. Setup Live AppData for pqd_live_streamer S-Function
    setappdata(0, 'PQD_Live_RunId',         run_id);
    setappdata(0, 'PQD_Live_ServerUrl',     server_url);
    setappdata(0, 'PQD_Live_CmdFile',       cmd_file);
    setappdata(0, 'PQD_Live_Mode',          mode);
    setappdata(0, 'PQD_Live_SchedClass',    cls);
    setappdata(0, 'PQD_Live_SchedOnset',    onset);
    setappdata(0, 'PQD_Live_SchedDuration', duration_s);

    %% 8. Dynamically attach pqd_live_streamer block in memory
    fprintf('[LiveSim] Attaching live streamer and control interfaces...\n');
    streamer_blk = [mdl '/PQD_Live_Streamer'];
    from_v_blk   = [mdl '/PQD_From_V5'];
    from_i_blk   = [mdl '/PQD_From_I5'];

    % Add S-Function streamer
    add_block('simulink/User-Defined Functions/Level-2 MATLAB S-Function', ...
              streamer_blk, 'FunctionName', 'pqd_live_streamer');

    % Add measurement inputs from Bus 5
    add_block('simulink/Signal Routing/From', from_v_blk, 'GotoTag', 'Vabc_5');
    add_block('simulink/Signal Routing/From', from_i_blk, 'GotoTag', 'Iabc_5');
    add_line(mdl, 'PQD_From_V5/1', 'PQD_Live_Streamer/1');
    add_line(mdl, 'PQD_From_I5/1', 'PQD_Live_Streamer/2');

    % Set disturbance blocks to External control and connect S-Function triggers
    set_param(fault_blk, 'External', 'on');
    add_line(mdl, 'PQD_Live_Streamer/1', 'PQD_Fault_Sag/1');

    set_param(swl_brk, 'External', 'on');
    add_line(mdl, 'PQD_Live_Streamer/2', 'PQD_Breaker_Swell/1');

    set_param(int_brk, 'External', 'on');
    add_line(mdl, 'PQD_Live_Streamer/3', 'PQD_Breaker_Interruption/1');

    fprintf('[LiveSim] Live streaming and injection architecture active.\n');

    %% 9. Run simulation (Real-time incremental streaming occurs during sim)
    fprintf('[LiveSim] Running sim (StopTime=%.3f s) with live streaming...\n', stop_time);
    t_sim = tic;
    simOut = sim(mdl, 'StopTime', num2str(stop_time));
    t_wall = toc(t_sim);
    fprintf('[LiveSim] sim() completed in %.1f s wall-clock.\n', t_wall);

    %% 10. Notify backend of completion
    complete_url = [server_url '/api/live/simulation/complete'];
    try
        done_payload = struct('run_id', run_id, 'status', 'completed', ...
                              'wall_time_s', t_wall);
        opts = weboptions('MediaType','application/json','Timeout',15);
        webwrite(complete_url, jsonencode(done_payload), opts);
        fprintf('[LiveSim] Completion notification sent.\n');
    catch ME
        fprintf('[LiveSim] Warning: completion POST failed: %s\n', ME.message);
    end

    %% 11. Close model WITHOUT saving
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
