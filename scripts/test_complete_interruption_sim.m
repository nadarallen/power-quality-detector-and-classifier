% scripts/test_complete_interruption_sim.m
% Complete test of wiring and simulating PQD_Breaker_Interruption

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

% Inspect PortHandles of Line 5 - 7, Line 4 - 5, Bus_5 230 KV, Load
b5 = [test_mdl '/Bus_5 230 KV'];
ph_b5 = get_param(b5, 'PortHandles');
ph_l57 = get_param([test_mdl '/Line 5 - 7 '], 'PortHandles');
ph_l45 = get_param([test_mdl '/Line 4 - 5 '], 'PortHandles');

% Print info
disp('LConn of Line 5-7:');
disp(ph_l57.RConn);
disp('RConn of Line 4-5:');
disp(ph_l45.LConn);
disp('Bus 5 LConn:');
disp(ph_b5.LConn);
disp('Bus 5 RConn:');
disp(ph_b5.RConn);

close_system(test_mdl, 0);
delete(fullfile(project_root, 'IEEE_9bus', [test_mdl '.slx']));
