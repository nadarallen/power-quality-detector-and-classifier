function pqd_live_streamer(block)
% pqd_live_streamer  —  Level-2 MATLAB S-Function for Continuous SIL Simulation
%
% Performs non-blocking 5 kHz incremental acquisition and streaming during active
% Simulink solver execution, and provides real-time disturbance control triggers
% to IEEE 9-bus disturbance subsystems (PQD_Fault_Sag, PQD_Breaker_Swell, etc.).
%
% Inputs:
%   Port 1: Vabc (3 channels, Bus 5 three-phase voltage in pu)
%   Port 2: Iabc (3 channels, Bus 5 three-phase line current in pu)
%
% Outputs:
%   Port 1: Sag_Trigger (0 = normal, 1 = fault active)
%   Port 2: Swell_Trigger (0 = open, 1 = closed / capacitor connected)
%   Port 3: Int_Trigger (0 = normal / closed, 1 = tripped / open)

    setup(block);
end

function setup(block)
    block.NumInputPorts  = 2;
    block.NumOutputPorts = 3;

    block.SetPreCompInpPortInfoToDynamic;
    block.SetPreCompOutPortInfoToDynamic;

    % Input 1: Vabc (3 channels)
    block.InputPort(1).Dimensions        = 3;
    block.InputPort(1).DirectFeedthrough = true;

    % Input 2: Iabc (3 channels)
    block.InputPort(2).Dimensions        = 3;
    block.InputPort(2).DirectFeedthrough = true;

    % Output 1: Sag control (1)
    block.OutputPort(1).Dimensions       = 1;
    % Output 2: Swell control (1)
    block.OutputPort(2).Dimensions       = 1;
    % Output 3: Interruption control (1)
    block.OutputPort(3).Dimensions       = 1;

    % Discrete sample time: 5000 Hz (dt = 0.0002 s = 200 us)
    block.SampleTimes = [0.0002 0];

    block.RegBlockMethod('PostPropagationSetup', @DoPostPropSetup);
    block.RegBlockMethod('Start', @Start);
    block.RegBlockMethod('Outputs', @Outputs);
    block.RegBlockMethod('Terminate', @Terminate);
end

function DoPostPropSetup(block)
    block.NumDworks = 8;
    % 1: SampleCount
    block.Dwork(1).Name            = 'SampleCount';
    block.Dwork(1).Dimensions      = 1;
    block.Dwork(1).DatatypeID      = 0;
    block.Dwork(1).Complexity      = 'Real';
    block.Dwork(1).UsedAsDiscState = true;

    % 2: ChunkSeq
    block.Dwork(2).Name            = 'ChunkSeq';
    block.Dwork(2).Dimensions      = 1;
    block.Dwork(2).DatatypeID      = 0;
    block.Dwork(2).Complexity      = 'Real';
    block.Dwork(2).UsedAsDiscState = true;

    % 3: SagTrigger
    block.Dwork(3).Name            = 'SagTrigger';
    block.Dwork(3).Dimensions      = 1;
    block.Dwork(3).DatatypeID      = 0;
    block.Dwork(3).Complexity      = 'Real';
    block.Dwork(3).UsedAsDiscState = true;

    % 4: SwlTrigger
    block.Dwork(4).Name            = 'SwlTrigger';
    block.Dwork(4).Dimensions      = 1;
    block.Dwork(4).DatatypeID      = 0;
    block.Dwork(4).Complexity      = 'Real';
    block.Dwork(4).UsedAsDiscState = true;

    % 5: IntTrigger
    block.Dwork(5).Name            = 'IntTrigger';
    block.Dwork(5).Dimensions      = 1;
    block.Dwork(5).DatatypeID      = 0;
    block.Dwork(5).Complexity      = 'Real';
    block.Dwork(5).UsedAsDiscState = true;

    % 6: InjectionOnsetSimTime
    block.Dwork(6).Name            = 'InjectionOnsetSimTime';
    block.Dwork(6).Dimensions      = 1;
    block.Dwork(6).DatatypeID      = 0;
    block.Dwork(6).Complexity      = 'Real';
    block.Dwork(6).UsedAsDiscState = true;

    % 7: InjectionDurationRemaining (samples)
    block.Dwork(7).Name            = 'InjectionDurationRemaining';
    block.Dwork(7).Dimensions      = 1;
    block.Dwork(7).DatatypeID      = 0;
    block.Dwork(7).Complexity      = 'Real';
    block.Dwork(7).UsedAsDiscState = true;

    % 8: ActiveDisturbanceId (0=Normal, 1=Sag, 2=Swell, 3=Interruption)
    block.Dwork(8).Name            = 'ActiveDisturbanceId';
    block.Dwork(8).Dimensions      = 1;
    block.Dwork(8).DatatypeID      = 0;
    block.Dwork(8).Complexity      = 'Real';
    block.Dwork(8).UsedAsDiscState = true;
