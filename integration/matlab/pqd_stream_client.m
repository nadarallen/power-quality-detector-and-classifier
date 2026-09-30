classdef pqd_stream_client < handle
    % PQD_STREAM_CLIENT HTTP client for streaming Simulink waveforms to Python PQD backend.
    %
    % Sends synchronized three-phase chunks (L1, L2, L3) and optional current
    % channels (Ia, Ib, Ic) to POST /api/ingest/simulink with 60 Hz metadata.
    
    properties
        api_url (1,1) string = "http://localhost:8500/api/ingest/simulink"
        health_url (1,1) string = "http://localhost:8500/api/health"
        device_id (1,1) string = "SIMULINK_IEEE9BUS_BUS5"
        sampling_rate_hz (1,1) double = 5000.0
        nominal_frequency_hz (1,1) double = 60.0
        timeout_sec (1,1) double = 10.0
        max_retries (1,1) double = 3
        sequence_number (1,1) double = 0
        total_samples_sent (1,1) double = 0
        total_chunks_sent (1,1) double = 0
    end
    
    methods
        function obj = pqd_stream_client(varargin)
            % Constructor: accepts Name-Value pairs for configuration
            p = inputParser;
            addParameter(p, 'api_url', "http://localhost:8500/api/ingest/simulink");
            addParameter(p, 'health_url', "http://localhost:8500/api/health");
            addParameter(p, 'device_id', "SIMULINK_IEEE9BUS_BUS5");
            addParameter(p, 'sampling_rate_hz', 5000.0);
            addParameter(p, 'nominal_frequency_hz', 60.0);
            addParameter(p, 'timeout_sec', 10.0);
            addParameter(p, 'max_retries', 3);
            parse(p, varargin{:});
            
            obj.api_url = string(p.Results.api_url);
            obj.health_url = string(p.Results.health_url);
            obj.device_id = string(p.Results.device_id);
            obj.sampling_rate_hz = double(p.Results.sampling_rate_hz);
            obj.nominal_frequency_hz = double(p.Results.nominal_frequency_hz);
            obj.timeout_sec = double(p.Results.timeout_sec);
            obj.max_retries = double(p.Results.max_retries);
        end
        
        function is_healthy = check_health(obj)
            % Verifies connectivity with the Python PQD backend
            opts = weboptions('Timeout', obj.timeout_sec, 'ContentType', 'json');
            try
                res = webread(obj.health_url, opts);
                if isfield(res, 'status') && (strcmp(res.status, 'online') || strcmp(res.status, 'ok'))
                    fprintf('[pqd_stream_client] Python backend ONLINE at %s\n', obj.health_url);
                    is_healthy = true;
                else
                    fprintf('[pqd_stream_client] Unexpected response from backend: %s\n', jsonencode(res));
                    is_healthy = false;
                end
            catch ME
                fprintf('[pqd_stream_client] Health check FAILED: %s\n', ME.message);
                is_healthy = false;
            end
        end
        
        function [ack, latency_ms] = send_chunk(obj, Vabc, varargin)
            % SEND_CHUNK Ingests a synchronized three-phase waveform batch to Python.
            %
            % Inputs:
            %   Vabc - [N x 3] matrix of phase voltages [Va, Vb, Vc]
            %
            % Optional Name-Value pairs:
            %   'Iabc'          - [N x 3] matrix of phase currents [Ia, Ib, Ic]
            %   'timestamp_utc' - UTC timestamp (seconds since Unix epoch)
            %   'seq_num'       - Sequence number (auto-incremented if omitted)
            
            p = inputParser;
            addParameter(p, 'Iabc', []);
            addParameter(p, 'timestamp_utc', []);
            addParameter(p, 'seq_num', []);
            parse(p, varargin{:});
            
            Iabc = p.Results.Iabc;
            ts = p.Results.timestamp_utc;
            seq = p.Results.seq_num;
            
            if isempty(seq)
                obj.sequence_number = obj.sequence_number + 1;
                seq = obj.sequence_number;
            else
                obj.sequence_number = seq;
            end
            
            if isempty(ts)
                % POSIX time in seconds
                ts = posixtime(datetime('now', 'TimeZone', 'UTC'));
            end
            
            [num_samples, num_phases] = size(Vabc);
            if num_phases ~= 3
                error('Vabc must be an N x 3 matrix (Va, Vb, Vc). Got %d columns.', num_phases);
            end
            
            % Build JSON payload
            payload = struct();
            payload.source = "simulink";
            payload.device_id = obj.device_id;
            payload.sequence_number = seq;
            payload.timestamp_utc = ts;
            payload.sampling_rate_hz = obj.sampling_rate_hz;
            payload.nominal_frequency_hz = obj.nominal_frequency_hz;
            
            payload.channels = struct();
            payload.channels.L1 = Vabc(:, 1)';
            payload.channels.L2 = Vabc(:, 2)';
            payload.channels.L3 = Vabc(:, 3)';
            
            if ~isempty(Iabc) && size(Iabc, 2) == 3
                payload.current_channels = struct();
                payload.current_channels.Ia = Iabc(:, 1)';
                payload.current_channels.Ib = Iabc(:, 2)';
                payload.current_channels.Ic = Iabc(:, 3)';
            end
            
            opts = weboptions(...
                'MediaType', 'application/json', ...
                'Timeout', obj.timeout_sec, ...
                'ContentType', 'json' ...
            );
            
            % Send with retry policy
            ack = [];
            last_err = "";
            t_start = tic;
            for attempt = 1:obj.max_retries
                try
                    ack = webwrite(obj.api_url, payload, opts);
                    break;
                catch ME
                    last_err = ME.message;
                    if attempt < obj.max_retries
                        pause(0.2 * attempt);
                    end
                end
            end
            latency_ms = toc(t_start) * 1000.0;
            
            if isempty(ack)
                error('pqd_stream_client:SendFailed', ...
                    'Failed to send chunk #%d after %d attempts: %s', ...
                    seq, obj.max_retries, last_err);
            end
            
            obj.total_chunks_sent = obj.total_chunks_sent + 1;
            obj.total_samples_sent = obj.total_samples_sent + num_samples;
        end
    end
end
