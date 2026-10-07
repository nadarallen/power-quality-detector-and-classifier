% scripts/test_simple_breaker.m
addpath('IEEE_9bus');

test_mdl = 'test_brk_sim';
new_system(test_mdl);
load_system(test_mdl);

% Add powergui
add_block('powerlib/powergui', [test_mdl '/powergui']);
set_param([test_mdl '/powergui'], 'SimulationMode', 'Continuous');

% Add 3-phase source
add_block('powerlib/Electrical Sources/Three-Phase Source', [test_mdl '/Source'], ...
    'Voltage', '230e3', 'Frequency', '60');

% Add Three-Phase Breaker
add_block('spsThreePhaseBreakerLib/Three-Phase Breaker', [test_mdl '/Breaker'], ...
    'InitialState', 'closed', ...
    'SwitchTimes', '[0.05 0.15]', ...
    'BreakerResistance', '0.001', ...
    'SnubberResistance', '1e6', ...
    'SnubberCapacitance', 'inf');

% Add Three-Phase VI Measurement
add_block('spsThreePhaseVIMeasurementLib/Three-Phase V-I Measurement', [test_mdl '/VI'], ...
    'VoltageMeasurement', 'phase-to-ground');

% Add Load
add_block('powerlib/Elements/Three-Phase Parallel RLC Load', [test_mdl '/Load'], ...
    'NominalVoltage', '230e3', 'NominalFrequency', '60', ...
    'ActivePower', '125e6', 'InductivePower', '50e6');

% Connect Source -> Breaker -> VI -> Load
add_line(test_mdl, 'Source/1', 'Breaker/LConn1', 'autorouting', 'on');
add_line(test_mdl, 'Source/2', 'Breaker/LConn2', 'autorouting', 'on');
add_line(test_mdl, 'Source/3', 'Breaker/LConn3', 'autorouting', 'on');

add_line(test_mdl, 'Breaker/RConn1', 'VI/LConn1', 'autorouting', 'on');
add_line(test_mdl, 'Breaker/RConn2', 'VI/LConn2', 'autorouting', 'on');
add_line(test_mdl, 'Breaker/RConn3', 'VI/LConn3', 'autorouting', 'on');

add_line(test_mdl, 'VI/RConn1', 'Load/LConn1', 'autorouting', 'on');
add_line(test_mdl, 'VI/RConn2', 'Load/LConn2', 'autorouting', 'on');
add_line(test_mdl, 'VI/RConn3', 'Load/LConn3', 'autorouting', 'on');

% Add Outport to log VI/Vabc
add_block('built-in/Outport', [test_mdl '/Vabc']);
add_line(test_mdl, 'VI/1', 'Vabc/1');

simOut = sim(test_mdl, 'StopTime', '0.20', 'SaveOutput', 'on');
V = simOut.Vabc;
disp('Simulated successfully!');
disp(['V size: ' mat2str(size(V))]);
v_pre = sqrt(mean(V(1000:2000, 1).^2));
v_event = sqrt(mean(V(3500:6000, 1).^2));
v_post = sqrt(mean(V(8500:9500, 1).^2));
fprintf('Pre: %.1f V, Event: %.1f V, Post: %.1f V, Ratio: %.4f\n', ...
    v_pre, v_event, v_post, v_event / v_pre);

close_system(test_mdl, 0);
