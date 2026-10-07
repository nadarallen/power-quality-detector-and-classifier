% scripts/test_interruption_phases.m
cur_dir = fileparts(mfilename('fullpath'));
proj_root = fileparts(cur_dir);
addpath(fullfile(proj_root, 'IEEE_9bus'));
mdl = 'IEEE_9bus_PQD_DISTURBANCES';
load_system(mdl);
brk_blk = [mdl '/PQD_Breaker_Interruption'];

% Test Phase A only (single-phase interruption)
fprintf('--- Testing Phase A Interruption ---\n');
set_param(brk_blk, 'SwitchA', 'on', 'SwitchB', 'off', 'SwitchC', 'off');
set_param(brk_blk, 'SwitchTimes', '[0.04 0.11]');
simOut = sim(mdl, 'StopTime', '0.20');
[Vres, tres] = resample(simOut.PQD_Vabc.Data, simOut.PQD_Vabc.Time, 5000);

mask_pre = (tres >= 0.01 & tres <= 0.035);
mask_evt = (tres >= 0.06 & tres <= 0.10);

vpre_a = sqrt(mean(Vres(mask_pre, 1).^2));
vevt_a = sqrt(mean(Vres(mask_evt, 1).^2));
vpre_b = sqrt(mean(Vres(mask_pre, 2).^2));
vevt_b = sqrt(mean(Vres(mask_evt, 2).^2));
vpre_c = sqrt(mean(Vres(mask_pre, 3).^2));
vevt_c = sqrt(mean(Vres(mask_evt, 3).^2));

fprintf('Phase A: pre=%.4f, evt=%.4f, ratio=%.4f\n', vpre_a, vevt_a, vevt_a/vpre_a);
fprintf('Phase B: pre=%.4f, evt=%.4f, ratio=%.4f\n', vpre_b, vevt_b, vevt_b/vpre_b);
fprintf('Phase C: pre=%.4f, evt=%.4f, ratio=%.4f\n', vpre_c, vevt_c, vevt_c/vpre_c);

% Reset to closed
set_param(brk_blk, 'SwitchA', 'on', 'SwitchB', 'on', 'SwitchC', 'on', 'SwitchTimes', '[999 999]');
close_system(mdl, 0);
