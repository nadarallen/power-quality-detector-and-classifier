% scripts/test_breaker_on_line45.m
% Test opening Line 4-5 alone vs isolating Bus 5

cur_dir = fileparts(mfilename('fullpath'));
project_root = fileparts(cur_dir);
addpath(fullfile(project_root, 'IEEE_9bus'));

src_mdl = 'IEEE_9bus_PQD_DISTURBANCES';
test_mdl = 'IEEE_9bus_PQD_DISTURBANCES_TEST';

copyfile(fullfile(project_root, 'IEEE_9bus', [src_mdl '.slx']), ...
         fullfile(project_root, 'IEEE_9bus', [test_mdl '.slx']));
load_system(test_mdl);

% Let's insert a breaker on Line 4-5
% First find line from Line 4 - 5 to Bus 5
lines = get_param(test_mdl, 'Lines');
disp('Analyzing connections...');
