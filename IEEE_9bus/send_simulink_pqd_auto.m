function send_simulink_pqd_auto()
% SEND_SIMULINK_PQD_AUTO Model callback for IEEE 9-bus Simulink model.
% Called automatically on simulation completion (StopFcn).
% Starts a brief 0.1-second timer to dispatch send_pqd_now as soon as Simulink
% finishes assigning the simulation results ('ans' or 'out') into the base workspace.

    cur_dir = fileparts(mfilename('fullpath'));
    project_root = fullfile(cur_dir, '..');
    addpath(fullfile(project_root, 'integration', 'matlab'));
    addpath(fullfile(project_root, 'IEEE_9bus'));

    % If data is already in workspace, send immediately
    if evalin('base', 'exist(''ans'', ''var'') || exist(''out'', ''var'') || exist(''PQD_Vabc'', ''var'')')
        send_pqd_now();
        return;
    end

    % Otherwise, schedule 0.1s timer to run right after Simulink assigns ans to base
    fprintf('\n[PQD Auto-Bridge] Simulation finished. Scheduling live transfer to frontend...\n');
    t = timer('StartDelay', 0.1, 'ExecutionMode', 'singleShot', ...
              'TimerFcn', @(~,~) do_transfer(), ...
              'StopFcn', @(tmr,~) delete(tmr));
    start(t);
end

function do_transfer()
    try
        send_pqd_now();
    catch ME
        fprintf('[PQD Auto-Bridge] Transfer error: %s\n', ME.message);
    end
end
