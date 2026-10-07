% scripts/test_interruption_concept.m
% Test the electrical interruption mechanism

cur_dir = fileparts(mfilename('fullpath'));
project_root = fileparts(cur_dir);
addpath(fullfile(project_root, 'IEEE_9bus'));

mdl = 'IEEE_9bus_PQD_DISTURBANCES';
load_system(mdl);

% Let's see what happens if we place a breaker between Line 4-5 / 5-7 and Bus 5
% First verify current lines
disp('Checking connectivity of Bus 5...');
