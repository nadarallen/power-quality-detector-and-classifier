% scripts/test_interruption_setup.m
% Tests the implementation of PQD_Breaker_Interruption in IEEE_9bus_PQD_DISTURBANCES

cur_dir = fileparts(mfilename('fullpath'));
project_root = fileparts(cur_dir);
addpath(fullfile(project_root, 'IEEE_9bus'));

mdl = 'IEEE_9bus_PQD_DISTURBANCES';
load_system(mdl);

% Let's inspect where Bus_5 230 KV and Load A are connected
disp('Inspecting Bus_5 230 KV ports and lines...');
b5 = [mdl '/Bus_5 230 KV'];
load_blk = [mdl '/125 MW\n50 MVAR'];
line45 = [mdl '/Line 4 - 5 '];
line57 = [mdl '/Line 5 - 7 '];

% Print block positions
disp(['b5 pos: ' mat2str(get_param(b5, 'Position'))]);
disp(['line45 pos: ' mat2str(get_param(line45, 'Position'))]);
disp(['line57 pos: ' mat2str(get_param(line57, 'Position'))]);
disp(['load pos: ' mat2str(get_param(load_blk, 'Position'))]);
