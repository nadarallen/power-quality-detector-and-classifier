cur_dir = fileparts(mfilename('fullpath'));
project_root = fileparts(cur_dir);
addpath(fullfile(project_root, 'IEEE_9bus'));
load_system('IEEE_9bus_PQD_DISTURBANCES');

b5 = 'IEEE_9bus_PQD_DISTURBANCES/Bus_5 230 KV';
blks = find_system(b5, 'LookUnderMasks', 'all');
disp('All blocks under Bus 5:');
for i = 1:length(blks)
    disp(blks{i});
end
