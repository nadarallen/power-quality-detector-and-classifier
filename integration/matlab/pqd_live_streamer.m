function pqd_live_streamer(block)
% pqd_live_streamer  —  Level-2 MATLAB S-Function for High-Performance SIL Acquisition
%
% Strictly decoupled producer for continuous IEEE 9-bus live demonstration:
% - Discrete 5000 Hz acquisition of Bus 5 Three-Phase Voltage (Vabc) and Line Current (Iabc)
% - Bounded in-memory FIFO queue buffer (250-sample chunks = 50 ms simulated time)
% - ZERO network calls inside the solver callback (prevents solver stutter and divergence)
% - Sets physical disturbance triggers from memory-managed active disturbance states
% - Handles queue backpressure and tracks dropped chunks

    setup(block);
end

function setup(block)
    block.NumInputPorts  = 2;
    block.NumOutputPorts = 4;

    block.SetPreCompInpPortInfoToDynamic;
    block.SetPreCompOutPortInfoToDynamic;

    % Input 1: Vabc (3 channels, per-unit phase-to-ground)
    block.InputPort(1).Dimensions        = 3;
    block.InputPort(1).DirectFeedthrough = true;

    % Input 2: Iabc (3 channels, per-unit line current)
    block.InputPort(2).Dimensions        = 3;
    block.InputPort(2).DirectFeedthrough = true;

    % Output 1: Sag control trigger (1 = fault active, 0 = normal)
    block.OutputPort(1).Dimensions       = 1;
    % Output 2: Swell control trigger (1 = breaker closed / capacitor connected, 0 = open)
    block.OutputPort(2).Dimensions       = 1;
    % Output 3: Interruption trigger (1 = series breaker closed/normal conduction, 0 = open/interruption)
    block.OutputPort(3).Dimensions       = 1;
    % Output 4: Transient trigger (1 = transient breaker closed/RLC ringing, 0 = open)
    block.OutputPort(4).Dimensions       = 1;

    % Discrete sample time: 5000 Hz (dt = 0.0002 s = 200 us)
    block.SampleTimes = [0.0002 0];

    block.RegBlockMethod('PostPropagationSetup', @DoPostPropSetup);
    block.RegBlockMethod('Start', @Start);
    block.RegBlockMethod('Outputs', @Outputs);
    block.RegBlockMethod('Terminate', @Terminate);
end

function DoPostPropSetup(block)
    block.NumDworks = 7;
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

    % 6: DurationRemaining (samples)
    block.Dwork(6).Name            = 'DurationRemaining';
    block.Dwork(6).Dimensions      = 1;
    block.Dwork(6).DatatypeID      = 0;
    block.Dwork(6).Complexity      = 'Real';
    block.Dwork(6).UsedAsDiscState = true;

    % 7: TrnTrigger
    block.Dwork(7).Name            = 'TrnTrigger';
    block.Dwork(7).Dimensions      = 1;
    block.Dwork(7).DatatypeID      = 0;
    block.Dwork(7).Complexity      = 'Real';
    block.Dwork(7).UsedAsDiscState = true;
end

