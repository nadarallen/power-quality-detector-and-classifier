% scripts/test_interruption_regression_all.m
% Tests that Normal, Sag, Swell, and Interruption all work identically and correctly

cur_dir = fileparts(mfilename('fullpath'));
project_root = fileparts(cur_dir);
addpath(fullfile(project_root, 'IEEE_9bus'));

test_mdl = 'IEEE_9bus_PQD_DISTURBANCES_TEST';
src_mdl = 'IEEE_9bus_PQD_DISTURBANCES';

copyfile(fullfile(project_root, 'IEEE_9bus', [src_mdl '.slx']), ...
         fullfile(project_root, 'IEEE_9bus', [test_mdl '.slx']));
load_system(test_mdl);

% Add PQD_Breaker_Interruption
brk_name = [test_mdl '/PQD_Breaker_Interruption'];
add_block('spsThreePhaseBreakerLib/Three-Phase Breaker', brk_name, ...
          'Position', [870, 480, 910, 550]);

b5 = [test_mdl '/Bus_5 230 KV'];
ph_b5 = get_param(b5, 'PortHandles');
load_blk = find_system(test_mdl, 'SearchDepth', 1, 'RegExp', 'on', 'Name', '125 MW.*');
load_name = get_param(load_blk{1}, 'Name');
ph_load = get_param(load_blk{1}, 'PortHandles');

for i = 1:3
    lh = get_param(ph_b5.LConn(i), 'Line');
    if lh > 0, delete_line(lh); end
    lh = get_param(ph_b5.RConn(i), 'Line');
    if lh > 0, delete_line(lh); end
    lh = get_param(ph_load.LConn(i), 'Line');
    if lh > 0, delete_line(lh); end
end

add_line(test_mdl, 'Line 4 - 5 /LConn1', 'Line 5 - 7 /RConn1', 'autorouting', 'on');
add_line(test_mdl, 'Line 4 - 5 /LConn2', 'Line 5 - 7 /RConn2', 'autorouting', 'on');
add_line(test_mdl, 'Line 4 - 5 /LConn3', 'Line 5 - 7 /RConn3', 'autorouting', 'on');

add_line(test_mdl, 'Line 5 - 7 /RConn1', 'PQD_Breaker_Interruption/LConn1', 'autorouting', 'on');
add_line(test_mdl, 'Line 5 - 7 /RConn2', 'PQD_Breaker_Interruption/LConn2', 'autorouting', 'on');
add_line(test_mdl, 'Line 5 - 7 /RConn3', 'PQD_Breaker_Interruption/LConn3', 'autorouting', 'on');

add_line(test_mdl, 'PQD_Breaker_Interruption/RConn1', 'Bus_5 230 KV/LConn1', 'autorouting', 'on');
add_line(test_mdl, 'PQD_Breaker_Interruption/RConn2', 'Bus_5 230 KV/LConn2', 'autorouting', 'on');
add_line(test_mdl, 'PQD_Breaker_Interruption/RConn3', 'Bus_5 230 KV/LConn3', 'autorouting', 'on');

add_line(test_mdl, 'Bus_5 230 KV/RConn1', [load_name '/LConn1'], 'autorouting', 'on');
add_line(test_mdl, 'Bus_5 230 KV/RConn2', [load_name '/LConn2'], 'autorouting', 'on');
add_line(test_mdl, 'Bus_5 230 KV/RConn3', [load_name '/LConn3'], 'autorouting', 'on');

% 1. TEST NORMAL (Breaker closed, sag disabled, swell disabled)
set_param(brk_name, 'InitialState', 'closed', 'SwitchTimes', '[999 1000]', ...
    'SwitchA', 'off', 'SwitchB', 'off', 'SwitchC', 'off', ...
    'BreakerResistance', '0.001', 'SnubberResistance', '1e6', 'SnubberCapacitance', 'inf');
set_param([test_mdl '/PQD_Fault_Sag'], 'FaultA', 'off', 'FaultB', 'off', 'FaultC', 'off', ...
    'GroundFault', 'off', 'SwitchTimes', '[999 1000]');
