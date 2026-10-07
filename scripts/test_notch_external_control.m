% scripts/test_notch_external_control.m
% Test physical commutation notch using Three-Phase Fault with external control

cur_dir = fileparts(mfilename('fullpath'));
project_root = fileparts(cur_dir);
addpath(fullfile(project_root, 'IEEE_9bus'));

mdl = 'IEEE_9bus_PQD_DISTURBANCES';
load_system(mdl);
set_param(mdl, 'MaxStep', '1e-4');

% Ensure dummy workspace variables exist
dummy_ts = timeseries([0 0 0; 0 0 0], [0; 1]);
assignin('base', 'harm_inj_signal', dummy_ts);
assignin('base', 'flicker_inj_signal', dummy_ts);

% Configure PQD_Notch_Bus5 with External = 'on'
notch_blk = [mdl '/PQD_Notch_Bus5'];
set_param(notch_blk, 'External', 'on');
set_param(notch_blk, 'FaultA', 'on');
set_param(notch_blk, 'FaultB', 'on');
set_param(notch_blk, 'FaultC', 'off'); % Line-to-line commutation between Phase A & B
set_param(notch_blk, 'GroundFault', 'off');
set_param(notch_blk, 'FaultResistance', '150.0');

% Build control pulse signal in workspace:
% 600 us notch width, 1/cycle near peak
t_vec = (0:1e-5:0.38)';
u_notch = zeros(size(t_vec));

f0 = 60.0;
T0 = 1.0 / f0;
dt_rep = T0; % 16.667 ms spacing (1 notch per cycle)
width_s = 0.0006; % 600 us
t_offset = 0.005; % 5 ms offset (near peak of Va)

t_cur = 0.05 + t_offset;
count = 0;
while t_cur + width_s <= 0.35
    mask = (t_vec >= t_cur) & (t_vec < (t_cur + width_s));
    u_notch(mask) = 1.0;
    count = count + 1;
    t_cur = t_cur + dt_rep;
end
fprintf('Generated %d symmetric commutation pulses (width = %.1f us, rep = 2/cycle).\n', count, width_s * 1e6);

notch_ctrl_ts = timeseries(u_notch, t_vec);
assignin('base', 'notch_ctrl_signal', notch_ctrl_ts);

% Temporary Constant block for input port if not wired yet
if isempty(find_system(mdl, 'SearchDepth', 1, 'Name', 'PQD_Notch_FromWS_Test'))
    add_block('built-in/FromWorkspace', [mdl '/PQD_Notch_FromWS_Test'], ...
              'VariableName', 'notch_ctrl_signal', 'Position', [950, 970, 1000, 990]);
    add_line(mdl, 'PQD_Notch_FromWS_Test/1', 'PQD_Notch_Bus5/1', 'autorouting', 'on');
end

% Run simulation
t_start = tic;
simOut = sim(mdl, 'StopTime', '0.38');
t_sim = toc(t_start);
fprintf('Simulation completed in %.2f s.\n', t_sim);

Vts = simOut.PQD_Vabc;
[Vres, tres] = resample(Vts.Data, Vts.Time, 5000);

% Slicing 200 ms frame
frame_mask = (tres >= 0.09 - 1e-6) & (tres < 0.29 - 1e-6);
V_frame = Vres(frame_mask, :);
t_frame = tres(frame_mask) - 0.09;
if size(V_frame, 1) > 1000, V_frame = V_frame(1:1000, :); t_frame = t_frame(1:1000); end

v_a = V_frame(:, 1);
rms_a = sqrt(mean(v_a.^2));
peak_a = max(abs(v_a));

fprintf('Phase A: RMS = %.4f pu, Peak = %.4f pu\n', rms_a, peak_a);

% Save to test file
out_p = fullfile(project_root, 'data', 'ieee9bus_60hz', 'notch', 'test_external_notch.mat');
if ~exist(fileparts(out_p), 'dir'), mkdir(fileparts(out_p)); end
save(out_p, 'V_frame', 't_frame', 'Vres', 'tres', '-v7');

% Clean up test block
delete_line(mdl, 'PQD_Notch_FromWS_Test/1', 'PQD_Notch_Bus5/1');
delete_block([mdl '/PQD_Notch_FromWS_Test']);
close_system(mdl, 0);
disp('Test completed successfully.');
