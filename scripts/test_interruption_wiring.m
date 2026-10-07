% scripts/test_interruption_wiring.m
% Complete test of wiring PQD_Breaker_Interruption and running simulation

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

% Inspect lines connected to Bus_5 230 KV
b5 = [test_mdl '/Bus_5 230 KV'];
disp('Bus 5 port connectivity:');
pc = get_param(b5, 'PortConnectivity');
for i = 1:length(pc)
    disp(['Port ' num2str(i) ' (' pc(i).Type ') Position=' mat2str(pc(i).Position)]);
end

close_system(test_mdl, 0);
delete(fullfile(project_root, 'IEEE_9bus', [test_mdl '.slx']));
