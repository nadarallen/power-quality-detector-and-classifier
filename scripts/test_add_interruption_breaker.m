% scripts/test_add_interruption_breaker.m
% Test adding PQD_Breaker_Interruption on a test copy of the disturbance model

cur_dir = fileparts(mfilename('fullpath'));
project_root = fileparts(cur_dir);
addpath(fullfile(project_root, 'IEEE_9bus'));

src_mdl = 'IEEE_9bus_PQD_DISTURBANCES';
test_mdl = 'IEEE_9bus_PQD_DISTURBANCES_TEST';

% Copy file
copyfile(fullfile(project_root, 'IEEE_9bus', [src_mdl '.slx']), ...
         fullfile(project_root, 'IEEE_9bus', [test_mdl '.slx']));

load_system(test_mdl);

% Try adding the three-phase breaker
brk_name = [test_mdl '/PQD_Breaker_Interruption'];
if isempty(find_system(test_mdl, 'SearchDepth', 1, 'Name', 'PQD_Breaker_Interruption'))
    add_block('spsThreePhaseBreakerLib/Three-Phase Breaker', brk_name, ...
              'Position', [810, 300, 860, 360]);
    disp('Successfully added PQD_Breaker_Interruption block!');
else
    disp('PQD_Breaker_Interruption already exists in test model.');
end

% Check its parameters
disp('DialogParameters of Three-Phase Breaker:');
disp(get_param(brk_name, 'DialogParameters'));

close_system(test_mdl, 0);
delete(fullfile(project_root, 'IEEE_9bus', [test_mdl '.slx']));
disp('Test completed cleanly.');
