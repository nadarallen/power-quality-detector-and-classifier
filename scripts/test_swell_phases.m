% scripts/test_swell_phases.m
cur = fileparts(mfilename('fullpath'));
root = fileparts(cur);
addpath(fullfile(root, 'IEEE_9bus'));

mdl = 'IEEE_9bus_PQD_DISTURBANCES';
load_system(mdl);
set_param(mdl, 'StopFcn', '');
set_param(mdl, 'Solver', 'ode23tb');
set_param(mdl, 'RelTol', '1e-4');

% Ensure Fault block is OFF
fault_blk = [mdl '/PQD_Fault_Sag'];
if ~isempty(find_system(mdl, 'SearchDepth', 1, 'Name', 'PQD_Fault_Sag'))
    set_param(fault_blk, 'FaultA', 'off', 'FaultB', 'off', 'FaultC', 'off', 'GroundFault', 'off');
end

brk_blk = [mdl '/PQD_Breaker_Swell'];
cap_blk = [mdl '/PQD_Cap_Swell'];

t_start = 0.12;
t_end   = 0.20;

set_param(brk_blk, 'InitialState', 'open');
set_param(brk_blk, 'SwitchTimes', sprintf('[%.4f %.4f]', t_start, t_end));
set_param(brk_blk, 'BreakerResistance', '0.001');
set_param(brk_blk, 'SnubberResistance', '1e6');
set_param(brk_blk, 'SnubberCapacitance', '0');

set_param(cap_blk, 'NominalVoltage', '230e3');
set_param(cap_blk, 'NominalFrequency', '60');
set_param(cap_blk, 'ActivePower', '100e3');
set_param(cap_blk, 'InductivePower', '0');
set_param(cap_blk, 'CapacitivePower', '150e6');

% Test 1: Single-phase swell (Phase A only)
set_param(brk_blk, 'SwitchA', 'on');
set_param(brk_blk, 'SwitchB', 'off');
set_param(brk_blk, 'SwitchC', 'off');

fprintf('Testing Single-Phase Swell (Phase A)...\n');
simOut = sim(mdl, 'StopTime', '0.38');
Vts = simOut.PQD_Vabc;
[Vres, tres] = resample(Vts.Data, Vts.Time, 5000);

fs = 5000; f0 = 60; hc = round(fs / (2*f0)); n = size(Vres, 1);
rms_a = zeros(n-hc+1, 1); rms_b = zeros(n-hc+1, 1); rms_c = zeros(n-hc+1, 1);
for i = 1:(n-hc+1)
    rms_a(i) = sqrt(mean(Vres(i:i+hc-1, 1).^2));
    rms_b(i) = sqrt(mean(Vres(i:i+hc-1, 2).^2));
    rms_c(i) = sqrt(mean(Vres(i:i+hc-1, 3).^2));
end
t_rms = (0:(n-hc))/fs;
pre_mask = (t_rms >= 0.04 & t_rms < 0.10);
ev_mask  = (t_rms >= 0.13 & t_rms <= 0.19);

pre_a = mean(rms_a(pre_mask)); pre_b = mean(rms_b(pre_mask)); pre_c = mean(rms_c(pre_mask));
ev_a = max(rms_a(ev_mask));    ev_b = max(rms_b(ev_mask));    ev_c = max(rms_c(ev_mask));

fprintf('Phase A: Pre=%.4f, Event=%.4f (ratio=%.3f)\n', pre_a, ev_a, ev_a/pre_a);
fprintf('Phase B: Pre=%.4f, Event=%.4f (ratio=%.3f)\n', pre_b, ev_b, ev_b/pre_b);
fprintf('Phase C: Pre=%.4f, Event=%.4f (ratio=%.3f)\n', pre_c, ev_c, ev_c/pre_c);

close_system(mdl, 0);
