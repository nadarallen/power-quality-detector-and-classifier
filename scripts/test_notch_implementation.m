% scripts/test_notch_implementation.m
% Exploration script to test 6-pulse rectifier and controlled commutation mechanism at Bus 5

cur_dir = fileparts(mfilename('fullpath'));
project_root = fileparts(cur_dir);
addpath(fullfile(project_root, 'IEEE_9bus'));

mdl = 'IEEE_9bus_PQD_DISTURBANCES';
load_system(mdl);

fprintf('Testing Notch physical injection mechanisms on %s...\n', mdl);

% Check Bus 5 connections
b5_rconn = get_param([mdl '/Bus_5 230 KV'], 'PortConnectivity');
fprintf('Bus 5 has %d port connections.\n', length(b5_rconn));
