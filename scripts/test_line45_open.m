% scripts/test_line45_open.m
% Disconnect Line 4-5 and measure Bus 5 voltage

cur_dir = fileparts(mfilename('fullpath'));
project_root = fileparts(cur_dir);
addpath(fullfile(project_root, 'IEEE_9bus'));

mdl = 'IEEE_9bus_PQD_DISTURBANCES';
load_system(mdl);

% Let's see: if we change the line resistance or disconnect Line 4-5
% Line 4 - 5 is a ThreePhasePiSectionLineBlock.
% Let's check parameters of Line 4 - 5
disp(get_param([mdl '/Line 4 - 5 '], 'DialogParameters'));
