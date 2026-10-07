% scripts/test_open_breaker.m
cur_dir = fileparts(mfilename('fullpath'));
project_root = fileparts(cur_dir);
addpath(fullfile(project_root, 'IEEE_9bus'));

src_mdl = 'IEEE_9bus_PQD_DISTURBANCES';
test_mdl = 'IEEE_9bus_PQD_DISTURBANCES_TEST';

copyfile(fullfile(project_root, 'IEEE_9bus', [src_mdl '.slx']), ...
         fullfile(project_root, 'IEEE_9bus', [test_mdl '.slx']));
load_system(test_mdl);

% Disable Sag and Swell
set_param([test_mdl '/PQD_Fault_Sag'], 'FaultA', 'off', 'FaultB', 'off', 'FaultC', 'off', ...
    'GroundFault', 'off', 'SwitchTimes', '[999 1000]');
set_param([test_mdl '/PQD_Breaker_Swell'], 'InitialState', 'open', 'SwitchTimes', '[999 1000]', ...
    'SwitchA', 'off', 'SwitchB', 'off', 'SwitchC', 'off');

% Add PQD_Breaker_Interruption but keep it OPEN the ENTIRE time
brk_name = [test_mdl '/PQD_Breaker_Interruption'];
add_block('spsThreePhaseBreakerLib/Three-Phase Breaker', brk_name, ...
          'Position', [870, 480, 910, 550]);

set_param(brk_name, 'InitialState', 'open'); % OPEN ENTIRE TIME
set_param(brk_name, 'SwitchA', 'on', 'SwitchB', 'on', 'SwitchC', 'on');
set_param(brk_name, 'SwitchTimes', '[999 1000]');
set_param(brk_name, 'BreakerResistance', '0.001');
set_param(brk_name, 'SnubberResistance', '1e6');
set_param(brk_name, 'SnubberCapacitance', 'inf');

b5 = [test_mdl '/Bus_5 230 KV'];
ph_b5 = get_param(b5, 'PortHandles');

for i = 1:3
    lh = get_param(ph_b5.LConn(i), 'Line');
    if lh > 0, delete_line(lh); end
    lh = get_param(ph_b5.RConn(i), 'Line');
    if lh > 0, delete_line(lh); end
end

add_line(test_mdl, 'Line 4 - 5 /LConn1', 'Line 5 - 7 /RConn1', 'autorouting', 'on');
add_line(test_mdl, 'Line 4 - 5 /LConn2', 'Line 5 - 7 /RConn2', 'autorouting', 'on');
add_line(test_mdl, 'Line 4 - 5 /LConn3', 'Line 5 - 7 /RConn3', 'autorouting', 'on');

add_line(test_mdl, 'Line 5 - 7 /RConn1', 'PQD_Breaker_Interruption/LConn1', 'autorouting', 'on');
add_line(test_mdl, 'Line 5 - 7 /RConn2', 'PQD_Breaker_Interruption/LConn2', 'autorouting', 'on');
add_line(test_mdl, 'Line 5 - 7 /RConn3', 'PQD_Breaker_Interruption/LConn3', 'autorouting', 'on');

add_line(test_mdl, 'PQD_Breaker_Interruption/RConn1', 'Bus_5 230 KV/LConn1', 'autorouting', 'on');
add_line(test_mdl, 'PQD_Breaker_Interruption/RConn2', 'Bus_5 230 KV/LConn2', 'autorouting', 'on');
add_line(test_mdl, 'PQD_Breaker_Interruption/RConn3', 'Bus_5 230 KV/LConn3', 'autorouting', 'on');

load_blk = find_system(test_mdl, 'SearchDepth', 1, 'RegExp', 'on', 'Name', '125 MW.*');
load_name = get_param(load_blk{1}, 'Name');
add_line(test_mdl, 'Bus_5 230 KV/RConn1', [load_name '/LConn1'], 'autorouting', 'on');
add_line(test_mdl, 'Bus_5 230 KV/RConn2', [load_name '/LConn2'], 'autorouting', 'on');
add_line(test_mdl, 'Bus_5 230 KV/RConn3', [load_name '/LConn3'], 'autorouting', 'on');

simOut = sim(test_mdl, 'StopTime', '0.20');
Vts = simOut.PQD_Vabc;
[Vres, tres] = resample(Vts.Data, Vts.Time, 5000);

v_rms = sqrt(mean(Vres(500:1000, :).^2, 1));
fprintf('With breaker OPEN: Vrms = [%.6f, %.6f, %.6f] pu\n', v_rms(1), v_rms(2), v_rms(3));

close_system(test_mdl, 0);
delete(fullfile(project_root, 'IEEE_9bus', [test_mdl '.slx']));
