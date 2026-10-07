% scripts/test_calibrate_flicker.m
% Calibrates Flicker current injection vs resulting voltage modulation depth m on Bus 5

cur_dir = fileparts(mfilename('fullpath'));
project_root = fileparts(cur_dir);
addpath(fullfile(project_root, 'IEEE_9bus'));

mdl = 'IEEE_9bus_PQD_DISTURBANCES';
load_system(mdl);

% Ensure dummy harm_inj_signal exists
dummy_ts = timeseries([0 0 0; 0 0 0], [0; 1]);
assignin('base', 'harm_inj_signal', dummy_ts);

% Ensure other disturbances are dormant
set_param([mdl '/PQD_Fault_Sag'], 'FaultA', 'off', 'FaultB', 'off', 'FaultC', 'off', ...
    'GroundFault', 'off', 'SwitchTimes', '[999 1000]');
set_param([mdl '/PQD_Breaker_Swell'], 'InitialState', 'open', 'SwitchTimes', '[999 1000]', ...
    'SwitchA', 'off', 'SwitchB', 'off', 'SwitchC', 'off');
set_param([mdl '/PQD_Breaker_Interruption'], 'InitialState', 'closed', 'SwitchTimes', '[999 1000]', ...
    'SwitchA', 'off', 'SwitchB', 'off', 'SwitchC', 'off');
set_param([mdl '/PQD_Harm_Enable'], 'Value', '0');

% Enable Flicker
set_param([mdl '/PQD_Flicker_Enable'], 'Value', '1');

% Let's test with fm = 10 Hz
t_vec = (0:1e-4:0.38)';
w0 = 2 * pi * 60;
fm = 10.0;

% Test I_m = 230.0 A
I_m = 230.0;
ia = I_m * sin(2 * pi * fm * t_vec) .* sin(w0 * t_vec);
ib = I_m * sin(2 * pi * fm * t_vec) .* sin(w0 * t_vec - 2*pi/3);
ic = I_m * sin(2 * pi * fm * t_vec) .* sin(w0 * t_vec + 2*pi/3);

flicker_inj_signal = timeseries([ia, ib, ic], t_vec);
assignin('base', 'flicker_inj_signal', flicker_inj_signal);

simOut = sim(mdl, 'StopTime', '0.38');
Vts = simOut.PQD_Vabc;
[Vres, tres] = resample(Vts.Data, Vts.Time, 5000);

% Slicing window: [0.09, 0.29] (200 ms, 1000 samples)
mask = (tres >= 0.09 - 1e-6 & tres < 0.29 - 1e-6);
V_frame = Vres(mask, :);
if size(V_frame, 1) > 1000, V_frame = V_frame(1:1000, :); end

% Compute half-cycle RMS of phase A
v_a = V_frame(:, 1);
half_cycle = round(5000 / (2 * 60)); % 42
rms_trace = zeros(length(v_a) - half_cycle + 1, 1);
for i = 1:length(rms_trace)
    rms_trace(i) = sqrt(mean(v_a(i:i+half_cycle-1).^2));
end

rms_mean = mean(rms_trace);
rms_min = min(rms_trace);
rms_max = max(rms_trace);
m_depth = (rms_max - rms_min) / (2 * rms_mean);

fprintf('--- CALIBRATION RESULTS ---\n');
fprintf('I_m: %.1f A\n', I_m);
fprintf('Mean RMS: %.4f pu\n', rms_mean);
fprintf('Min RMS: %.4f pu\n', rms_min);
fprintf('Max RMS: %.4f pu\n', rms_max);
fprintf('Modulation depth m (half-cycle RMS): %.4f (%.2f%%)\n', m_depth, m_depth * 100);

% Compute Hilbert envelope on phase A
va_analytic = hilbert(v_a);
env = abs(va_analytic);
env_mean = mean(env);
env_min = min(env);
env_max = max(env);
env_depth = (env_max - env_min) / (2 * env_mean);
fprintf('Analytic envelope depth: %.4f (%.2f%%)\n', env_depth, env_depth * 100);

% Check THD on phase A
f_sig = fft(v_a);
mag = abs(f_sig(1:500));
[fund_mag, fund_bin] = max(mag(10:15));
fund_bin = fund_bin + 9;
harm_bins = [fund_bin*2-1, fund_bin*3-2, fund_bin*5-4, fund_bin*7-6]; % 2nd, 3rd, 5th, 7th
harm_energy = sum(mag(harm_bins).^2);
thd_est = sqrt(harm_energy) / fund_mag * 100;
fprintf('THD estimate: %.3f%%\n', thd_est);

% Reset Flicker Enable = 0
set_param([mdl '/PQD_Flicker_Enable'], 'Value', '0');
save_system(mdl);
close_system(mdl, 0);
