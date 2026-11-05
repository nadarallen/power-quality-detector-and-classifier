root_dir = 'D:/my study/Project/power-quality-detector-and-classifier';
addpath(fullfile(root_dir, 'IEEE_9bus'));
mdl = 'IEEE_9bus_PQD_DISTURBANCES';
load_system(mdl);

dummy_ts = timeseries([0 0 0; 0 0 0], [0; 1]);
dummy_single = timeseries([0; 0], [0; 1]);
assignin('base', 'harm_inj_signal', dummy_ts);
assignin('base', 'flicker_inj_signal', dummy_ts);
assignin('base', 'notch_ctrl_signal', dummy_single);

% Add a step block for external trigger
set_param([mdl '/PQD_Fault_Sag'], 'FaultA', 'on', 'FaultB', 'on', 'FaultC', 'on', ...
          'GroundFault', 'on', 'FaultResistance', '2.0', 'GroundResistance', '0.01', ...
          'External', 'on');

step_blk = [mdl '/Test_Step'];
add_block('simulink/Sources/Step', step_blk, 'Time', '0.05', 'Before', '0', 'After', '1');
add_line(mdl, 'Test_Step/1', 'PQD_Fault_Sag/1');

set_param(mdl, 'StopTime', '0.15', 'Solver', 'ode23tb');
sim(mdl);

V = evalin('base', 'PQD_Vabc');
t = V.Time;
d = V.Data;

idx_norm = find(t >= 0.02 & t < 0.04);
idx_fault = find(t >= 0.07 & t < 0.12);

rms_norm = sqrt(mean(d(idx_norm, 1).^2));
rms_fault = sqrt(mean(d(idx_fault, 1).^2));

fprintf('External Step RMS Normal (t=0.03): %.4f pu\n', rms_norm);
fprintf('External Step RMS Fault  (t=0.10): %.4f pu\n', rms_fault);

close_system(mdl, 0);
