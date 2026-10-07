% scripts/test_breaker_placement.m
% Test breaker placement effects on Bus 5 voltage

cur_dir = fileparts(mfilename('fullpath'));
project_root = fileparts(cur_dir);
addpath(fullfile(project_root, 'IEEE_9bus'));

mdl = 'IEEE_9bus_PQD_DISTURBANCES';
load_system(mdl);

% Ensure Sag and Swell are disabled
set_param([mdl '/PQD_Fault_Sag'], 'FaultA', 'off', 'FaultB', 'off', 'FaultC', 'off', ...
    'GroundFault', 'off', 'SwitchTimes', '[999 1000]');
set_param([mdl '/PQD_Breaker_Swell'], 'InitialState', 'open', 'SwitchTimes', '[999 1000]', ...
    'SwitchA', 'off', 'SwitchB', 'off', 'SwitchC', 'off');

% Run baseline
simOut = sim(mdl, 'StopTime', '0.25');
Vts = simOut.PQD_Vabc;
[Vres, tres] = resample(Vts.Data, Vts.Time, 5000);
rms_base = sqrt(mean(Vres(500:750, 1).^2));
fprintf('Baseline Phase A RMS: %.4f pu\n', rms_base);
