% scripts/test_normal_generation.m
% Verification of 2-condition simulation and parameter variation

cur_dir = fileparts(mfilename('fullpath'));
project_root = fileparts(cur_dir);
addpath(fullfile(project_root, 'IEEE_9bus'));

mdl = 'IEEE_9bus_PQD_HIL_R2025a';
load_system(fullfile(project_root, 'IEEE_9bus', mdl));
set_param(mdl, 'StopFcn', '');

fprintf('Testing Condition 1: Nominal...\n');
tic;
simOut1 = sim(mdl, 'StopTime', '0.25');
t1 = toc;
Vts1 = simOut1.PQD_Vabc;
[Vres1, tres1] = resample(Vts1.Data, Vts1.Time, 5000);
mask1 = tres1 >= 0.05;
Vres1 = Vres1(mask1, :);
fprintf('Cond 1: Wall-time %.2fs | Samples: %d | Vrms: %.4f\n', t1, size(Vres1,1), sqrt(mean(Vres1(:,1).^2)));

fprintf('Testing Condition 2: Load +15%%, Freq 59.97 Hz...\n');
set_param([mdl '/125 MW 50 MVAR/Three-Phase Parallel RLC Load'], 'ActivePower', '143.75e6', 'InductivePower', '57.5e6');
set_param([mdl '/247.5 MVA, 16.5 kV'], 'Frequency', '59.97');
set_param([mdl '/192 MVA, 18 kV'], 'Frequency', '59.97');
set_param([mdl '/128 MVA, 13.8 kV'], 'Frequency', '59.97');

tic;
simOut2 = sim(mdl, 'StopTime', '0.25');
t2 = toc;
Vts2 = simOut2.PQD_Vabc;
[Vres2, tres2] = resample(Vts2.Data, Vts2.Time, 5000);
mask2 = tres2 >= 0.05;
Vres2 = Vres2(mask2, :);
fprintf('Cond 2: Wall-time %.2fs | Samples: %d | Vrms: %.4f\n', t2, size(Vres2,1), sqrt(mean(Vres2(:,1).^2)));

close_system(mdl, 0);
fprintf('[SUCCESS] Both test conditions executed cleanly.\n');
exit(0);
