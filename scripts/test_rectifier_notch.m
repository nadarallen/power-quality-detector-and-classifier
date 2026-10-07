% scripts/test_rectifier_notch.m
% Test building and simulating a physical 6-pulse rectifier on Bus 5

cur_dir = fileparts(mfilename('fullpath'));
project_root = fileparts(cur_dir);
addpath(fullfile(project_root, 'IEEE_9bus'));

mdl = 'IEEE_9bus_PQD_DISTURBANCES';
load_system(mdl);

% Let's inspect Universal Bridge blocks and pulse generators available in Simscape
disp('Testing Simscape components for 6-pulse rectifier:');
which_sps = which('powerlib');
disp(which_sps);

% Check if Synchronized 6-Pulse Generator exists
p6 = which('Synchronized 6-Pulse Generator');
disp(['Synchronized 6-Pulse Generator: ' p6]);
p6_blk = find_system('powerlib', 'RegExp', 'on', 'Name', '.*Pulse Generator.*');
disp('Pulse Generator blocks in powerlib:');
disp(p6_blk);
