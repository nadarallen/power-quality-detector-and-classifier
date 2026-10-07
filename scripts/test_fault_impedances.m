% scripts/test_fault_impedances.m
cur_dir = fileparts(mfilename('fullpath'));
project_root = fileparts(cur_dir);
addpath(fullfile(project_root, 'IEEE_9bus'));

mdl = 'IEEE_9bus_PQD_DISTURBANCES';
load_system(mdl);

% Set Fault at Bus 4 with Rf = 0.1 ohm, ground = 0.01 ohm
fault_blk = [mdl '/PQD_Fault_Sag'];
set_param(fault_blk, 'FaultA', 'on', 'FaultB', 'on', 'FaultC', 'on', ...
    'GroundFault', 'on', 'SwitchTimes', '[0.12 0.20]', ...
    'FaultResistance', '0.01', 'GroundResistance', '0.01');

simOut = sim(mdl, 'StopTime', '0.30');
Vts = simOut.PQD_Vabc;
[Vres, tres] = resample(Vts.Data, Vts.Time, 5000);

% Compute half-cycle RMS
w_half = 42;
rms_prof = zeros(length(Vres) - w_half + 1, 3);
for k = 1:size(rms_prof, 1)
    rms_prof(k, :) = sqrt(mean(Vres(k:k+w_half-1, :).^2, 1));
end
t_rms = tres(1:size(rms_prof, 1));

idx_event = (t_rms >= 0.13) & (t_rms <= 0.19);
min_rms = min(rms_prof(idx_event, 1));
mean_rms = mean(rms_prof(idx_event, 1));
pre_rms = mean(rms_prof(t_rms < 0.10, 1));

fprintf('Bus 4 Solid Fault: Pre=%.4f, Event=%.4f, Min=%.4f, Ratio=%.4f\n', ...
    pre_rms, mean_rms, min_rms, mean_rms / pre_rms);
