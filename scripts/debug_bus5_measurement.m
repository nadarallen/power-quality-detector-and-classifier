% scripts/debug_bus5_measurement.m
cur_dir = fileparts(mfilename('fullpath'));
project_root = fileparts(cur_dir);
addpath(fullfile(project_root, 'IEEE_9bus'));

src_mdl = 'IEEE_9bus_PQD_DISTURBANCES';
test_mdl = 'IEEE_9bus_PQD_DISTURBANCES_TEST';

copyfile(fullfile(project_root, 'IEEE_9bus', [src_mdl '.slx']), ...
         fullfile(project_root, 'IEEE_9bus', [test_mdl '.slx']));
load_system(test_mdl);

% Print exactly what is inside Bus_5 230 KV
b5 = [test_mdl '/Bus_5 230 KV'];
disp(get_param(b5, 'DialogParameters'));
disp(['Vbase: ' num2str(get_param(b5, 'Vbase'))]);
disp(['OutputType: ' get_param(b5, 'OutputType')]);

close_system(test_mdl, 0);
delete(fullfile(project_root, 'IEEE_9bus', [test_mdl '.slx']));
