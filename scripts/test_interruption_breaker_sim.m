% scripts/test_interruption_breaker_sim.m
% Tests the implementation and electrical behavior of PQD_Breaker_Interruption

cur_dir = fileparts(mfilename('fullpath'));
project_root = fileparts(cur_dir);
addpath(fullfile(project_root, 'IEEE_9bus'));

mdl = 'IEEE_9bus_PQD_DISTURBANCES';
load_system(mdl);

% Ensure Sag and Swell are disabled
if ~isempty(find_system(mdl, 'SearchDepth', 1, 'Name', 'PQD_Fault_Sag'))
    set_param([mdl '/PQD_Fault_Sag'], 'FaultA', 'off', 'FaultB', 'off', 'FaultC', 'off', ...
        'GroundFault', 'off', 'SwitchTimes', '[999 1000]');
end
if ~isempty(find_system(mdl, 'SearchDepth', 1, 'Name', 'PQD_Breaker_Swell'))
    set_param([mdl '/PQD_Breaker_Swell'], 'InitialState', 'open', 'SwitchTimes', '[999 1000]', ...
        'SwitchA', 'off', 'SwitchB', 'off', 'SwitchC', 'off');
end

disp('Starting test simulation script...');