function Start(block)
    block.Dwork(1).Data = 0;
    block.Dwork(2).Data = 0;
    block.Dwork(3).Data = 0.0; % Sag: 0 = fault open
    block.Dwork(4).Data = 0.0; % Swell: 0 = cap open
    block.Dwork(5).Data = 1.0; % Interruption: 1 = breaker closed (normal conduction)
    block.Dwork(6).Data = 0;
    block.Dwork(7).Data = 0.0; % Transient: 0 = RLC open

    setappdata(0, 'PQD_Live_VBuf', []);
    setappdata(0, 'PQD_Live_IBuf', []);
    setappdata(0, 'PQD_Live_TBuf', []);
    setappdata(0, 'PQD_Live_ChunkQueue', {});
    setappdata(0, 'PQD_Live_DroppedCount', 0);
    setappdata(0, 'PQD_ActiveDisturbance', 'Normal');
    setappdata(0, 'PQD_DistDurationSamples', 0);
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

    %% 1. Update disturbance triggers from controller appdata
    active_dist = getappdata(0, 'PQD_ActiveDisturbance');
    if isempty(active_dist), active_dist = 'Normal'; end

    % Check if a new disturbance injection was commanded
    dist_dur_samps = getappdata(0, 'PQD_DistDurationSamples');
    if ~isempty(dist_dur_samps) && dist_dur_samps > 0
        block.Dwork(6).Data = dist_dur_samps;
        setappdata(0, 'PQD_DistDurationSamples', 0);
    end

    % Apply trigger state:
    % Sag (Fault): 1.0 = fault applied, 0.0 = no fault
    % Swell (Cap Breaker): 1.0 = cap connected, 0.0 = cap disconnected
    % Interruption (Series Breaker): 1.0 = CLOSED (normal conduction), 0.0 = OPEN (interruption)
    % Transient (RLC Breaker): 1.0 = closed / oscillatory ringing, 0.0 = open
    if strcmp(active_dist, 'Sag')
        block.Dwork(3).Data = 1.0;
        block.Dwork(4).Data = 0.0;
        block.Dwork(5).Data = 1.0;
        block.Dwork(7).Data = 0.0;
    elseif strcmp(active_dist, 'Swell')
        block.Dwork(3).Data = 0.0;
        block.Dwork(4).Data = 1.0;
        block.Dwork(5).Data = 1.0;
        block.Dwork(7).Data = 0.0;
    elseif strcmp(active_dist, 'Interruption')
        block.Dwork(3).Data = 0.0;
        block.Dwork(4).Data = 0.0;
        block.Dwork(5).Data = 0.0;
        block.Dwork(7).Data = 0.0;
    elseif strcmp(active_dist, 'Transient')
        block.Dwork(3).Data = 0.0;
        block.Dwork(4).Data = 0.0;
        block.Dwork(5).Data = 1.0;
        block.Dwork(7).Data = 1.0;
    else
        block.Dwork(3).Data = 0.0;
        block.Dwork(4).Data = 0.0;
        block.Dwork(5).Data = 1.0;
        block.Dwork(7).Data = 0.0;
        block.Dwork(6).Data = 0; % Clear any remaining disturbance duration on reset
    end

    % Handle timed duration expiry in exact simulation step count
    if block.Dwork(6).Data > 0
        block.Dwork(6).Data = block.Dwork(6).Data - 1;
        if block.Dwork(6).Data <= 0
            % Duration expired -> auto-revert to normal baseline
            setappdata(0, 'PQD_ActiveDisturbance', 'Normal');
            block.Dwork(3).Data = 0.0;
            block.Dwork(4).Data = 0.0;
            block.Dwork(5).Data = 1.0;
            block.Dwork(7).Data = 0.0;
        end
    end

    %% 2. Output triggers to model physical blocks
    block.OutputPort(1).Data = block.Dwork(3).Data; % Sag (Fault block)
    block.OutputPort(2).Data = block.Dwork(4).Data; % Swell (Cap breaker)
    block.OutputPort(3).Data = block.Dwork(5).Data; % Interruption (Series breaker)
    block.OutputPort(4).Data = block.Dwork(7).Data; % Transient (RLC breaker)

    %% 3. Bounded In-Memory Queue Buffer (250 samples = 50 ms)
    % ZERO network calls are executed inside this solver callback!
    chunk_size = 250;
    if size(v_buf, 1) >= chunk_size
        chunk_seq = block.Dwork(2).Data + 1;
        block.Dwork(2).Data = chunk_seq;

        run_id = getappdata(0, 'PQD_Live_RunId');
        if isempty(run_id), run_id = 'LIVE_RUN_DEFAULT'; end

        % Format chunk adhering to strict API specification
        chunk = struct();
        chunk.run_id                = run_id;
        chunk.sequence              = chunk_seq;
        chunk.sequence_number       = chunk_seq;
        chunk.chunk_index           = chunk_seq;
        chunk.simulation_time_start = t_buf(1);
        chunk.simulation_time_end   = t_buf(end);
        chunk.sampling_rate         = 5000;
        chunk.sampling_rate_hz      = 5000;
        chunk.nominal_frequency_hz  = 60;
        chunk.timestamp_utc         = posixtime(datetime('now', 'TimeZone', 'UTC'));

        % Phase channels (both A, B, C and L1, L2, L3 aliases for full compatibility)
        chunk.voltage = struct( ...
            'A', v_buf(:, 1).', ...
            'B', v_buf(:, 2).', ...
            'C', v_buf(:, 3).', ...
            'L1', v_buf(:, 1).', ...
            'L2', v_buf(:, 2).', ...
            'L3', v_buf(:, 3).' );

        chunk.current = struct( ...
            'A', i_buf(:, 1).', ...
            'B', i_buf(:, 2).', ...
            'C', i_buf(:, 3).', ...
            'L1', i_buf(:, 1).', ...
            'L2', i_buf(:, 2).', ...
            'L3', i_buf(:, 3).' );

        chunk.channels = chunk.voltage;
        chunk.current_channels = chunk.current;

        % Enqueue into bounded in-memory FIFO queue (max 20 chunks = 1 second)
        MAX_QUEUE_LEN = 20;
        queue = getappdata(0, 'PQD_Live_ChunkQueue');
        if isempty(queue), queue = {}; end

        if length(queue) >= MAX_QUEUE_LEN
            % Backpressure: drop oldest chunk to prevent unbounded memory growth
            queue(1) = [];
            dropped = getappdata(0, 'PQD_Live_DroppedCount') + 1;
            setappdata(0, 'PQD_Live_DroppedCount', dropped);
        end

        chunk.dropped_chunks = getappdata(0, 'PQD_Live_DroppedCount');
        queue{end+1} = chunk;
        setappdata(0, 'PQD_Live_ChunkQueue', queue);

        v_buf = [];
        i_buf = [];
        t_buf = [];
    end

    setappdata(0, 'PQD_Live_VBuf', v_buf);
    setappdata(0, 'PQD_Live_IBuf', i_buf);
    setappdata(0, 'PQD_Live_TBuf', t_buf);
end

function Terminate(block)
    if isappdata(0, 'PQD_Live_VBuf'),           rmappdata(0, 'PQD_Live_VBuf'); end
    if isappdata(0, 'PQD_Live_IBuf'),           rmappdata(0, 'PQD_Live_IBuf'); end
    if isappdata(0, 'PQD_Live_TBuf'),           rmappdata(0, 'PQD_Live_TBuf'); end
    if isappdata(0, 'PQD_ActiveDisturbance'),    rmappdata(0, 'PQD_ActiveDisturbance'); end
    if isappdata(0, 'PQD_DistDurationSamples'), rmappdata(0, 'PQD_DistDurationSamples'); end
end
