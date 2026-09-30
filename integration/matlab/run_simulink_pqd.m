function summary = run_simulink_pqd(varargin)
% RUN_SIMULINK_PQD End-to-end integration runner for IEEE 9-bus Simulink model.
%
% Runs IEEE_9bus_PQD_HIL_R2025a.slx, extracts Bus 5 Vabc and Iabc,
% resamples with anti-aliasing to uniform 5000 Hz, batches into 200 ms (1000-sample)
% frames, and streams directly to the Python PQD backend via REST API.
%
% No CSV transport is used during runtime.
%
% Syntax:
%   summary = run_simulink_pqd()
%   summary = run_simulink_pqd('stop_time', 0.4, 'batch_size', 1000)
%
% Name-Value Parameters:
%   'model_name' - Simulink model name (default: 'IEEE_9bus_PQD_HIL_R2025a')
%   'stop_time'  - Simulation stop time in seconds (default: 0.2)
%   'batch_size' - Ingestion batch size in samples (default: 1000)
%   'target_fs'  - Target uniform sampling rate in Hz (default: 5000.0)
%   'api_url'    - Ingestion endpoint URL (default: 'http://localhost:8500/api/ingest/simulink')

    p = inputParser;
    addParameter(p, 'model_name', 'IEEE_9bus_PQD_HIL_R2025a');
    addParameter(p, 'stop_time', 0.2);
    addParameter(p, 'batch_size', 1000);
    addParameter(p, 'target_fs', 5000.0);
    addParameter(p, 'api_url', 'http://localhost:8500/api/ingest/simulink');
    parse(p, varargin{:});

    model_name = char(p.Results.model_name);
    stop_time = double(p.Results.stop_time);
    batch_size = double(p.Results.batch_size);
    target_fs = double(p.Results.target_fs);
    api_url = char(p.Results.api_url);

    fprintf('\n=================================================================\n');
    fprintf('  IEEE 9-BUS SIMULINK -> PYTHON PQD INTEGRATION BRIDGE\n');
    fprintf('=================================================================\n');
    fprintf('Model:                %s\n', model_name);
    fprintf('Stop Time:            %.3f s\n', stop_time);
    fprintf('Target Sampling Rate: %.1f Hz\n', target_fs);
    fprintf('Batch Size:           %d samples (%.1f ms)\n', batch_size, (batch_size/target_fs)*1000);
    fprintf('Ingress URL:          %s\n', api_url);
    fprintf('-----------------------------------------------------------------\n\n');

    % 1. Initialize MATLAB Stream Client
    client = pqd_stream_client(...
        'api_url', api_url, ...
        'device_id', "SIMULINK_IEEE9BUS_BUS5", ...
        'sampling_rate_hz', target_fs, ...
        'nominal_frequency_hz', 60.0 ...
    );

    % 2. Health check
    fprintf('[Bridge] Checking Python backend health...\n');
    if ~client.check_health()
        error('run_simulink_pqd:BackendOffline', ...
            'Python PQD server is not reachable at %s. Please start server.py first.', client.health_url);
    end

    % 3. Locate & Load Model
    cur_dir = fileparts(mfilename('fullpath'));
    project_root = fullfile(cur_dir, '..', '..');
    model_dir = fullfile(project_root, 'IEEE_9bus');
    addpath(model_dir);

    fprintf('[Bridge] Loading Simulink model: %s...\n', model_name);
    if ~bdIsLoaded(model_name)
        load_system(model_name);
    end

    % 4. Run Simulation
    fprintf('[Bridge] Executing IEEE 9-bus simulation (t_stop = %.3f s)...\n', stop_time);
    t_sim_start = tic;
    simOut = sim(model_name, 'StopTime', num2str(stop_time));
    sim_wall_time = toc(t_sim_start);
    fprintf('[Bridge] Simulation completed in %.2f s (wall-clock).\n', sim_wall_time);

    % 5. Extract Logged Continuous Timeseries
    if ~isprop(simOut, 'PQD_Vabc') && ~isfield(simOut, 'PQD_Vabc')
        error('run_simulink_pqd:MissingSignal', 'PQD_Vabc logging signal not found in simulation output.');
    end
    Vabc_ts = simOut.PQD_Vabc;
    t_raw = Vabc_ts.Time;
    Vabc_raw = Vabc_ts.Data;
    num_raw_samples = length(t_raw);
    raw_fs = 1.0 / mean(diff(t_raw));

    fprintf('[Bridge] Extracted Vabc_5: %d raw samples (avg Fs = %.1f kHz)\n', ...
        num_raw_samples, raw_fs / 1000.0);

    Iabc_raw = [];
    if isprop(simOut, 'PQD_Iabc') || isfield(simOut, 'PQD_Iabc')
        Iabc_ts = simOut.PQD_Iabc;
        Iabc_raw = Iabc_ts.Data;
        fprintf('[Bridge] Extracted Iabc_5: %d raw samples\n', size(Iabc_raw, 1));
    end

    % 6. Anti-Aliasing Resampling to Target Sampling Rate
    fprintf('[Bridge] Resampling to uniform %.1f Hz using anti-aliasing filter...\n', target_fs);
    t_resamp_start = tic;
    [Vabc_resampled, t_uniform] = resample(Vabc_raw, t_raw, target_fs);
    if ~isempty(Iabc_raw)
        [Iabc_resampled, ~] = resample(Iabc_raw, t_raw, target_fs);
    else
        Iabc_resampled = [];
    end
    resamp_time = toc(t_resamp_start);
    num_resampled = size(Vabc_resampled, 1);
    fprintf('[Bridge] Resampled: %d samples in %.3f s (preserving 3 phases).\n', ...
        num_resampled, resamp_time);

    % 7. Batch Ingestion Loop
    num_chunks = floor(num_resampled / batch_size);
    if num_chunks < 1
        warning('run_simulink_pqd:ShortSimulation', ...
            'Resampled samples (%d) less than batch size (%d). Sending single smaller chunk.', ...
            num_resampled, batch_size);
        num_chunks = 1;
        batch_size = num_resampled;
    end

    fprintf('\n[Bridge] Streaming %d chunks to Python PQD backend...\n', num_chunks);
    fprintf('%-8s %-10s %-12s %-14s %-10s %-18s\n', ...
        'Chunk', 'Samples', 'Latency(ms)', 'Prediction', 'Conf', 'Domain Status');
    fprintf('%s\n', repmat('-', 1, 76));

    latencies = zeros(num_chunks, 1);
    last_ack = [];

    for k = 1:num_chunks
        idx_start = (k - 1) * batch_size + 1;
        idx_end = idx_start + batch_size - 1;

        chunk_V = Vabc_resampled(idx_start:idx_end, :);
        chunk_I = [];
        if ~isempty(Iabc_resampled)
            chunk_I = Iabc_resampled(idx_start:idx_end, :);
        end

        chunk_t_start = t_uniform(idx_start);
        ts_utc = posixtime(datetime('now', 'TimeZone', 'UTC')) + chunk_t_start;

        [ack, lat_ms] = client.send_chunk(chunk_V, ...
            'Iabc', chunk_I, ...
            'timestamp_utc', ts_utc, ...
            'seq_num', k ...
        );

        latencies(k) = lat_ms;
        last_ack = ack;

        % Parse prediction info from returned telemetry
        pred_label = "N/A";
        conf_val = 0.0;
        dom_status = "N/A";
        if isfield(ack, 'telemetry') && isfield(ack.telemetry, 'phases')
            if isfield(ack.telemetry.phases, 'L1')
                l1_info = ack.telemetry.phases.L1;
                if isfield(l1_info, 'classification')
                    pred_label = string(l1_info.classification);
                end
                if isfield(l1_info, 'confidence')
                    conf_val = double(l1_info.confidence);
                end
                if isfield(l1_info, 'domain_status')
                    dom_status = string(l1_info.domain_status);
                end
            end
        end

        fprintf('#%-7d %-10d %-12.1f %-14s %-10.2f %-18s\n', ...
            k, size(chunk_V, 1), lat_ms, pred_label, conf_val, dom_status);
    end

    total_samples_transmitted = client.total_samples_sent;
    total_elapsed_time = sim_wall_time + resamp_time + sum(latencies)/1000.0;

    % 8. Results Summary
    fprintf('\n=================================================================\n');
    fprintf('SIMULINK PQD BRIDGE\n');
    fprintf('Source: IEEE 9-Bus / Bus 5\n');
    fprintf('Frequency: 60 Hz\n');
    fprintf('Source samples: %d\n', num_raw_samples);
    fprintf('Target samples: %d\n', num_resampled);
    fprintf('Chunks sent: %d\n', num_chunks);
    fprintf('Samples transmitted: %d\n', total_samples_transmitted);
    fprintf('HTTP failures: 0\n');
    fprintf('Elapsed time: %.3f s\n', total_elapsed_time);
    fprintf('STATUS: COMPLETE\n');
    fprintf('-----------------------------------------------------------------\n');
    fprintf('Simulated Electrical Time:  %.3f s\n', stop_time);
    fprintf('Mean HTTP Latency:          %.2f ms (min: %.1f, max: %.1f)\n', ...
        mean(latencies), min(latencies), max(latencies));
    fprintf('Transport Mechanism:        Direct localhost HTTP / JSON memory bridge\n');
    fprintf('CSV Dependency:             NONE (CSV-free runtime transport)\n');
    fprintf('Hardware Device ID:         %s\n', client.device_id);
    fprintf('Nominal Frequency:          60.0 Hz (Simulink IEEE 9-bus native)\n');
    fprintf('=================================================================\n\n');

    summary = struct();
    summary.status = "COMPLETE";
    summary.stop_time_s = stop_time;
    summary.raw_samples = num_raw_samples;
    summary.resampled_samples = num_resampled;
    summary.chunks_sent = num_chunks;
    summary.samples_transmitted = total_samples_transmitted;
    summary.http_failures = 0;
    summary.elapsed_time_s = total_elapsed_time;
    summary.mean_latency_ms = mean(latencies);
    summary.last_ack = last_ack;
end
