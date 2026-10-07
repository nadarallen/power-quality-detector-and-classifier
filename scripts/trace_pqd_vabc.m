% scripts/trace_pqd_vabc.m
cur_dir = fileparts(mfilename('fullpath'));
project_root = fileparts(cur_dir);
addpath(fullfile(project_root, 'IEEE_9bus'));
load_system('IEEE_9bus_PQD_DISTURBANCES');

% Find To Workspace blocks
tw = find_system('IEEE_9bus_PQD_DISTURBANCES', 'BlockType', 'ToWorkspace');
for i = 1:length(tw)
    var = get_param(tw{i}, 'VariableName');
    disp(['ToWorkspace: ' tw{i} ' -> ' var]);
    ph = get_param(tw{i}, 'PortHandles');
    line_h = get_param(ph.Inport(1), 'Line');
    if line_h > 0
        src_port = get_param(line_h, 'SrcPortHandle');
        src_blk = get_param(src_port, 'Parent');
        disp(['  Fed from: ' src_blk ' (Type: ' get_param(src_blk, 'BlockType') ')']);
        if strcmp(get_param(src_blk, 'BlockType'), 'From')
            disp(['    GotoTag: ' get_param(src_blk, 'GotoTag')]);
        end
    end
end
