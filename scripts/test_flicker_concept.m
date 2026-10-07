% scripts/test_flicker_concept.m
% Tests the controlled physical Flicker mechanism on IEEE_9bus_PQD_DISTURBANCES.slx

cur_dir = fileparts(mfilename('fullpath'));
project_root = fileparts(cur_dir);
addpath(fullfile(project_root, 'IEEE_9bus'));

mdl = 'IEEE_9bus_PQD_DISTURBANCES';
load_system(mdl);

% Check existing blocks
disp('Loaded model.');

% We want to test adding PQD_Flicker controlled current sources and injecting
% a sinusoidal AM load current:
% i_flk(t) = I_m * sin(2*pi*fm*t) * sin(w0*t + phi)

% Let's test what I_m gives m = 0.05 (5% modulation)
% In harmonics, 45 A produced ~0.058 pu H3 voltage.
% Let's test with I_m = 40 A, fm = 10 Hz, f0 = 60 Hz.
fm = 10.0;
w0 = 2 * pi * 60.0;
t_vec = (0:1e-4:0.38)';

% Let's create the flicker current signal
I_m = 35.0; % Amps peak
ia = I_m * sin(2 * pi * fm * t_vec) .* sin(w0 * t_vec);
ib = I_m * sin(2 * pi * fm * t_vec) .* sin(w0 * t_vec - 2*pi/3);
ic = I_m * sin(2 * pi * fm * t_vec) .* sin(w0 * t_vec + 2*pi/3);

disp('Synthesized test test current vectors.');
close_system(mdl, 0);
