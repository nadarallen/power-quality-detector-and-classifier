% scripts/apply_interruption_to_disturbances_slx.m
% Applies PQD_Breaker_Interruption to IEEE_9bus_PQD_DISTURBANCES.slx permanently

cur_dir = fileparts(mfilename('fullpath'));
project_root = fileparts(cur_dir);
addpath(fullfile(project_root, 'IEEE_9bus'));

mdl = 'IEEE_9bus_PQD_DISTURBANCES';
load_system(mdl);

% Add PQD_Breaker_Interruption if not present
brk_name = [mdl '/PQD_Breaker_Interruption'];
if isempty(find_system(mdl, 'SearchDepth', 1, 'Name', 'PQD_Breaker_Interruption'))
    add_block('spsThreePhaseBreakerLib/Three-Phase Breaker', brk_name, ...
              'Position', [870, 480, 910, 550]);
end

% Set default dormant state (closed, ready for normal, sag, swell)
set_param(brk_name, 'InitialState', 'closed');
set_param(brk_name, 'SwitchA', 'off', 'SwitchB', 'off', 'SwitchC', 'off');
set_param(brk_name, 'SwitchTimes', '[999 1000]');
set_param(brk_name, 'BreakerResistance', '0.001');
set_param(brk_name, 'SnubberResistance', '1e6');
set_param(brk_name, 'SnubberCapacitance', 'inf');

b5 = [mdl '/Bus_5 230 KV'];
ph_b5 = get_param(b5, 'PortHandles');
load_blk = find_system(mdl, 'SearchDepth', 1, 'RegExp', 'on', 'Name', '125 MW.*');
load_name = get_param(load_blk{1}, 'Name');
ph_load = get_param(load_blk{1}, 'PortHandles');

for i = 1:3
    lh = get_param(ph_b5.LConn(i), 'Line');
    if lh > 0, delete_line(lh); end
    lh = get_param(ph_b5.RConn(i), 'Line');
    if lh > 0, delete_line(lh); end
    lh = get_param(ph_load.LConn(i), 'Line');
    if lh > 0, delete_line(lh); end
end

add_line(mdl, 'Line 4 - 5 /LConn1', 'Line 5 - 7 /RConn1', 'autorouting', 'on');
add_line(mdl, 'Line 4 - 5 /LConn2', 'Line 5 - 7 /RConn2', 'autorouting', 'on');
add_line(mdl, 'Line 4 - 5 /LConn3', 'Line 5 - 7 /RConn3', 'autorouting', 'on');

add_line(mdl, 'Line 5 - 7 /RConn1', 'PQD_Breaker_Interruption/LConn1', 'autorouting', 'on');
add_line(mdl, 'Line 5 - 7 /RConn2', 'PQD_Breaker_Interruption/LConn2', 'autorouting', 'on');
add_line(mdl, 'Line 5 - 7 /RConn3', 'PQD_Breaker_Interruption/LConn3', 'autorouting', 'on');

add_line(mdl, 'PQD_Breaker_Interruption/RConn1', 'Bus_5 230 KV/LConn1', 'autorouting', 'on');
add_line(mdl, 'PQD_Breaker_Interruption/RConn2', 'Bus_5 230 KV/LConn2', 'autorouting', 'on');
add_line(mdl, 'PQD_Breaker_Interruption/RConn3', 'Bus_5 230 KV/LConn3', 'autorouting', 'on');

add_line(mdl, 'Bus_5 230 KV/RConn1', [load_name '/LConn1'], 'autorouting', 'on');
add_line(mdl, 'Bus_5 230 KV/RConn2', [load_name '/LConn2'], 'autorouting', 'on');
add_line(mdl, 'Bus_5 230 KV/RConn3', [load_name '/LConn3'], 'autorouting', 'on');

% Save model
save_system(mdl);
close_system(mdl);
disp('Successfully applied PQD_Breaker_Interruption and saved IEEE_9bus_PQD_DISTURBANCES.slx!');
