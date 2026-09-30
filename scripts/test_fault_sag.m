% scripts/test_fault_sag.m
cur_dir = fileparts(mfilename('fullpath'));
project_root = fileparts(cur_dir);
addpath(fullfile(project_root, 'IEEE_9bus'));

pristine_mdl = fullfile(project_root, 'IEEE_9bus', 'IEEE_9bus_PQD_HIL_R2025a.slx');
working_mdl_path = fullfile(project_root, 'IEEE_9bus', 'IEEE_9bus_PQD_DISTURBANCES.slx');

% 1. Copy pristine to working model if not exists
if ~exist(working_mdl_path, 'file')
    fprintf('Copying pristine model to working model...\n');
    copyfile(pristine_mdl, working_mdl_path);
end

working_mdl = 'IEEE_9bus_PQD_DISTURBANCES';
load_system(working_mdl);
set_param(working_mdl, 'StopFcn', '');

% 2. Check if PQD_Fault_Sag already exists
fault_blk = [working_mdl '/PQD_Fault_Sag'];
if isempty(find_system(working_mdl, 'SearchDepth', 1, 'Name', 'PQD_Fault_Sag'))
    fprintf('Adding Three-Phase Fault block at Bus 4...\n');
    add_block('powerlib/Elements/Three-Phase Fault', fault_blk, 'Position', [700, 200, 750, 260]);
    
    % Connect terminals to Line 4 - 5 RConn (which is Bus 4 node)
    add_line(working_mdl, 'Line 4 - 5 /RConn1', 'PQD_Fault_Sag/LConn1', 'autorouting', 'on');
    add_line(working_mdl, 'Line 4 - 5 /RConn2', 'PQD_Fault_Sag/LConn2', 'autorouting', 'on');
    add_line(working_mdl, 'Line 4 - 5 /RConn3', 'PQD_Fault_Sag/LConn3', 'autorouting', 'on');
    save_system(working_mdl);
end

% 3. Configure Fault parameters: 3-phase fault at Bus 4
% Switch times: start at 0.12 s, end at 0.22 s (duration = 100 ms = 6 cycles)
set_param(fault_blk, 'FaultA', 'on', 'FaultB', 'on', 'FaultC', 'on', 'GroundFault', 'on');
set_param(fault_blk, 'SwitchTimes', '[0.12 0.22]');
set_param(fault_blk, 'FaultResistance', '30'); % Test 30 ohms
set_param(fault_blk, 'GroundResistance', '0.01');

fprintf('Running simulation with 30 ohm fault at Bus 4...\n');
simOut = sim(working_mdl, 'StopTime', '0.38');

Vts = simOut.PQD_Vabc;
t = Vts.Time;
v = Vts.Data;

% Resample to 5000 Hz
[vres, tres] = resample(v, t, 5000);

% Pre-event: 0.06 to 0.11 s
mask_pre = (tres >= 0.06 & tres <= 0.11);
rms_pre = sqrt(mean(vres(mask_pre, 1).^2));

% During event: 0.13 to 0.21 s
mask_event = (tres >= 0.13 & tres <= 0.21);
rms_event = sqrt(mean(vres(mask_event, 1).^2));

% Post-event: 0.25 to 0.35 s
mask_post = (tres >= 0.25 & tres <= 0.35);
rms_post = sqrt(mean(vres(mask_post, 1).^2));

residual_pu = rms_event / rms_pre;

fprintf('\n=== SIMULATION RESULTS (Bus 5 Voltage) ===\n');
fprintf('Pre-event RMS (Phase A):  %.4f pu\n', rms_pre);
fprintf('Event RMS (Phase A):      %.4f pu\n', rms_event);
fprintf('Post-event RMS (Phase A): %.4f pu\n', rms_post);
fprintf('Residual Voltage:         %.4f pu (%.1f%% of pre-event)\n', residual_pu, residual_pu * 100);

close_system(working_mdl, 1);
