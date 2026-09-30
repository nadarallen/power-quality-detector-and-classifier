function audit = deep_model_audit()
% DEEP_MODEL_AUDIT Programmatic reverse-engineering audit of IEEE_9bus_PQD_HIL_R2025a.slx
% Non-destructive: loads the system, inspects blocks and signal paths, outputs JSON.

    model_name = 'IEEE_9bus_PQD_HIL_R2025a';
    cur_dir = fileparts(mfilename('fullpath'));
    project_root = fullfile(cur_dir, '..', '..');
    addpath(fullfile(project_root, 'IEEE_9bus'));
    addpath(cur_dir);

    fprintf('Loading model: %s...\n', model_name);
    load_system(model_name);

    audit = struct();
    audit.model_name = model_name;
    audit.timestamp = char(datetime('now', 'Format', 'yyyy-MM-dd HH:mm:ss'));

    % 1. Model Configuration & Solver
    fprintf('1. Querying Solver and Simulation parameters...\n');
    audit.solver = struct();
    audit.solver.solver_type = get_param(model_name, 'SolverType');
    audit.solver.solver_name = get_param(model_name, 'Solver');
    audit.solver.start_time = get_param(model_name, 'StartTime');
    audit.solver.stop_time = get_param(model_name, 'StopTime');
    audit.solver.max_step = get_param(model_name, 'MaxStep');
    audit.solver.min_step = get_param(model_name, 'MinStep');
    audit.solver.initial_step = get_param(model_name, 'InitialStep');
    audit.solver.fixed_step = get_param(model_name, 'FixedStep');
    audit.solver.rel_tol = get_param(model_name, 'RelTol');
    audit.solver.abs_tol = get_param(model_name, 'AbsTol');
    audit.solver.return_workspace_outputs = get_param(model_name, 'ReturnWorkspaceOutputs');
    audit.solver.output_save_name = get_param(model_name, 'OutputSaveName');

    % Callbacks
    audit.callbacks = struct();
    cb_names = {'PreLoadFcn', 'PostLoadFcn', 'InitFcn', 'StartFcn', 'PauseFcn', 'ContinueFcn', 'StopFcn', 'CloseFcn'};
    for i = 1:length(cb_names)
        cb = cb_names{i};
        audit.callbacks.(cb) = get_param(model_name, cb);
    end

    % 2. powergui Configuration
    fprintf('2. Inspecting powergui block...\n');
    pg_blocks = find_system(model_name, 'BlockType', 'powergui');
    if isempty(pg_blocks)
        pg_blocks = find_system(model_name, 'MaskType', 'PSBoption');
    end
    audit.powergui = struct();
    if ~isempty(pg_blocks)
        pg = pg_blocks{1};
        audit.powergui.block_path = pg;
        audit.powergui.SimulationMode = get_param(pg, 'SimulationMode');
        try audit.powergui.SampleTime = get_param(pg, 'SampleTime'); catch, end
        try audit.powergui.Frequency = get_param(pg, 'frequency'); catch, end
        try audit.powergui.Frq = get_param(pg, 'Frq'); catch, end
        try audit.powergui.PhasorFrequency = get_param(pg, 'PhasorFrequency'); catch, end
    else
        audit.powergui.status = 'NOT FOUND';
    end

    % 3. Model Hierarchy & Top-level subsystems
    fprintf('3. Inspecting top-level hierarchy...\n');
    top_blocks = find_system(model_name, 'SearchDepth', 1);
    top_subsystems = find_system(model_name, 'SearchDepth', 1, 'BlockType', 'SubSystem');
    audit.hierarchy = struct();
    audit.hierarchy.top_blocks_count = length(top_blocks);
    audit.hierarchy.top_subsystems = top_subsystems;

    % 4. Generators
    fprintf('4. Inspecting Generators...\n');
    gen_blocks = [find_system(model_name, 'MaskType', 'Synchronous Machine'); ...
                  find_system(model_name, 'MaskType', 'Three-Phase Source'); ...
                  find_system(model_name, 'BlockType', 'ThreePhaseSource')];
    if isempty(gen_blocks)
        % fallback to search by name/mask
        gen_blocks = find_system(model_name, 'RegExp', 'on', 'Name', '(?i)gen|source|machine');
    end
    audit.generators = {};
    for i = 1:length(gen_blocks)
        g = gen_blocks{i};
        g_info = struct('block_path', g, 'mask_type', get_param(g, 'MaskType'), 'block_type', get_param(g, 'BlockType'));
        params = {'Voltage', 'Frequency', 'PhaseAngle', 'NominalPower', 'BasePower', 'Resistance', 'Inductance', 'Vnom', 'Pnom'};
        for p = params
            try g_info.(p{1}) = get_param(g, p{1}); catch, end
        end
        audit.generators{end+1} = g_info;
    end

    % 5. Transformers
    fprintf('5. Inspecting Transformers...\n');
    xfmr_blocks = find_system(model_name, 'RegExp', 'on', 'MaskType', '(?i)transformer');
    if isempty(xfmr_blocks)
        xfmr_blocks = find_system(model_name, 'RegExp', 'on', 'Name', '(?i)trafo|transformer|tr_');
    end
    audit.transformers = {};
    for i = 1:length(xfmr_blocks)
        x = xfmr_blocks{i};
        x_info = struct('block_path', x, 'mask_type', get_param(x, 'MaskType'));
        params = {'NominalPower', 'Winding1Connection', 'Winding2Connection', 'Winding1', 'Winding2', 'Winding3'};
        for p = params
            try x_info.(p{1}) = get_param(x, p{1}); catch, end
        end
        audit.transformers{end+1} = x_info;
    end

    % 6. Transmission Lines
    fprintf('6. Inspecting Transmission Lines...\n');
    line_blocks = find_system(model_name, 'RegExp', 'on', 'MaskType', '(?i)line|pi section');
    if isempty(line_blocks)
        line_blocks = find_system(model_name, 'RegExp', 'on', 'Name', '(?i)line');
    end
    audit.transmission_lines = {};
    for i = 1:length(line_blocks)
        l = line_blocks{i};
        l_info = struct('block_path', l, 'mask_type', get_param(l, 'MaskType'));
        params = {'Length', 'Frequency', 'Resistances', 'Inductances', 'Capacitances', 'r', 'l', 'c'};
        for p = params
            try l_info.(p{1}) = get_param(l, p{1}); catch, end
        end
        audit.transmission_lines{end+1} = l_info;
    end

    % 7. Loads
    fprintf('7. Inspecting Loads...\n');
    load_blocks = find_system(model_name, 'RegExp', 'on', 'MaskType', '(?i)load');
    if isempty(load_blocks)
        load_blocks = find_system(model_name, 'RegExp', 'on', 'Name', '(?i)load');
    end
    audit.loads = {};
    for i = 1:length(load_blocks)
        ld = load_blocks{i};
        ld_info = struct('block_path', ld, 'mask_type', get_param(ld, 'MaskType'));
        params = {'NominalVoltage', 'NominalFrequency', 'ActivePower', 'InductivePower', 'CapacitivePower', 'P', 'QL', 'QC', 'Vnom', 'fn'};
        for p = params
            try ld_info.(p{1}) = get_param(ld, p{1}); catch, end
        end
        audit.loads{end+1} = ld_info;
    end

    % 8. Bus 5 & All Buses
    fprintf('8. Inspecting Buses and Connections...\n');
    bus_blocks = find_system(model_name, 'RegExp', 'on', 'Type', 'block', 'Name', '(?i)bus');
    audit.buses = {};
    for i = 1:length(bus_blocks)
        b = bus_blocks{i};
        audit.buses{end+1} = struct('block_path', b, 'block_type', get_param(b, 'BlockType'), 'mask_type', get_param(b, 'MaskType'));
    end

    % 9. Measurements
    fprintf('9. Inspecting Measurement Blocks...\n');
    meas_blocks = find_system(model_name, 'RegExp', 'on', 'MaskType', '(?i)measurement');
    audit.measurements = {};
    for i = 1:length(meas_blocks)
        m = meas_blocks{i};
        m_info = struct('block_path', m, 'mask_type', get_param(m, 'MaskType'), 'block_type', get_param(m, 'BlockType'));
        params = {'VoltageMeasurement', 'CurrentMeasurement', 'PhasorSimulation', 'Vbase', 'Ibase'};
        for p = params
            try m_info.(p{1}) = get_param(m, p{1}); catch, end
        end
        audit.measurements{end+1} = m_info;
    end

    % 10. Goto / From blocks (tracing Vabc_5 and Iabc_5)
    fprintf('10. Inspecting Goto/From blocks for Vabc_5 and Iabc_5...\n');
    goto_blocks = find_system(model_name, 'BlockType', 'Goto');
    audit.goto_blocks = {};
    for i = 1:length(goto_blocks)
        gt = goto_blocks{i};
        tag = get_param(gt, 'GotoTag');
        if contains(lower(tag), 'vabc') || contains(lower(tag), 'iabc') || contains(lower(tag), 'bus') || contains(lower(tag), '5')
            audit.goto_blocks{end+1} = struct('block_path', gt, 'tag', tag, 'visibility', get_param(gt, 'TagVisibility'));
        end
    end

    from_blocks = find_system(model_name, 'BlockType', 'From');
    audit.from_blocks = {};
    for i = 1:length(from_blocks)
        fr = from_blocks{i};
        tag = get_param(fr, 'GotoTag');
        if contains(lower(tag), 'vabc') || contains(lower(tag), 'iabc') || contains(lower(tag), 'bus') || contains(lower(tag), '5')
            audit.from_blocks{end+1} = struct('block_path', fr, 'tag', tag);
        end
    end

    % 11. To Workspace blocks & Logging variables
    fprintf('11. Inspecting To Workspace blocks & Logging variables...\n');
    to_ws_blocks = find_system(model_name, 'BlockType', 'ToWorkspace');
    audit.to_workspace = {};
    for i = 1:length(to_ws_blocks)
        tw = to_ws_blocks{i};
        audit.to_workspace{end+1} = struct(...
            'block_path', tw, ...
            'variable_name', get_param(tw, 'VariableName'), ...
            'save_format', get_param(tw, 'SaveFormat'), ...
            'max_data_points', get_param(tw, 'MaxDataPoints'), ...
            'decimation', get_param(tw, 'Decimation'), ...
            'sample_time', get_param(tw, 'SampleTime') ...
        );
    end

    % 12. Detailed Trace of Bus 5 -> Vabc_5 & Iabc_5
    fprintf('12. Tracing exact signal routing for Bus 5, Vabc_5, and Iabc_5...\n');
    audit.bus5_trace = struct();
    bus5_candidates = find_system(model_name, 'RegExp', 'on', 'Type', 'block', 'Name', '(?i)bus\s*5|b5');
    audit.bus5_trace.bus5_blocks = bus5_candidates;

    % Trace To Workspace blocks
    audit.trace_to_workspace = {};
    for i = 1:length(to_ws_blocks)
        tw = to_ws_blocks{i};
        var_name = get_param(tw, 'VariableName');
        curr_blk = tw;
        chain = {curr_blk};
        for depth = 1:10
            lh = get_param(curr_blk, 'LineHandles');
            if isempty(lh.Inport) || lh.Inport(1) == -1, break; end
            src_p = get_param(lh.Inport(1), 'SrcPortHandle');
            if isempty(src_p) || src_p == -1, break; end
            src_b = get_param(src_p, 'Parent');
            chain{end+1} = sprintf('%s (Port %d)', src_b, get_param(src_p, 'PortNumber'));
            if strcmp(get_param(src_b, 'BlockType'), 'From')
                from_tag = get_param(src_b, 'GotoTag');
                chain{end+1} = sprintf('[From Tag: %s]', from_tag);
                % find matching Goto
                gotos = find_system(model_name, 'BlockType', 'Goto', 'GotoTag', from_tag);
                if ~isempty(gotos)
                    chain{end+1} = sprintf('[Matching Goto: %s]', gotos{1});
                    curr_blk = gotos{1};
                    continue;
                end
            end
            curr_blk = src_b;
        end
        audit.trace_to_workspace{end+1} = struct('block', tw, 'var_name', var_name, 'chain', {chain});
    end

    % Trace Vabc_5 Goto / From tags specifically
    audit.vabc_5_trace = struct();
    v5_gotos = find_system(model_name, 'BlockType', 'Goto', 'GotoTag', 'Vabc_5');
    audit.vabc_5_trace.gotos = v5_gotos;
    v5_froms = find_system(model_name, 'BlockType', 'From', 'GotoTag', 'Vabc_5');
    audit.vabc_5_trace.froms = v5_froms;

    audit.iabc_5_trace = struct();
    i5_gotos = find_system(model_name, 'BlockType', 'Goto', 'GotoTag', 'Iabc_5');
    audit.iabc_5_trace.gotos = i5_gotos;
    i5_froms = find_system(model_name, 'BlockType', 'From', 'GotoTag', 'Iabc_5');
    audit.iabc_5_trace.froms = i5_froms;

    % Subsystem inspection
    subsystems = find_system(model_name, 'BlockType', 'SubSystem');
    audit.subsystems = {};
    for i = 1:length(subsystems)
        s = subsystems{i};
        audit.subsystems{end+1} = struct('name', s, 'blocks_count', length(find_system(s, 'SearchDepth', 1)));
    end

    % Save machine-readable JSON
    json_path = fullfile(project_root, 'docs', 'IEEE9BUS_MODEL_AUDIT.json');
    fid = fopen(json_path, 'w');
    if fid ~= -1
        fwrite(fid, jsonencode(audit, 'PrettyPrint', true));
        fclose(fid);
        fprintf('Saved audit JSON to: %s\n', json_path);
    end

    fprintf('\n========================================================\n');
    fprintf('  MODEL AUDIT PROGRAMMATIC EXTRACTION COMPLETED\n');
    fprintf('========================================================\n\n');
end
