% scripts/test_notch_switching.m
% Test physical notch generation via commutation switching at Bus 5

cur_dir = fileparts(mfilename('fullpath'));
project_root = fileparts(cur_dir);
addpath(fullfile(project_root, 'IEEE_9bus'));

mdl = 'IEEE_9bus_PQD_DISTURBANCES';
load_system(mdl);

% Ensure FromWorkspace dummy variables exist
dummy_ts = timeseries([0 0 0; 0 0 0], [0; 1]);
assignin('base', 'harm_inj_signal', dummy_ts);
assignin('base', 'flicker_inj_signal', dummy_ts);

% Create test transition times: 600 us notch width, repeating every cycle (16.67 ms)
% from t = 0.05 to 0.35 s
t_start = 0.05;
f0 = 60.0;
T0 = 1 / f0; % 16.667 ms
width = 0.0006; % 600 us (3 samples at 5 kHz)

n_cycles = 18;
sw_times = [];
for k = 0:n_cycles
    tk = t_start + k * T0;
    sw_times = [sw_times, tk, tk + width];
end

sw_str = ['[' sprintf('%.6f ', sw_times) ']'];
fprintf('Generated %d switching transitions (width = %.1f us).\n', length(sw_times)/2, width*1e6);

% Let's test on a temporary block or inspect if PQD_Fault_Sag can be cloned
try
    notch_blk = [mdl '/PQD_Notch_Test'];
    if isempty(find_system(mdl, 'SearchDepth', 1, 'Name', 'PQD_Notch_Test'))
        add_block('spsThreePhaseFaultLib/Three-Phase Fault', notch_blk, ...
                  'Position', [1050, 950, 1100, 1000]);
        % Connect to Bus 5 RConn1, RConn2, RConn3
        add_line(mdl, 'Bus_5 230 KV/RConn1', 'PQD_Notch_Test/LConn1', 'autorouting', 'on');
        add_line(mdl, 'Bus_5 230 KV/RConn2', 'PQD_Notch_Test/LConn2', 'autorouting', 'on');
        add_line(mdl, 'Bus_5 230 KV/RConn3', 'PQD_Notch_Test/LConn3', 'autorouting', 'on');
    end
    
    set_param(notch_blk, 'FaultA', 'on', 'FaultB', 'on', 'FaultC', 'off', ...
              'GroundFault', 'off', 'FaultResistance', '25.0', ...
              'SwitchTimes', sw_str);
          
    disp('Successfully configured PQD_Notch_Test.');
    
    % Run quick simulation
    t_sim_start = tic;
    simOut = sim(mdl, 'StopTime', '0.20', 'ReturnWorkspaceOutputs', 'on');
    t_elapsed = toc(t_sim_start);
    fprintf('Simulation completed in %.2f seconds.\n', t_elapsed);
    
    % Check PQD_Vabc output
    Vabc = simOut.PQD_Vabc.Data;
    t = simOut.PQD_Vabc.Time;
    fprintf('Simulated %d points. Vabc shape: %d x %d\n', length(t), size(Vabc, 1), size(Vabc, 2));
    
    % Resample to 5000 Hz
    t_res = (0:1/5000:0.20)';
    V_res = interp1(t, Vabc, t_res);
    
    % Find minimum voltage around first notch (t = 0.05 s)
    idx_notch = find(t_res >= 0.048 & t_res <= 0.054);
    v_a_notch = V_res(idx_notch, 1);
    v_a_normal = max(V_res(1:200, 1));
    v_min = min(v_a_notch);
    
    depth = (v_a_normal - v_min) / v_a_normal;
    fprintf('Normal peak: %.4f pu, Notch trough: %.4f pu, Measured depth: %.2f%%\n', ...
            v_a_normal, v_min, depth * 100);
    
    % Clean up test block
    delete_line(mdl, 'Bus_5 230 KV/RConn1', 'PQD_Notch_Test/LConn1');
    delete_line(mdl, 'Bus_5 230 KV/RConn2', 'PQD_Notch_Test/LConn2');
    delete_line(mdl, 'Bus_5 230 KV/RConn3', 'PQD_Notch_Test/LConn3');
    delete_block(notch_blk);
    disp('Cleaned up PQD_Notch_Test.');
    
catch e
    disp(['Error during test: ' getReport(e)]);
    try
        close_system(mdl, 0);
    catch
    end
end
