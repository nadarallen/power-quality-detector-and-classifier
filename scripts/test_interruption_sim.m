% scripts/test_interruption_sim.m
% Test different interruption mechanisms on IEEE_9bus_PQD_DISTURBANCES

load_system('IEEE_9bus/IEEE_9bus_PQD_DISTURBANCES.slx');

% Check if PQD_Fault_Sag or PQD_Breaker_Swell are active
set_param('IEEE_9bus_PQD_DISTURBANCES/PQD_Fault_Sag', 'FaultMode', '0'); % disabled
set_param('IEEE_9bus_PQD_DISTURBANCES/PQD_Breaker_Swell', 'InitialState', '0', 'SwitchingTimes', '[999 999]');

disp('Testing simulation baseline...');
simOut = sim('IEEE_9bus/IEEE_9bus_PQD_DISTURBANCES.slx', 'StopTime', '0.2', 'SaveOutput', 'on');
v_base = simOut.Vabc_5;
t_base = simOut.tout;
v_base_rms = sqrt(mean(v_base(500:1000, 1).^2));
disp(['Baseline Phase A RMS: ' num2str(v_base_rms)]);
