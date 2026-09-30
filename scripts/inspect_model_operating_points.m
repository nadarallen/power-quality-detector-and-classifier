% scripts/inspect_model_operating_points.m
% Programmatic inspection of controllable parameters in IEEE_9bus_PQD_HIL_R2025a.slx

cur_dir = fileparts(mfilename('fullpath'));
project_root = fileparts(cur_dir);
model = 'IEEE_9bus_PQD_HIL_R2025a';
model_path = fullfile(project_root, 'IEEE_9bus', model);

fprintf('Loading model from: %s\n', model_path);
load_system(model_path);

blks = find_system(model, 'SearchDepth', 1);
results = struct();

for i = 2:length(blks)
    b = blks{i};
    bname = strrep(get_param(b, 'Name'), char(10), ' ');
    btype = get_param(b, 'BlockType');
    mtype = '';
    try
        mtype = get_param(b, 'MaskType');
    catch
    end
    
    entry = struct();
    entry.FullName = b;
    entry.Name = bname;
    entry.BlockType = btype;
    entry.MaskType = mtype;
    
    % Get all dialog parameters
    try
        dp = get_param(b, 'DialogParameters');
        f = fieldnames(dp);
        pstruct = struct();
        for k = 1:length(f)
            pname = f{k};
            pval = get_param(b, pname);
            if ischar(pval)
                pstruct.(pname) = pval;
            end
        end
        entry.Params = pstruct;
    catch
        entry.Params = struct();
    end
    
    safe_field = matlab.lang.makeValidName(bname);
    results.(safe_field) = entry;
end

json_str = jsonencode(results, 'PrettyPrint', true);
out_json = fullfile(project_root, 'data', 'ieee9bus_blocks_info.json');
fid = fopen(out_json, 'w');
fwrite(fid, json_str);
fclose(fid);
fprintf('[Success] Saved block parameters to: %s\n', out_json);
exit(0);
