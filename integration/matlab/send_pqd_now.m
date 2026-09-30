function send_pqd_now()
% SEND_PQD_NOW Transfers the latest Simulink simulation run from MATLAB to the frontend.
%
% Call this immediately after running IEEE_9bus_PQD_HIL_R2025a in Simulink GUI,
% or use stream_simulink_live for continuous live streaming.

    cur_dir = fileparts(mfilename('fullpath'));
    project_root = fullfile(cur_dir, '..', '..');
    addpath(fullfile(project_root, 'integration', 'matlab'));
    addpath(fullfile(project_root, 'IEEE_9bus'));

    v_data = [];
    t_data = [];
    i_data = [];

    % 1. Check ans (default variable when clicking Run in Simulink GUI)
    if evalin('base', 'exist(''ans'', ''var'')')
        ans_var = evalin('base', 'ans');
        if isprop(ans_var, 'PQD_Vabc') || isfield(ans_var, 'PQD_Vabc')
            v_ts = ans_var.PQD_Vabc;
            t_data = v_ts.Time;
            v_data = v_ts.Data;
            if isprop(ans_var, 'PQD_Iabc') || isfield(ans_var, 'PQD_Iabc')
                i_data = ans_var.PQD_Iabc.Data;
            end
        end
    end

    % 2. Check out
    if isempty(v_data) && evalin('base', 'exist(''out'', ''var'')')
        out_var = evalin('base', 'out');
        if isprop(out_var, 'PQD_Vabc') || isfield(out_var, 'PQD_Vabc')
            v_ts = out_var.PQD_Vabc;
            t_data = v_ts.Time;
            v_data = v_ts.Data;
            if isprop(out_var, 'PQD_Iabc') || isfield(out_var, 'PQD_Iabc')
                i_data = out_var.PQD_Iabc.Data;
            end
        end
    end

    % 3. Check direct variable
    if isempty(v_data) && evalin('base', 'exist(''PQD_Vabc'', ''var'')')
        v_ts = evalin('base', 'PQD_Vabc');
        t_data = v_ts.Time;
        v_data = v_ts.Data;
        if evalin('base', 'exist(''PQD_Iabc'', ''var'')')
            i_ts = evalin('base', 'PQD_Iabc');
            i_data = i_ts.Data;
        end
    end

    if isempty(v_data)
        fprintf('\n[send_pqd_now] No simulation data found in workspace.\n');
        fprintf('Run the IEEE 9-bus simulation in Simulink first, or run: run_simulink_pqd\n\n');
        return;
    end

    target_fs = 5000.0;
    fprintf('\n[send_pqd_now] Transferring Bus 5 measurements (%d points) to frontend...\n', length(t_data));

    [v_5k, ~] = resample(v_data, t_data, target_fs);
    if ~isempty(i_data)
        [i_5k, ~] = resample(i_data, t_data, target_fs);
    else
        i_5k = [];
    end

    client = pqd_stream_client('sampling_rate_hz', target_fs, 'nominal_frequency_hz', 60.0);
    if ~client.check_health()
        fprintf('[send_pqd_now] Python server is offline. Start python server.py 8500 first.\n');
        return;
    end

    batch_size = 1000;
    num_chunks = floor(size(v_5k, 1) / batch_size);
    if num_chunks < 1
        num_chunks = 1;
        batch_size = size(v_5k, 1);
    end

    for k = 1:num_chunks
        idx_s = (k - 1) * batch_size + 1;
        idx_e = idx_s + batch_size - 1;
        chunk_v = v_5k(idx_s:idx_e, :);
        chunk_i = [];
        if ~isempty(i_5k)
            chunk_i = i_5k(idx_s:idx_e, :);
        end
        [ack, lat_ms] = client.send_chunk(chunk_v, 'Iabc', chunk_i, 'seq_num', k);
        fprintf('  -> Chunk #%d (%d samples) sent in %.1f ms | Status: %s\n', ...
            k, size(chunk_v, 1), lat_ms, ack.status);
    end

    fprintf('[send_pqd_now] SUCCESS: Live readings captured and displayed on frontend!\n\n');
end