end

function Start(block)
    block.Dwork(1).Data = 0;
    block.Dwork(2).Data = 0;
    block.Dwork(3).Data = 0;
    block.Dwork(4).Data = 0;
    block.Dwork(5).Data = 0;
    block.Dwork(6).Data = -1.0;
    block.Dwork(7).Data = 0;
    block.Dwork(8).Data = 0;

    setappdata(0, 'PQD_Live_VBuf', []);
    setappdata(0, 'PQD_Live_IBuf', []);
    setappdata(0, 'PQD_Live_TBuf', []);
    setappdata(0, 'PQD_Live_LastCmdTime', 0);

    % Connect persistent TCP socket client if port configured
    tcp_port = getappdata(0, 'PQD_Live_TcpPort');
    if isempty(tcp_port), tcp_port = 8502; end
    try
        t_client = tcpclient('127.0.0.1', tcp_port, 'Timeout', 1);
        setappdata(0, 'PQD_Live_TcpClient', t_client);
        fprintf('[LiveStream] Fast local TCP transport connected on port %d.\n', tcp_port);
    catch
        setappdata(0, 'PQD_Live_TcpClient', []);
        fprintf('[LiveStream] TCP connect skipped (will use HTTP POST fallback).\n');
    end
end

function Outputs(block)
    count = block.Dwork(1).Data + 1;
    block.Dwork(1).Data = count;
    t_sim = block.CurrentTime;

    v_sample = block.InputPort(1).Data;
    i_sample = block.InputPort(2).Data;

    v_buf = getappdata(0, 'PQD_Live_VBuf');
    i_buf = getappdata(0, 'PQD_Live_IBuf');
    t_buf = getappdata(0, 'PQD_Live_TBuf');

    v_buf(end+1, 1:3) = v_sample(1:3);
    i_buf(end+1, 1:3) = i_sample(1:3);
    t_buf(end+1, 1)   = t_sim;

    %% 1. Poll command file for real-time injection / reset / stop (every 25 steps = 5 ms)
    cmd_file = getappdata(0, 'PQD_Live_CmdFile');
    if ~isempty(cmd_file) && mod(count, 25) == 0 && exist(cmd_file, 'file')
        f_info = dir(cmd_file);
        last_cmd_t = getappdata(0, 'PQD_Live_LastCmdTime');
        if ~isempty(f_info) && f_info.datenum > last_cmd_t
            setappdata(0, 'PQD_Live_LastCmdTime', f_info.datenum);
            try
                cmd_text = fileread(cmd_file);
                cmd = jsondecode(cmd_text);
                if isfield(cmd, 'action')
                    if strcmp(cmd.action, 'inject')
                        dist = cmd.disturbance;
                        dur_s = 0.10;
                        if isfield(cmd, 'duration_s')
                            dur_s = double(cmd.duration_s);
                        elseif isfield(cmd, 'params') && isfield(cmd.params, 'duration_ms')
                            dur_s = double(cmd.params.duration_ms) / 1000.0;
                        end

                        % Reset all triggers first
                        block.Dwork(3).Data = 0;
                        block.Dwork(4).Data = 0;
                        block.Dwork(5).Data = 0;

                        if strcmp(dist, 'Sag')
                            block.Dwork(3).Data = 1.0;
                            block.Dwork(8).Data = 1.0;
                        elseif strcmp(dist, 'Swell')
                            block.Dwork(4).Data = 1.0;
                            block.Dwork(8).Data = 2.0;
                        elseif strcmp(dist, 'Interruption')
                            block.Dwork(5).Data = 1.0;
                            block.Dwork(8).Data = 3.0;
                        end

                        block.Dwork(6).Data = t_sim;
                        if dur_s > 0
                            block.Dwork(7).Data = round(dur_s * 5000); % remaining samples
                        else
                            block.Dwork(7).Data = -1; % continuous until reset
                        end
                        fprintf('[LiveStream] INJECTED %s at t=%.3f s (dur=%.0f ms)\n', ...
                                dist, t_sim, dur_s * 1000);

                    elseif strcmp(cmd.action, 'reset')
                        block.Dwork(3).Data = 0.0;
                        block.Dwork(4).Data = 0.0;
                        block.Dwork(5).Data = 0.0;
                        block.Dwork(7).Data = 0;
                        block.Dwork(8).Data = 0.0;
                        fprintf('[LiveStream] RESET TO NORMAL at t=%.3f s\n', t_sim);

                    elseif strcmp(cmd.action, 'stop')
                        fprintf('[LiveStream] STOP COMMAND received at t=%.3f s -> Stopping Simulink...\n', t_sim);
                        set_param(bdroot, 'SimulationCommand', 'stop');
                    end
                end
            catch
            end
        end
    end

    % Check if timed disturbance duration expired
    if block.Dwork(7).Data > 0
        block.Dwork(7).Data = block.Dwork(7).Data - 1;
        if block.Dwork(7).Data <= 0
            % Duration expired -> auto-recover to normal baseline
            block.Dwork(3).Data = 0.0;
            block.Dwork(4).Data = 0.0;
            block.Dwork(5).Data = 0.0;
            block.Dwork(8).Data = 0.0;
            fprintf('[LiveStream] Injected disturbance finished -> restored Normal at t=%.3f s\n', t_sim);
        end
    end

    %% 2. Output triggers to model blocks
    block.OutputPort(1).Data = block.Dwork(3).Data; % Sag trigger
    block.OutputPort(2).Data = block.Dwork(4).Data; % Swell trigger
    block.OutputPort(3).Data = block.Dwork(5).Data; % Interruption trigger

    %% 3. Incremental Chunk Streaming (Every 250 samples = 50 ms of 5 kHz data)
    chunk_size = 250;
    if size(v_buf, 1) >= chunk_size
        chunk_seq = block.Dwork(2).Data + 1;
        block.Dwork(2).Data = chunk_seq;

        run_id = getappdata(0, 'PQD_Live_RunId');
        if isempty(run_id), run_id = 'LIVE_RUN_DEFAULT'; end

        server_url = getappdata(0, 'PQD_Live_ServerUrl');
        if isempty(server_url), server_url = 'http://127.0.0.1:8500'; end

        % Strict validation against NaNs or Infs
        if any(isnan(v_buf(:))) || any(isinf(v_buf(:)))
            fprintf('[LiveStream] FATAL: NaN or Inf in simulated voltage!\n');
            error('pqd_live_streamer:InvalidSignal', 'NaN or Inf in simulated voltage waveform.');
        end

        payload = struct();
        payload.source               = 'simulink';
        payload.run_id               = run_id;
        payload.device_id            = 'SIMULINK_IEEE9BUS_BUS5';
        payload.sampling_rate_hz     = 5000;
        payload.nominal_frequency_hz = 60;
        payload.chunk_index          = chunk_seq;
        payload.sequence_number      = chunk_seq;
        payload.sim_time_start       = t_buf(1);
        payload.sim_time_end         = t_buf(end);
        payload.timestamp_utc        = posixtime(datetime('now', 'TimeZone', 'UTC'));

        payload.channels = struct( ...
            'L1', v_buf(:, 1).', ...
            'L2', v_buf(:, 2).', ...
            'L3', v_buf(:, 3).' );

        if ~isempty(i_buf) && ~any(isnan(i_buf(:))) && ~any(isinf(i_buf(:)))
            payload.current_channels = struct( ...
                'L1', i_buf(:, 1).', ...
                'L2', i_buf(:, 2).', ...
                'L3', i_buf(:, 3).' );
        end

        json_bytes = uint8([jsonencode(payload) newline]);

        % Send via fast non-blocking TCP socket if connected
        t_client = getappdata(0, 'PQD_Live_TcpClient');
        tcp_sent = false;
        if ~isempty(t_client)
            try
                write(t_client, json_bytes);
                tcp_sent = true;
            catch
                % TCP dropped -> fallback to HTTP
                t_client = [];
                setappdata(0, 'PQD_Live_TcpClient', []);
            end
        end

        if ~tcp_sent
            try
                opts = weboptions('MediaType', 'application/json', 'Timeout', 5);
                webwrite([server_url '/api/ingest/simulink'], jsonencode(payload), opts);
            catch ME
                if mod(chunk_seq, 20) == 0
                    fprintf('[LiveStream] HTTP Chunk %d warning: %s\n', chunk_seq, ME.message);
                end
            end
        end

        v_buf = [];
        i_buf = [];
        t_buf = [];
    end

    setappdata(0, 'PQD_Live_VBuf', v_buf);
    setappdata(0, 'PQD_Live_IBuf', i_buf);
    setappdata(0, 'PQD_Live_TBuf', t_buf);
end

function Terminate(block)
    % Clean up TCP client
    t_client = getappdata(0, 'PQD_Live_TcpClient');
    if ~isempty(t_client)
        try
            delete(t_client);
        catch
        end
    end

    if isappdata(0, 'PQD_Live_VBuf'),        rmappdata(0, 'PQD_Live_VBuf'); end
    if isappdata(0, 'PQD_Live_IBuf'),        rmappdata(0, 'PQD_Live_IBuf'); end
    if isappdata(0, 'PQD_Live_TBuf'),        rmappdata(0, 'PQD_Live_TBuf'); end
    if isappdata(0, 'PQD_Live_TcpClient'),   rmappdata(0, 'PQD_Live_TcpClient'); end
    if isappdata(0, 'PQD_Live_LastCmdTime'), rmappdata(0, 'PQD_Live_LastCmdTime'); end
end
