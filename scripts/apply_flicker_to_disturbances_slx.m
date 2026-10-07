% scripts/apply_flicker_to_disturbances_slx.m
% Permanently adds PQD_Flicker infrastructure to IEEE_9bus_PQD_DISTURBANCES.slx
% Ensures complete dormancy when PQD_Flicker_Enable == 0

cur_dir = fileparts(mfilename('fullpath'));
project_root = fileparts(cur_dir);
addpath(fullfile(project_root, 'IEEE_9bus'));

mdl = 'IEEE_9bus_PQD_DISTURBANCES';
load_system(mdl);

% 1. Add 3 Controlled Current Sources and Grounds for Flicker
phases = {'A', 'B', 'C'};
y_pos = [720, 800, 880];

for idx = 1:3
    p = phases{idx};
    src_blk = [mdl '/PQD_Flicker_' p];
    gnd_blk = [mdl '/PQD_Gnd_Flicker_' p];
    
    if isempty(find_system(mdl, 'SearchDepth', 1, 'Name', ['PQD_Flicker_' p]))
        add_block('spsControlledCurrentSourceLib/Controlled Current Source', src_blk, ...
                  'Initialize', 'off', 'Source_Type', 'AC', ...
                  'Position', [1050, y_pos(idx), 1100, y_pos(idx)+40]);
        add_block('spsGroundLib/Ground', gnd_blk, ...
                  'Position', [1130, y_pos(idx)+10, 1150, y_pos(idx)+30]);
        
        % Connect LConn1 to Bus 5 RConn(idx)
        add_line(mdl, ['Bus_5 230 KV/RConn' num2str(idx)], ['PQD_Flicker_' p '/LConn1'], 'autorouting', 'on');
        % Connect RConn1 to Ground LConn1
        add_line(mdl, ['PQD_Flicker_' p '/RConn1'], ['PQD_Gnd_Flicker_' p '/LConn1'], 'autorouting', 'on');
    end
end

% 2. Add control infrastructure
if isempty(find_system(mdl, 'SearchDepth', 1, 'Name', 'PQD_Flicker_Enable'))
    add_block('built-in/Constant', [mdl '/PQD_Flicker_Enable'], ...
              'Value', '0', 'Position', [870, 780, 900, 800]);
end
if isempty(find_system(mdl, 'SearchDepth', 1, 'Name', 'PQD_Flicker_Zero'))
    add_block('built-in/Constant', [mdl '/PQD_Flicker_Zero'], ...
              'Value', '[0 0 0]', 'Position', [870, 820, 920, 840]);
end
if isempty(find_system(mdl, 'SearchDepth', 1, 'Name', 'PQD_Flicker_FromWS'))
    add_block('built-in/FromWorkspace', [mdl '/PQD_Flicker_FromWS'], ...
              'VariableName', 'flicker_inj_signal', 'Position', [870, 740, 930, 760]);
end
if isempty(find_system(mdl, 'SearchDepth', 1, 'Name', 'PQD_Flicker_Switch'))
    add_block('built-in/Switch', [mdl '/PQD_Flicker_Switch'], ...
              'Criteria', 'u2 > Threshold', 'Threshold', '0.5', ...
              'Position', [950, 770, 980, 810]);
    add_line(mdl, 'PQD_Flicker_FromWS/1', 'PQD_Flicker_Switch/1', 'autorouting', 'on');
    add_line(mdl, 'PQD_Flicker_Enable/1', 'PQD_Flicker_Switch/2', 'autorouting', 'on');
    add_line(mdl, 'PQD_Flicker_Zero/1', 'PQD_Flicker_Switch/3', 'autorouting', 'on');
end
if isempty(find_system(mdl, 'SearchDepth', 1, 'Name', 'PQD_Flicker_Demux'))
    add_block('built-in/Demux', [mdl '/PQD_Flicker_Demux'], ...
              'Outputs', '3', 'Position', [1000, 760, 1005, 900]);
    add_line(mdl, 'PQD_Flicker_Switch/1', 'PQD_Flicker_Demux/1', 'autorouting', 'on');
    add_line(mdl, 'PQD_Flicker_Demux/1', 'PQD_Flicker_A/1', 'autorouting', 'on');
    add_line(mdl, 'PQD_Flicker_Demux/2', 'PQD_Flicker_B/1', 'autorouting', 'on');
    add_line(mdl, 'PQD_Flicker_Demux/3', 'PQD_Flicker_C/1', 'autorouting', 'on');
end

% Set default dormant state: Enable = 0
set_param([mdl '/PQD_Flicker_Enable'], 'Value', '0');

% Save model
save_system(mdl);
close_system(mdl);
disp('Successfully applied PQD_Flicker infrastructure to IEEE_9bus_PQD_DISTURBANCES.slx!');
