% scripts/test_interruption_breaker.m
% Test adding PQD_Breaker_Interruption to IEEE_9bus_PQD_DISTURBANCES

cur_dir = fileparts(mfilename('fullpath'));
project_root = fileparts(cur_dir);
addpath(fullfile(project_root, 'IEEE_9bus'));

mdl = 'IEEE_9bus_PQD_DISTURBANCES';
load_system(mdl);

% Check if PQD_Breaker_Interruption already exists
brk_int = [mdl '/PQD_Breaker_Interruption'];
if isempty(find_system(mdl, 'SearchDepth', 1, 'Name', 'PQD_Breaker_Interruption'))
    disp('PQD_Breaker_Interruption does not exist yet.');
else
    disp('PQD_Breaker_Interruption already exists.');
end
