% scripts/test_interruption_breaker_wiring.m
% Test wiring and simulation of PQD_Breaker_Interruption

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

% Add PQD_Breaker_Interruption
brk_name = [test_mdl '/PQD_Breaker_Interruption'];
if isempty(find_system(test_mdl, 'SearchDepth', 1, 'Name', 'PQD_Breaker_Interruption'))
    add_block('spsThreePhaseBreakerLib/Three-Phase Breaker', brk_name, ...
              'Position', [810, 680, 860, 740]);
end

% Set breaker parameters:
% Opens at t = 0.12 s, recloses at t = 0.19 s (duration = 70 ms = 4.2 cycles)
% Initial state = closed (1)
set_param(brk_name, 'InitialState', '1'); % closed initially
set_param(brk_name, 'SwitchA', 'on', 'SwitchB', 'on', 'SwitchC', 'on');
set_param(brk_name, 'SwitchTimes', '[0.12 0.19]');
set_param(brk_name, 'BreakerResistance', '0.001');
set_param(brk_name, 'SnubberResistance', '1e6');
set_param(brk_name, 'SnubberCapacitance', 'inf'); % pure resistive snubber

disp('Breaker configured. Testing connections and simulation...');
