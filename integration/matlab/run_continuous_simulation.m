function run_continuous_simulation(config_json_path)
% run_continuous_simulation  —  Continuous SIL Simulation Driver for IEEE 9-bus
%
% Implements a persistent, continuous Software-in-the-Loop simulation session:
% - Loads IEEE_9bus_PQD_DISTURBANCES.slx once in memory
% - Configures continuous execution (StopTime = inf)
% - Enables Simulink Pacing (1.0 s/s) for real-time 1:1 execution
% - Attaches Level-2 S-Function streamer (5 kHz, 250-sample chunks)
% - Handles mid-run disturbance injection and runtime reset via command file
% - Safely terminates upon explicit stop command without saving model changes.
%
% Pristine reference HIL model is NEVER touched or loaded here.
% Model changes are kept strictly in-memory and discarded upon cleanup.

    fprintf('[ContinuousSim] Initializing continuous session from: %s\n', config_json_path);

    %% 1. Read and validate config JSON
    if ~exist(config_json_path, 'file')
        error('[ContinuousSim] Config file not found: %s', config_json_path);
    end
    raw = fileread(config_json_path);
    cfg = jsondecode(raw);

    run_id     = cfg.run_id;
    server_url = cfg.server_url;
    model_dir  = cfg.model_dir;
    cmd_file   = '';
    if isfield(cfg, 'cmd_file'), cmd_file = cfg.cmd_file; end

    tcp_port = 8502;
    if isfield(cfg, 'tcp_port'), tcp_port = double(cfg.tcp_port); end

    fprintf('[ContinuousSim] run_id=%s  server=%s  tcp_port=%d\n', run_id, server_url, tcp_port);

    %% 2. Setup paths
    addpath(model_dir);
    cur_dir = fileparts(mfilename('fullpath'));
    addpath(cur_dir);

    mdl = 'IEEE_9bus_PQD_DISTURBANCES';

    if bdIsLoaded(mdl)
        close_system(mdl, 0);
    end

    fprintf('[ContinuousSim] Loading model %s ...\n', mdl);
    load_system(mdl);
    cleanupObj = onCleanup(@() cleanup_sim(mdl));

    %% 3. Configure solver and real-time pacing
    set_param(mdl, 'StopFcn', '');
    set_param(mdl, 'Solver',  'ode23tb');
    set_param(mdl, 'RelTol',  '1e-4');
    set_param(mdl, 'MaxStep', '2.5e-5');
    set_param(mdl, 'EnablePacing', 'on');
    set_param(mdl, 'PacingRate', 1.0);
    set_param(mdl, 'ReturnWorkspaceOutputs', 'off');
    fprintf('[ContinuousSim] Configured: ode23tb, MaxStep=2.5e-5, PacingRate=1.0 s/s.\n');

    %% 4. Ensure required base workspace variables exist
    dummy_ts     = timeseries([0 0 0; 0 0 0], [0; 1]);
    dummy_single = timeseries([0; 0],          [0; 1]);
    assignin('base', 'harm_inj_signal',    dummy_ts);
    assignin('base', 'flicker_inj_signal', dummy_ts);
    assignin('base', 'notch_ctrl_signal',  dummy_single);

    %% 5. Disturbance block handles
    fault_blk = [mdl '/PQD_Fault_Sag'];
    swl_brk   = [mdl '/PQD_Breaker_Swell'];
    swl_cap   = [mdl '/PQD_Cap_Swell'];
    int_brk   = [mdl '/PQD_Breaker_Interruption'];
    trn_brk   = [mdl '/PQD_Breaker_Transient'];
    trn_rlc   = [mdl '/PQD_RLC_Transient'];
    notch_blk = [mdl '/PQD_Notch_Bus5'];

    %% 6. Reset all disturbance blocks to initial dormant baseline
    set_param(fault_blk, 'FaultA', 'off', 'FaultB', 'off', 'FaultC', 'off', ...
              'GroundFault', 'on', 'SwitchTimes', '[999 1000]', ...
              'FaultResistance', '5.0', 'GroundResistance', '0.1');
    set_param(swl_brk, 'InitialState', 'open', ...
              'SwitchA', 'on', 'SwitchB', 'on', 'SwitchC', 'on', ...
              'SwitchTimes', '[999 1000]', ...
              'BreakerResistance', '0.001', 'SnubberResistance', '1e6', 'SnubberCapacitance', '0');
    set_param(swl_cap, 'NominalVoltage', '230e3', 'NominalFrequency', '60', ...
              'ActivePower', '100e3', 'InductivePower', '0', 'CapacitivePower', '150e6');
    set_param(int_brk, 'InitialState', 'closed', ...
              'SwitchA', 'on', 'SwitchB', 'on', 'SwitchC', 'on', ...
              'SwitchTimes', '[999 1000]', ...
              'BreakerResistance', '0.001', 'SnubberResistance', '1e6', 'SnubberCapacitance', '0');
    set_param([mdl '/PQD_Harm_Enable'],   'Value', '0');
    set_param([mdl '/PQD_Flicker_Enable'],'Value', '0');
    set_param(notch_blk, 'FaultA', 'off', 'FaultB', 'off', 'FaultC', 'off', 'GroundFault', 'off');
    set_param([mdl '/PQD_Notch_Enable'],  'Value', '0');
    set_param(trn_brk, 'InitialState', 'open', 'SwitchTimes', '[999 1000]');

    %% 7. Setup Live AppData for pqd_live_streamer
    setappdata(0, 'PQD_Live_RunId',      run_id);
    setappdata(0, 'PQD_Live_ServerUrl',  server_url);
    setappdata(0, 'PQD_Live_CmdFile',    cmd_file);
    setappdata(0, 'PQD_Live_TcpPort',    tcp_port);
    setappdata(0, 'PQD_Live_Continuous', true);

    %% 8. Dynamically attach pqd_live_streamer S-Function block in memory
    fprintf('[ContinuousSim] Attaching Level-2 S-Function live streamer...\n');
    streamer_blk = [mdl '/PQD_Live_Streamer'];
    from_v_blk   = [mdl '/PQD_From_V5'];
    from_i_blk   = [mdl '/PQD_From_I5'];

    % Add S-Function block
    add_block('simulink/User-Defined Functions/Level-2 MATLAB S-Function', ...
              streamer_blk, 'FunctionName', 'pqd_live_streamer');

    % Connect Bus 5 measurements
    add_block('simulink/Signal Routing/From', from_v_blk, 'GotoTag', 'Vabc_5');
    add_block('simulink/Signal Routing/From', from_i_blk, 'GotoTag', 'Iabc_5');
    add_line(mdl, 'PQD_From_V5/1', 'PQD_Live_Streamer/1');
    add_line(mdl, 'PQD_From_I5/1', 'PQD_Live_Streamer/2');

    % Connect external disturbance triggers
    set_param(fault_blk, 'External', 'on');
    add_line(mdl, 'PQD_Live_Streamer/1', 'PQD_Fault_Sag/1');

    set_param(swl_brk, 'External', 'on');
    add_line(mdl, 'PQD_Live_Streamer/2', 'PQD_Breaker_Swell/1');

    set_param(int_brk, 'External', 'on');
    add_line(mdl, 'PQD_Live_Streamer/3', 'PQD_Breaker_Interruption/1');

    fprintf('[ContinuousSim] Streamer attached successfully.\n');

    %% 9. Run continuous simulation (StopTime = inf)
    fprintf('[ContinuousSim] Starting continuous simulation loop (StopTime=inf, Pacing=1.0 s/s)...\n');
    t_start = tic;
    try
        sim(mdl, 'StopTime', 'inf');
    catch ME
        if contains(ME.identifier, 'StoppedByUser') || contains(ME.message, 'SimulationCommand')
            fprintf('[ContinuousSim] Simulation stopped gracefully by command.\n');
        else
            fprintf('[ContinuousSim] Simulation exited: %s (%s)\n', ME.message, ME.identifier);
        end
    end
    t_elapsed = toc(t_start);
    fprintf('[ContinuousSim] Continuous run ended after %.1f s wall-clock.\n', t_elapsed);

    %% 10. Notify backend of stop/complete
    complete_url = [server_url '/api/live/simulation/complete'];
    try
        done_payload = struct('run_id', run_id, 'status', 'stopped', 'wall_time_s', t_elapsed);
        opts = weboptions('MediaType','application/json','Timeout',5);
        webwrite(complete_url, jsonencode(done_payload), opts);
        fprintf('[ContinuousSim] Stopped notification sent.\n');
    catch
    end

    %% 11. Cleanup and discard changes (model is NEVER saved)
    set_param(mdl, 'Dirty', 'off');
    close_system(mdl, 0);
    fprintf('[ContinuousSim] Model closed cleanly without saving.\n');
end

function cleanup_sim(mdl)
    try
        if bdIsLoaded(mdl)
            set_param(mdl, 'Dirty', 'off');
            close_system(mdl, 0);
            fprintf('[ContinuousSim] Cleanup: %s closed.\n', mdl);
        end
    catch
    end
end

