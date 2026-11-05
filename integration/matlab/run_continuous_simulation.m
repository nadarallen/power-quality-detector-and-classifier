function run_continuous_simulation(config_json_path)
% run_continuous_simulation  —  Continuous SIL Simulation Driver for IEEE 9-bus
%
% Implements a persistent, continuous Software-in-the-Loop simulation session:
% - Loads IEEE_9bus_PQD_DISTURBANCES.slx once in memory
% - Configures continuous execution (StopTime = inf)
% - Enables Simulink Pacing (1.0 s/s) for real-time 1:1 execution
% - Attaches Level-2 S-Function streamer (5 kHz, 250-sample chunks)
% - Streamer runs decoupled in solver (pushes to in-memory FIFO queue)
% - Main script consumer drains queue and sends chunks via TCP to Python (127.0.0.1:8502)
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

    %% 3. Ensure required base workspace variables exist
    dummy_ts     = timeseries([0 0 0; 0 0 0], [0; 1]);
    dummy_single = timeseries([0; 0],          [0; 1]);
    assignin('base', 'harm_inj_signal',    dummy_ts);
    assignin('base', 'flicker_inj_signal', dummy_ts);
    assignin('base', 'notch_ctrl_signal',  dummy_single);

    %% 4. Configure solver and real-time pacing
    set_param(mdl, 'StopFcn', '');
    set_param(mdl, 'Solver',  'ode23tb');
    set_param(mdl, 'RelTol',  '1e-4');
    set_param(mdl, 'MaxStep', '2.5e-5');
    set_param(mdl, 'StopTime', 'inf');
    set_param(mdl, 'EnablePacing', 'on');
    set_param(mdl, 'PacingRate', 1.0);
    set_param(mdl, 'ReturnWorkspaceOutputs', 'off');
    fprintf('[ContinuousSim] Configured: StopTime=inf, ode23tb, MaxStep=2.5e-5, PacingRate=1.0 s/s.\n');

    %% 5. Disturbance block handles
    fault_blk = [mdl '/PQD_Fault_Sag'];
    swl_brk   = [mdl '/PQD_Breaker_Swell'];
    swl_cap   = [mdl '/PQD_Cap_Swell'];
    int_brk   = [mdl '/PQD_Breaker_Interruption'];
    trn_brk   = [mdl '/PQD_Breaker_Transient'];
    trn_rlc   = [mdl '/PQD_RLC_Transient'];
    notch_blk = [mdl '/PQD_Notch_Bus5'];

    %% 6. Reset all disturbance blocks to initial dormant baseline
    set_param(fault_blk, 'FaultA', 'on', 'FaultB', 'on', 'FaultC', 'on', ...
              'GroundFault', 'on', 'SwitchTimes', '[999 1000]', ...
              'FaultResistance', '2.0', 'GroundResistance', '0.01');
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
    setappdata(0, 'PQD_Live_ChunkQueue', {});
    setappdata(0, 'PQD_Live_DroppedCount', 0);
    setappdata(0, 'PQD_ActiveDisturbance', 'Normal');
    setappdata(0, 'PQD_DistDurationSamples', 0);

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

    %% 9. Establish TCP connection to Python backend receiver
    tcpClient = [];
    fprintf('[ContinuousSim] Connecting to Python TCP telemetry receiver on 127.0.0.1:%d ...\n', tcp_port);
    for retry = 1:15
        try
            tcpClient = tcpclient('127.0.0.1', tcp_port, 'Timeout', 3);
            fprintf('[ContinuousSim] Connected to TCP telemetry server (attempt %d).\n', retry);
            break;
        catch
            pause(0.5);
        end
    end
    if isempty(tcpClient)
        fprintf('[ContinuousSim] Warning: TCP connection failed. Will stream via HTTP fallback.\n');
    end

    %% 10. Start non-blocking continuous simulation
    fprintf('[ContinuousSim] Launching Simulink model asynchronously (SimulationCommand=start)...\n');
    set_param(mdl, 'SimulationCommand', 'start');

    t_start = tic;
    chunks_sent = 0;

    %% 11. Consumer loop: drain queue to TCP and poll mid-run commands
    while true
        sim_status = get_param(mdl, 'SimulationStatus');
        if strcmp(sim_status, 'stopped')
            fprintf('[ContinuousSim] SimulationStatus reported stopped.\n');
            break;
        end

        % 11a. Drain in-memory chunk queue
        queue = getappdata(0, 'PQD_Live_ChunkQueue');
        if ~isempty(queue)
            while ~isempty(queue)
                chunk = queue{1};
                queue(1) = [];
                setappdata(0, 'PQD_Live_ChunkQueue', queue);

                % Transmit chunk
                if ~isempty(tcpClient)
                    try
                        raw_json = jsonencode(chunk);
                        write(tcpClient, uint8([raw_json char(10)]));
                        chunks_sent = chunks_sent + 1;
                    catch TCP_ERR
                        fprintf('[ContinuousSim] TCP write error: %s\n', TCP_ERR.message);
                        tcpClient = [];
                    end
                else
                    % HTTP fallback
                    try
                        post_url = [server_url '/api/ingest/simulink'];
                        opts = weboptions('MediaType', 'application/json', 'Timeout', 2);
                        webwrite(post_url, chunk, opts);
                        chunks_sent = chunks_sent + 1;
                    catch
                    end
                end

                % Re-fetch queue in case new chunks arrived
                queue = getappdata(0, 'PQD_Live_ChunkQueue');
            end
        end

        % 11b. Check command file for runtime injection / reset / stop
        if ~isempty(cmd_file) && exist(cmd_file, 'file')
            try
                cmd_raw = fileread(cmd_file);
                delete(cmd_file);
                cmd = jsondecode(cmd_raw);
                action = cmd.action;

                if strcmp(action, 'inject')
                    dist = cmd.disturbance;
                    dur_s = 0.10;
                    if isfield(cmd, 'duration_s'), dur_s = double(cmd.duration_s); end
                    dur_samples = round(dur_s * 5000);

                    setappdata(0, 'PQD_DistDurationSamples', dur_samples);
                    setappdata(0, 'PQD_ActiveDisturbance', dist);
                    fprintf('[ContinuousSim] INJECT applied via S-Function trigger: %s for %.3f s (%d samples)\n', dist, dur_s, dur_samples);

                elseif strcmp(action, 'reset')
                    setappdata(0, 'PQD_ActiveDisturbance', 'Normal');
                    setappdata(0, 'PQD_DistDurationSamples', 0);
                    fprintf('[ContinuousSim] RESET applied: restored to Normal.\n');

                elseif strcmp(action, 'pause')
                    set_param(mdl, 'SimulationCommand', 'pause');
                    fprintf('[ContinuousSim] PAUSE applied.\n');

                elseif strcmp(action, 'continue')
                    set_param(mdl, 'SimulationCommand', 'continue');
                    fprintf('[ContinuousSim] CONTINUE applied.\n');

                elseif strcmp(action, 'stop')
                    fprintf('[ContinuousSim] STOP requested by command.\n');
                    break;
                end
            catch CMD_ERR
                fprintf('[ContinuousSim] Error processing command: %s\n', CMD_ERR.message);
            end
        end

        pause(0.02);
    end

    t_elapsed = toc(t_start);
    fprintf('[ContinuousSim] Continuous run loop ended after %.1f s wall-clock (%d chunks sent).\n', t_elapsed, chunks_sent);

    %% 12. Graceful stop and cleanup
    try
        curr_stat = get_param(mdl, 'SimulationStatus');
        if strcmp(curr_stat, 'running') || strcmp(curr_stat, 'paused')
            set_param(mdl, 'SimulationCommand', 'stop');
        end
    catch
    end

    if ~isempty(tcpClient)
        try, delete(tcpClient); clear tcpClient; catch, end
    end

    %% 13. Notify backend of stop/complete
    complete_url = [server_url '/api/live/simulation/complete'];
    try
        done_payload = struct('run_id', run_id, 'status', 'stopped', 'wall_time_s', t_elapsed, 'chunks_sent', chunks_sent);
        opts = weboptions('MediaType', 'application/json', 'Timeout', 5);
        webwrite(complete_url, done_payload, opts);
        fprintf('[ContinuousSim] Complete notification sent to backend.\n');
    catch
    end

    fprintf('[ContinuousSim] Session complete. Closing model without saving.\n');
    close_system(mdl, 0);
end

function cleanup_sim(mdl)
    try
        if bdIsLoaded(mdl)
            stat = get_param(mdl, 'SimulationStatus');
            if strcmp(stat, 'running') || strcmp(stat, 'paused')
                set_param(mdl, 'SimulationCommand', 'stop');
            end
            close_system(mdl, 0);
        end
    catch
    end
end
