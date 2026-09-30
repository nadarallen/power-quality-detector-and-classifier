% scripts/run_disturbance_simulation.m
% Executes a single disturbance scenario on IEEE_9bus_PQD_DISTURBANCES.slx
% Usage: matlab -batch "run_disturbance_simulation('scenarios/definitions/SAG_0001_three_phase_symmetric.json', 'data/ieee9bus_60hz/sag/raw_sim_sag_0001.mat')"

function run_disturbance_simulation(scenario_json_path, output_mat_path)
    if nargin < 1
        scenario_json_path = 'scenarios/definitions/SAG_0001_three_phase_symmetric.json';
    end
    if nargin < 2
        output_mat_path = 'data/ieee9bus_60hz/sag/raw_sim_sag_0001.mat';
    end

    cur_dir = fileparts(mfilename('fullpath'));
    project_root = fileparts(cur_dir);
    addpath(fullfile(project_root, 'IEEE_9bus'));

    % Ensure output directory exists
    out_dir = fileparts(output_mat_path);
    if ~exist(out_dir, 'dir')
        mkdir(out_dir);
    end

    fprintf('[SimRunner] Reading scenario: %s\n', scenario_json_path);
    raw_text = fileread(scenario_json_path);
    scen = jsondecode(raw_text);

    mdl = 'IEEE_9bus_PQD_DISTURBANCES';
    load_system(mdl);
    set_param(mdl, 'StopFcn', '');
    set_param(mdl, 'Solver', 'ode23tb');
    set_param(mdl, 'RelTol', '1e-4');

    % Set base loads / generator operating point if specified
    cond_id = 1;
    if isfield(scen, 'operating_condition_id')
        cond_id = scen.operating_condition_id;
    end
    fprintf('[SimRunner] Operating condition ID: %d\n', cond_id);

    % Configure Fault Block
    fault_blk = [mdl '/PQD_Fault_Sag'];
    if isempty(find_system(mdl, 'SearchDepth', 1, 'Name', 'PQD_Fault_Sag'))
        error('Fault block %s does not exist in working model!', fault_blk);
    end

    % Determine timing
    % Nominal simulation stop time: 0.38 s
    % Let fault start at t = 0.12 s
    t_fault_start = 0.12;
    duration_s = scen.parameters.duration_ms / 1000.0;
    t_fault_end = t_fault_start + duration_s;

    % Phase configuration
    ph_str = scen.injection_location.phase;
    fault_a = 'off'; fault_b = 'off'; fault_c = 'off';
    if contains(ph_str, 'A'), fault_a = 'on'; end
    if contains(ph_str, 'B'), fault_b = 'on'; end
    if contains(ph_str, 'C'), fault_c = 'on'; end

    set_param(fault_blk, 'FaultA', fault_a);
    set_param(fault_blk, 'FaultB', fault_b);
    set_param(fault_blk, 'FaultC', fault_c);
    set_param(fault_blk, 'GroundFault', 'on');
    set_param(fault_blk, 'SwitchTimes', sprintf('[%.6f %.6f]', t_fault_start, t_fault_end));
    set_param(fault_blk, 'FaultResistance', num2str(scen.parameters.fault_resistance_ohms));
    set_param(fault_blk, 'GroundResistance', num2str(scen.parameters.ground_resistance_ohms));

    fprintf('[SimRunner] Fault Config: Phase=%s, Rf=%.1f ohm, t=[%.4f, %.4f] s\n', ...
        ph_str, scen.parameters.fault_resistance_ohms, t_fault_start, t_fault_end);

    t_start = tic;
    simOut = sim(mdl, 'StopTime', '0.38');
    t_wall = toc(t_start);
    fprintf('[SimRunner] Simulation completed in %.2f s\n', t_wall);

    % Resample to 5000 Hz
    Vts = simOut.PQD_Vabc;
    [Vres, tres] = resample(Vts.Data, Vts.Time, 5000);

    Ires = [];
    if isprop(simOut, 'PQD_Iabc') || isfield(simOut, 'PQD_Iabc')
        Its = simOut.PQD_Iabc;
        [Ires, ~] = resample(Its.Data, Its.Time, 5000);
    else
        Ires = zeros(size(Vres));
    end

    % Slice 200 ms (1000 samples) window
    onset_s = scen.parameters.onset_time_ms / 1000.0;
    t_frame_start = t_fault_start - onset_s;
    t_frame_end = t_frame_start + 0.200;

    frame_mask = (tres >= (t_frame_start - 1e-6) & tres < (t_frame_end - 1e-6));
    V_frame = Vres(frame_mask, :);
    I_frame = Ires(frame_mask, :);
    t_frame = tres(frame_mask) - t_frame_start; % 0 to 0.200 s

    % Trim to exactly 1000 samples if rounding produced 1001
    if size(V_frame, 1) > 1000
        V_frame = V_frame(1:1000, :);
        I_frame = I_frame(1:1000, :);
        t_frame = t_frame(1:1000);
    elseif size(V_frame, 1) < 1000
        error('Frame sample count %d < 1000', size(V_frame, 1));
    end

    fprintf('[SimRunner] Extracted frame: %d samples, t=[0, %.3f] s\n', ...
        size(V_frame, 1), t_frame(end));

    % Save results
    save(output_mat_path, 'V_frame', 'I_frame', 't_frame', 'scen', 't_wall', ...
         't_fault_start', 't_fault_end', 't_frame_start', 't_frame_end', '-v7');
    fprintf('[SimRunner] Successfully saved to %s\n', output_mat_path);

    close_system(mdl, 0);
end
