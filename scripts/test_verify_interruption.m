% scripts/test_verify_interruption.m
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
              'Position', [870, 480, 910, 550]);
end

set_param(brk_name, 'InitialState', 'closed'); % closed initially
set_param(brk_name, 'SwitchA', 'on', 'SwitchB', 'on', 'SwitchC', 'on');
set_param(brk_name, 'SwitchTimes', '[0.12 0.20]');
set_param(brk_name, 'BreakerResistance', '0.001');
set_param(brk_name, 'SnubberResistance', '1e6');
set_param(brk_name, 'SnubberCapacitance', 'inf'); % pure resistive snubber

b5 = [test_mdl '/Bus_5 230 KV'];
ph_b5 = get_param(b5, 'PortHandles');

% Delete all 6 lines directly by handle
for i = 1:3
    lh = get_param(ph_b5.LConn(i), 'Line');
    if lh > 0, delete_line(lh); end
    lh = get_param(ph_b5.RConn(i), 'Line');
    if lh > 0, delete_line(lh); end
end

% Verify all lines connected to Bus 5 are 0
for i = 1:3
    disp(['LConn' num2str(i) ' Line after del: ' num2str(get_param(ph_b5.LConn(i), 'Line'))]);
    disp(['RConn' num2str(i) ' Line after del: ' num2str(get_param(ph_b5.RConn(i), 'Line'))]);
end

% Connect Line 4-5 directly to Line 5-7 (through transmission)
add_line(test_mdl, 'Line 4 - 5 /LConn1', 'Line 5 - 7 /RConn1', 'autorouting', 'on');
add_line(test_mdl, 'Line 4 - 5 /LConn2', 'Line 5 - 7 /RConn2', 'autorouting', 'on');
add_line(test_mdl, 'Line 4 - 5 /LConn3', 'Line 5 - 7 /RConn3', 'autorouting', 'on');

% Connect through-transmission junction to Breaker input
add_line(test_mdl, 'Line 5 - 7 /RConn1', 'PQD_Breaker_Interruption/LConn1', 'autorouting', 'on');
add_line(test_mdl, 'Line 5 - 7 /RConn2', 'PQD_Breaker_Interruption/LConn2', 'autorouting', 'on');
add_line(test_mdl, 'Line 5 - 7 /RConn3', 'PQD_Breaker_Interruption/LConn3', 'autorouting', 'on');

% Connect Breaker output to Bus 5 measurement input
add_line(test_mdl, 'PQD_Breaker_Interruption/RConn1', 'Bus_5 230 KV/LConn1', 'autorouting', 'on');
add_line(test_mdl, 'PQD_Breaker_Interruption/RConn2', 'Bus_5 230 KV/LConn2', 'autorouting', 'on');
add_line(test_mdl, 'PQD_Breaker_Interruption/RConn3', 'Bus_5 230 KV/LConn3', 'autorouting', 'on');

% Connect Bus 5 measurement output to Load A
load_blk = find_system(test_mdl, 'SearchDepth', 1, 'RegExp', 'on', 'Name', '125 MW.*');
load_name = get_param(load_blk{1}, 'Name');
add_line(test_mdl, 'Bus_5 230 KV/RConn1', [load_name '/LConn1'], 'autorouting', 'on');
add_line(test_mdl, 'Bus_5 230 KV/RConn2', [load_name '/LConn2'], 'autorouting', 'on');
add_line(test_mdl, 'Bus_5 230 KV/RConn3', [load_name '/LConn3'], 'autorouting', 'on');

disp('Re-wiring complete. Running simulation...');
t_start = tic;
simOut = sim(test_mdl, 'StopTime', '0.38');
t_wall = toc(t_start);
fprintf('Simulation completed in %.2f s\n', t_wall);

% Extract and resample PQD_Vabc
Vts = simOut.PQD_Vabc;
[Vres, tres] = resample(Vts.Data, Vts.Time, 5000);

N = size(Vres, 1);
w_half = 42;
rms_prof = zeros(N - w_half + 1, 3);
for k = 1:size(rms_prof, 1)
    rms_prof(k, :) = sqrt(mean(Vres(k:k+w_half-1, :).^2, 1));
end
t_rms = tres(1:size(rms_prof, 1));

idx_pre = (t_rms >= 0.04) & (t_rms <= 0.10);
v_pre_rms = mean(rms_prof(idx_pre, 1));

idx_event = (t_rms >= 0.14) & (t_rms <= 0.19);
v_event_rms = mean(rms_prof(idx_event, 1));
v_min_rms = min(rms_prof(idx_event, 1));

idx_post = (t_rms >= 0.23) & (t_rms <= 0.35);
v_post_rms = mean(rms_prof(idx_post, 1));

v_ratio = v_event_rms / v_pre_rms;
v_min_ratio = v_min_rms / v_pre_rms;

fprintf('========================================\n');
fprintf('VERIFIED INTERRUPTION SIMULATION RESULTS:\n');
fprintf('  Pre-event RMS:   %.4f pu\n', v_pre_rms);
fprintf('  Event RMS:       %.4f pu (Ratio: %.4f)\n', v_event_rms, v_ratio);
fprintf('  Minimum RMS:     %.4f pu (Ratio: %.4f)\n', v_min_rms, v_min_ratio);
fprintf('  Post-event RMS:  %.4f pu\n', v_post_rms);
fprintf('  IEEE 1159 Check: Residual < 0.10 pu: %s\n', mat2str(v_ratio < 0.10));
fprintf('========================================\n');

close_system(test_mdl, 0);
delete(fullfile(project_root, 'IEEE_9bus', [test_mdl '.slx']));
