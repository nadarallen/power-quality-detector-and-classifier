% scripts/apply_harmonics_to_disturbances_slx.m
% Permanently adds PQD_Harmonics subsystem to IEEE_9bus_PQD_DISTURBANCES.slx
% Ensures complete dormancy when PQD_Harm_Enable == 0

cur_dir = fileparts(mfilename('fullpath'));
project_root = fileparts(cur_dir);
addpath(fullfile(project_root, 'IEEE_9bus'));

mdl = 'IEEE_9bus_PQD_DISTURBANCES';
load_system(mdl);

% 1. Add 3 Controlled Current Sources and Grounds if not already present
phases = {'A', 'B', 'C'};
y_pos = [480, 560, 640];

for idx = 1:3
    p = phases{idx};
    src_blk = [mdl '/PQD_Harmonics_' p];
    gnd_blk = [mdl '/PQD_Gnd_Harm_' p];
    
    if isempty(find_system(mdl, 'SearchDepth', 1, 'Name', ['PQD_Harmonics_' p]))
        add_block('spsControlledCurrentSourceLib/Controlled Current Source', src_blk, ...
                  'Initialize', 'off', 'Source_Type', 'AC', ...
                  'Position', [1050, y_pos(idx), 1100, y_pos(idx)+40]);
        add_block('spsGroundLib/Ground', gnd_blk, ...
                  'Position', [1130, y_pos(idx)+10, 1150, y_pos(idx)+30]);
        
        % Connect LConn1 to Bus 5 RConn(idx)
        add_line(mdl, ['Bus_5 230 KV/RConn' num2str(idx)], ['PQD_Harmonics_' p '/LConn1'], 'autorouting', 'on');
        % Connect RConn1 to Ground LConn1
        add_line(mdl, ['PQD_Harmonics_' p '/RConn1'], ['PQD_Gnd_Harm_' p '/LConn1'], 'autorouting', 'on');
    end
end

% 2. Add control infrastructure
if isempty(find_system(mdl, 'SearchDepth', 1, 'Name', 'PQD_Harm_Enable'))
    add_block('built-in/Constant', [mdl '/PQD_Harm_Enable'], ...
              'Value', '0', 'Position', [870, 540, 900, 560]);
end
if isempty(find_system(mdl, 'SearchDepth', 1, 'Name', 'PQD_Harm_Zero'))
    add_block('built-in/Constant', [mdl '/PQD_Harm_Zero'], ...
              'Value', '[0 0 0]', 'Position', [870, 580, 920, 600]);
end
if isempty(find_system(mdl, 'SearchDepth', 1, 'Name', 'PQD_Harm_FromWS'))
    add_block('built-in/FromWorkspace', [mdl '/PQD_Harm_FromWS'], ...
              'VariableName', 'harm_inj_signal', 'Position', [870, 500, 930, 520]);
end
if isempty(find_system(mdl, 'SearchDepth', 1, 'Name', 'PQD_Harm_Switch'))
    add_block('built-in/Switch', [mdl '/PQD_Harm_Switch'], ...
              'Criteria', 'u2 > Threshold', 'Threshold', '0.5', ...
              'Position', [950, 530, 980, 570]);
    add_line(mdl, 'PQD_Harm_FromWS/1', 'PQD_Harm_Switch/1', 'autorouting', 'on');
    add_line(mdl, 'PQD_Harm_Enable/1', 'PQD_Harm_Switch/2', 'autorouting', 'on');
    add_line(mdl, 'PQD_Harm_Zero/1', 'PQD_Harm_Switch/3', 'autorouting', 'on');
end
if isempty(find_system(mdl, 'SearchDepth', 1, 'Name', 'PQD_Harm_Demux'))
    add_block('built-in/Demux', [mdl '/PQD_Harm_Demux'], ...
              'Outputs', '3', 'Position', [1000, 520, 1005, 660]);
    add_line(mdl, 'PQD_Harm_Switch/1', 'PQD_Harm_Demux/1', 'autorouting', 'on');
    add_line(mdl, 'PQD_Harm_Demux/1', 'PQD_Harmonics_A/1', 'autorouting', 'on');
    add_line(mdl, 'PQD_Harm_Demux/2', 'PQD_Harmonics_B/1', 'autorouting', 'on');
    add_line(mdl, 'PQD_Harm_Demux/3', 'PQD_Harmonics_C/1', 'autorouting', 'on');
end

% Set default dormant state: Enable = 0
set_param([mdl '/PQD_Harm_Enable'], 'Value', '0');

% Save model
save_system(mdl);
close_system(mdl);
disp('Successfully applied PQD_Harmonics infrastructure to IEEE_9bus_PQD_DISTURBANCES.slx!');