set_param([test_mdl '/PQD_Breaker_Swell'], 'InitialState', 'open', 'SwitchTimes', '[999 1000]', ...
    'SwitchA', 'off', 'SwitchB', 'off', 'SwitchC', 'off');

simOut = sim(test_mdl, 'StopTime', '0.25');
[Vnorm, ~] = resample(simOut.PQD_Vabc.Data, simOut.PQD_Vabc.Time, 5000);
rms_norm = sqrt(mean(Vnorm(500:1000, 1).^2));
fprintf('NORMAL TEST: RMS = %.4f pu (Expected ~0.5887)\n', rms_norm);

% 2. TEST SAG (Breaker closed, Sag 3P fault Rf=60 ohm)
set_param([test_mdl '/PQD_Fault_Sag'], 'FaultA', 'on', 'FaultB', 'on', 'FaultC', 'on', ...
    'GroundFault', 'on', 'SwitchTimes', '[0.12 0.20]', 'FaultResistance', '60', 'GroundResistance', '0.01');
simOut = sim(test_mdl, 'StopTime', '0.25');
[Vsag, ~] = resample(simOut.PQD_Vabc.Data, simOut.PQD_Vabc.Time, 5000);
rms_sag = sqrt(mean(Vsag(700:900, 1).^2));
fprintf('SAG TEST: Event RMS = %.4f pu, Ratio = %.4f (Expected 0.35-0.55)\n', rms_sag, rms_sag / rms_norm);

% 3. TEST SWELL (Breaker closed, Sag off, Swell 3P cap 150 MVAR)
set_param([test_mdl '/PQD_Fault_Sag'], 'FaultA', 'off', 'FaultB', 'off', 'FaultC', 'off', ...
    'GroundFault', 'off', 'SwitchTimes', '[999 1000]');
set_param([test_mdl '/PQD_Breaker_Swell'], 'InitialState', 'open', 'SwitchTimes', '[0.12 0.20]', ...
    'SwitchA', 'on', 'SwitchB', 'on', 'SwitchC', 'on', 'BreakerResistance', '0.001', ...
    'SnubberResistance', '1e6', 'SnubberCapacitance', 'inf');
set_param([test_mdl '/PQD_Cap_Swell'], 'NominalVoltage', '230e3', 'NominalFrequency', '60', ...
    'ActivePower', '100e3', 'InductivePower', '0', 'CapacitivePower', '150e6');
simOut = sim(test_mdl, 'StopTime', '0.25');
[Vswl, ~] = resample(simOut.PQD_Vabc.Data, simOut.PQD_Vabc.Time, 5000);
rms_swl = sqrt(mean(Vswl(700:900, 1).^2));
fprintf('SWELL TEST: Event RMS = %.4f pu, Ratio = %.4f (Expected 1.25-1.40)\n', rms_swl, rms_swl / rms_norm);

% 4. TEST INTERRUPTION (Swell off, Sag off, Breaker opens at 0.12, closes at 0.20)
set_param([test_mdl '/PQD_Breaker_Swell'], 'InitialState', 'open', 'SwitchTimes', '[999 1000]', ...
    'SwitchA', 'off', 'SwitchB', 'off', 'SwitchC', 'off');
set_param(brk_name, 'InitialState', 'closed', 'SwitchTimes', '[0.12 0.20]', ...
    'SwitchA', 'on', 'SwitchB', 'on', 'SwitchC', 'on');
simOut = sim(test_mdl, 'StopTime', '0.25');
[Vint, ~] = resample(simOut.PQD_Vabc.Data, simOut.PQD_Vabc.Time, 5000);
rms_int = sqrt(mean(Vint(700:900, 1).^2));
fprintf('INTERRUPTION TEST: Event RMS = %.4f pu, Ratio = %.4f (Expected < 0.10)\n', rms_int, rms_int / rms_norm);

close_system(test_mdl, 0);
delete(fullfile(project_root, 'IEEE_9bus', [test_mdl '.slx']));
