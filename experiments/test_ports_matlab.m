root_dir = 'D:/my study/Project/power-quality-detector-and-classifier';
addpath(fullfile(root_dir, 'IEEE_9bus'));
addpath(fullfile(root_dir, 'integration/matlab'));
mdl = 'IEEE_9bus_PQD_DISTURBANCES';
load_system(mdl);

fprintf('=== Testing PQD_Fault_Sag ports before External=on ===\n');
disp(get_param([mdl '/PQD_Fault_Sag'], 'Ports'));

set_param([mdl '/PQD_Fault_Sag'], 'External', 'on');
fprintf('=== Testing PQD_Fault_Sag ports after External=on ===\n');
disp(get_param([mdl '/PQD_Fault_Sag'], 'Ports'));

fprintf('=== Testing PQD_Breaker_Swell ports after External=on ===\n');
set_param([mdl '/PQD_Breaker_Swell'], 'External', 'on');
disp(get_param([mdl '/PQD_Breaker_Swell'], 'Ports'));

fprintf('=== Testing PQD_Breaker_Interruption ports after External=on ===\n');
set_param([mdl '/PQD_Breaker_Interruption'], 'External', 'on');
disp(get_param([mdl '/PQD_Breaker_Interruption'], 'Ports'));

close_system(mdl, 0);
