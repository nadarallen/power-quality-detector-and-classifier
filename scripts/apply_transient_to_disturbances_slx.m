% scripts/apply_transient_to_disturbances_slx.m
% Permanently adds PQD_Transient infrastructure to IEEE_9bus_PQD_DISTURBANCES.slx
% Implements physical capacitor bank switching at Bus 5 per Gate 3C Section 4.8
% Ensures complete dormancy when dormant (Breaker open, SwitchTimes = [999 1000])

cur_dir = fileparts(mfilename('fullpath'));
project_root = fileparts(cur_dir);
addpath(fullfile(project_root, 'IEEE_9bus'));

mdl = 'IEEE_9bus_PQD_DISTURBANCES';
load_system(mdl);

brk_name = [mdl '/PQD_Breaker_Transient'];
rlc_name = [mdl '/PQD_RLC_Transient'];
gnd_name = [mdl '/PQD_Gnd_Transient'];

% 1. Ensure blocks exist
if isempty(find_system(mdl, 'SearchDepth', 1, 'Name', 'PQD_Breaker_Transient'))
    add_block('spsThreePhaseBreakerLib/Three-Phase Breaker', brk_name, 'Position', [1050, 800, 1100, 850]);
    add_line(mdl, 'Bus_5 230 KV/RConn1', 'PQD_Breaker_Transient/LConn1', 'autorouting', 'on');
    add_line(mdl, 'Bus_5 230 KV/RConn2', 'PQD_Breaker_Transient/LConn2', 'autorouting', 'on');
    add_line(mdl, 'Bus_5 230 KV/RConn3', 'PQD_Breaker_Transient/LConn3', 'autorouting', 'on');
    disp('Added PQD_Breaker_Transient and connected to Bus 5.');
else
    disp('PQD_Breaker_Transient already exists.');
end

if isempty(find_system(mdl, 'SearchDepth', 1, 'Name', 'PQD_RLC_Transient'))
    add_block('spsThreePhaseSeriesRLCBranchLib/Three-Phase Series RLC Branch', rlc_name, 'Position', [1150, 800, 1200, 850]);
    add_line(mdl, 'PQD_Breaker_Transient/RConn1', 'PQD_RLC_Transient/LConn1', 'autorouting', 'on');
    add_line(mdl, 'PQD_Breaker_Transient/RConn2', 'PQD_RLC_Transient/LConn2', 'autorouting', 'on');
    add_line(mdl, 'PQD_Breaker_Transient/RConn3', 'PQD_RLC_Transient/LConn3', 'autorouting', 'on');
    disp('Added PQD_RLC_Transient and connected to Breaker.');
else
    disp('PQD_RLC_Transient already exists.');
end

if isempty(find_system(mdl, 'SearchDepth', 1, 'Name', 'PQD_Gnd_Transient'))
    add_block('spsGroundLib/Ground', gnd_name, 'Position', [1250, 820, 1270, 840]);
    add_line(mdl, 'PQD_RLC_Transient/RConn1', 'PQD_Gnd_Transient/LConn1', 'autorouting', 'on');
    add_line(mdl, 'PQD_RLC_Transient/RConn2', 'PQD_Gnd_Transient/LConn1', 'autorouting', 'on');
    add_line(mdl, 'PQD_RLC_Transient/RConn3', 'PQD_Gnd_Transient/LConn1', 'autorouting', 'on');
    disp('Added PQD_Gnd_Transient and connected to RLC branch.');
else
    disp('PQD_Gnd_Transient already exists.');
end

% 2. Configure default parameters (dormant state)
set_param(rlc_name, 'BranchType', 'RLC');
set_param(rlc_name, 'Resistance', '1.0');
set_param(rlc_name, 'Inductance', '2.0e-3');
set_param(rlc_name, 'Capacitance', '2.0e-6');

set_param(brk_name, 'InitialState', 'open');
set_param(brk_name, 'SwitchTimes', '[999 1000]');
set_param(brk_name, 'SwitchA', 'off');
set_param(brk_name, 'SwitchB', 'off');
set_param(brk_name, 'SwitchC', 'off');
set_param(brk_name, 'BreakerResistance', '0.001');
set_param(brk_name, 'SnubberResistance', '1e5');
set_param(brk_name, 'SnubberCapacitance', '1e-9');

save_system(mdl);
close_system(mdl);
disp('Successfully configured complete PQD_Transient infrastructure in IEEE_9bus_PQD_DISTURBANCES.slx!');
