% scripts/apply_notch_to_disturbances_slx.m
% Permanently adds PQD_Notch infrastructure to IEEE_9bus_PQD_DISTURBANCES.slx
% Implements physical commutation switching at Bus 5 per Gate 3C Section 4.7
% Ensures complete dormancy when PQD_Notch_Enable == 0

cur_dir = fileparts(mfilename('fullpath'));
project_root = fileparts(cur_dir);
addpath(fullfile(project_root, 'IEEE_9bus'));

mdl = 'IEEE_9bus_PQD_DISTURBANCES';
load_system(mdl);

notch_blk = [mdl '/PQD_Notch_Bus5'];

% 1. Ensure PQD_Notch_Bus5 exists and is connected to Bus 5
if isempty(find_system(mdl, 'SearchDepth', 1, 'Name', 'PQD_Notch_Bus5'))
    add_block('spsThreePhaseFaultLib/Three-Phase Fault', notch_blk, ...
              'Position', [1050, 960, 1100, 1010]);
    add_line(mdl, 'Bus_5 230 KV/RConn1', 'PQD_Notch_Bus5/LConn1', 'autorouting', 'on');
    add_line(mdl, 'Bus_5 230 KV/RConn2', 'PQD_Notch_Bus5/LConn2', 'autorouting', 'on');
    add_line(mdl, 'Bus_5 230 KV/RConn3', 'PQD_Notch_Bus5/LConn3', 'autorouting', 'on');
    disp('Added PQD_Notch_Bus5 and connected to Bus 5.');
else
    disp('PQD_Notch_Bus5 already exists.');
end

% Set External control on
set_param(notch_blk, 'External', 'on');
set_param(notch_blk, 'FaultA', 'off');
set_param(notch_blk, 'FaultB', 'off');
set_param(notch_blk, 'FaultC', 'off');
set_param(notch_blk, 'GroundFault', 'off');
set_param(notch_blk, 'FaultResistance', '80.0');
set_param(notch_blk, 'GroundResistance', '0.01');
set_param(notch_blk, 'SnubberResistance', '1e6');
set_param(notch_blk, 'SnubberCapacitance', 'inf');

% 2. Add Control Infrastructure
if isempty(find_system(mdl, 'SearchDepth', 1, 'Name', 'PQD_Notch_Enable'))
    add_block('built-in/Constant', [mdl '/PQD_Notch_Enable'], ...
              'Value', '0', 'Position', [870, 960, 900, 980]);
end
if isempty(find_system(mdl, 'SearchDepth', 1, 'Name', 'PQD_Notch_Zero'))
    add_block('built-in/Constant', [mdl '/PQD_Notch_Zero'], ...
              'Value', '0', 'Position', [870, 1000, 900, 1020]);
end
if isempty(find_system(mdl, 'SearchDepth', 1, 'Name', 'PQD_Notch_FromWS'))
    add_block('built-in/FromWorkspace', [mdl '/PQD_Notch_FromWS'], ...
              'VariableName', 'notch_ctrl_signal', 'Position', [870, 920, 930, 940]);
end
if isempty(find_system(mdl, 'SearchDepth', 1, 'Name', 'PQD_Notch_Switch'))
    add_block('built-in/Switch', [mdl '/PQD_Notch_Switch'], ...
              'Criteria', 'u2 > Threshold', 'Threshold', '0.5', ...
              'Position', [950, 950, 980, 990]);
    add_line(mdl, 'PQD_Notch_FromWS/1', 'PQD_Notch_Switch/1', 'autorouting', 'on');
    add_line(mdl, 'PQD_Notch_Enable/1', 'PQD_Notch_Switch/2', 'autorouting', 'on');
    add_line(mdl, 'PQD_Notch_Zero/1', 'PQD_Notch_Switch/3', 'autorouting', 'on');
end

% Connect Switch output to PQD_Notch_Bus5 Inport 1
h_sw = get_param([mdl '/PQD_Notch_Switch'], 'PortHandles');
h_notch = get_param(notch_blk, 'PortHandles');
line_existing = get_param(h_notch.Inport, 'Line');
if line_existing == -1
    add_line(mdl, 'PQD_Notch_Switch/1', 'PQD_Notch_Bus5/1', 'autorouting', 'on');
    disp('Connected PQD_Notch_Switch output to PQD_Notch_Bus5 Inport 1.');
end

% Set default dormant state: Enable = 0
set_param([mdl '/PQD_Notch_Enable'], 'Value', '0');

save_system(mdl);
close_system(mdl);
disp('Successfully configured complete PQD_Notch infrastructure in IEEE_9bus_PQD_DISTURBANCES.slx!');
