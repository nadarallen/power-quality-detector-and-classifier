function stream_simulink_live(varargin)
% STREAM_SIMULINK_LIVE Continuous live simulation and streaming engine.
%
% Runs the IEEE 9-bus simulation in an active live loop, continuously pushing
% synchronized 3-phase waveforms and measurements directly into the Python PQD backend.
% The live frontend dashboard updates in real-time as each chunk arrives.
%
% Syntax:
%   stream_simulink_live()
%   stream_simulink_live('cycles', 20, 'pause_sec', 0.2)
%
% Name-Value Parameters:
%   'cycles'     - Number of streaming cycles to run (default: 10, or inf for continuous)
%   'stop_time'  - Simulation window duration per cycle in seconds (default: 0.2)
%   'pause_sec'  - Pause between streaming cycles in seconds (default: 0.1)
%   'target_fs'  - Target sampling rate in Hz (default: 5000.0)

    p = inputParser;
    addParameter(p, 'cycles', 10);
    addParameter(p, 'stop_time', 0.2);
    addParameter(p, 'pause_sec', 0.1);
    addParameter(p, 'target_fs', 5000.0);
    parse(p, varargin{:});

    cycles = p.Results.cycles;
    stop_time = double(p.Results.stop_time);
    pause_sec = double(p.Results.pause_sec);
    target_fs = double(p.Results.target_fs);

    model_name = 'IEEE_9bus_PQD_HIL_R2025a';
    cur_dir = fileparts(mfilename('fullpath'));
    project_root = fullfile(cur_dir, '..', '..');
    addpath(fullfile(project_root, 'IEEE_9bus'));
    addpath(cur_dir);

    fprintf('\n=================================================================\n');
    fprintf('  IEEE 9-BUS LIVE STREAMING TO WEB FRONTEND\n');
    fprintf('=================================================================\n');
    fprintf('Model:                %s\n', model_name);
    fprintf('Streaming Cycles:     %g (Press Ctrl+C to stop anytime)\n', cycles);
    fprintf('Cycle Duration:       %.2f s (%d samples @ %.1f Hz)\n', stop_time, round(stop_time * target_fs), target_fs);
    fprintf('Cycle Interval:       %.2f s\n', pause_sec);
    fprintf('=================================================================\n\n');

    client = pqd_stream_client('sampling_rate_hz', target_fs, 'nominal_frequency_hz', 60.0);
    if ~client.check_health()
        error('stream_simulink_live:BackendOffline', ...
            'Python PQD server is offline. Please start: python server.py 8500');
    end

    if ~bdIsLoaded(model_name)
        load_system(model_name);
    end

    c = 1;
    total_chunks = 0;
    while c <= cycles
        fprintf('[Live Stream] Running cycle #%d (t_stop = %.2f s)...\n', c, stop_time);
        t_start = tic;
        simOut = sim(model_name, 'StopTime', num2str(stop_time));
        sim_time = toc(t_start);

        v_ts = simOut.PQD_Vabc;
        t_raw = v_ts.Time;
        v_raw = v_ts.Data;

        i_raw = [];
        if isprop(simOut, 'PQD_Iabc') || isfield(simOut, 'PQD_Iabc')
            i_raw = simOut.PQD_Iabc.Data;
        end

        % Anti-aliasing resample
        [v_5k, t_5k] = resample(v_raw, t_raw, target_fs);
        if ~isempty(i_raw)
            [i_5k, ~] = resample(i_raw, t_raw, target_fs);
        else
            i_5k = [];
        end

        % Stream chunk
        chunk_len = min(1000, size(v_5k, 1));
        chunk_v = v_5k(1:chunk_len, :);
        chunk_i = [];
        if ~isempty(i_5k)
            chunk_i = i_5k(1:chunk_len, :);
        end

        ts_utc = posixtime(datetime('now', 'TimeZone', 'UTC'));
        total_chunks = total_chunks + 1;

        [ack, lat_ms] = client.send_chunk(chunk_v, ...
            'Iabc', chunk_i, ...
            'timestamp_utc', ts_utc, ...
            'seq_num', total_chunks ...
        );

        % Parse live status from telemetry
        pred = "NORMAL";
        if isfield(ack, 'telemetry') && isfield(ack.telemetry, 'phases') && isfield(ack.telemetry.phases, 'L1')
            pred = string(ack.telemetry.phases.L1.classification);
        end

        fprintf('  -> Sent chunk #%d (%d pts) | Latency: %.1f ms | Status: %s | Sim: %.2fs\n', ...
            total_chunks, chunk_len, lat_ms, pred, sim_time);

        if c < cycles && pause_sec > 0
            pause(pause_sec);
        end
        c = c + 1;
    end

    fprintf('\n[Live Stream] Streaming completed. Total chunks delivered to frontend: %d\n\n', total_chunks);
end
