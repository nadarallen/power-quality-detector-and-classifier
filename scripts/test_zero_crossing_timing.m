% scripts/test_zero_crossing_timing.m
cur_dir = fileparts(mfilename('fullpath'));
project_root = fileparts(cur_dir);
addpath(fullfile(project_root, 'IEEE_9bus'));

mdl = 'IEEE_9bus_PQD_DISTURBANCES';
load_system(mdl);

% Set breaker switching times at exact zero-crossings of 60 Hz:
% t_start = 7 / 60 = 0.116667 s
% t_end   = 11 / 60 = 0.183333 s (duration = 4 cycles = 66.67 ms)
t_start = 7.0 / 60.0;
t_end   = 11.0 / 60.0;

int_blk = [mdl '/PQD_Breaker_Interruption'];
set_param(int_blk, 'InitialState', 'closed', ...
    'SwitchTimes', sprintf('[%.6f %.6f]', t_start, t_end), ...
    'SwitchA', 'on', 'SwitchB', 'on', 'SwitchC', 'on', ...
    'BreakerResistance', '0.001', 'SnubberResistance', '1e6', 'SnubberCapacitance', 'inf');

simOut = sim(mdl, 'StopTime', '0.38');
[Vres, tres] = resample(simOut.PQD_Vabc.Data, simOut.PQD_Vabc.Time, 5000);

% Slice 200 ms window: onset = 40 ms -> frame starts at t_start - 0.040 = 0.076667 s
t_f_start = t_start - 0.040;
idx_w = (tres >= t_f_start) & (tres < t_f_start + 0.200);
V_frame = Vres(idx_w, :);
if size(V_frame, 1) > 1000, V_frame = V_frame(1:1000, :); end

max_dA = max(abs(diff(V_frame(:, 1))));
max_dB = max(abs(diff(V_frame(:, 2))));
max_dC = max(abs(diff(V_frame(:, 3))));
max_all = max([max_dA, max_dB, max_dC]);

fprintf('Zero-Crossing Timing Test:\n');
fprintf('  Max delta_v: A=%.4f, B=%.4f, C=%.4f (Max=%.4f pu)\n', max_dA, max_dB, max_dC, max_all);
