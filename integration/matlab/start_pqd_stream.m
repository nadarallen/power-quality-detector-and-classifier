% START_PQD_STREAM
% Convenience launcher for MATLAB/Simulink IEEE 9-bus -> Python PQD bridge.
%
% Usage:
%   start_pqd_stream
%
% This script runs IEEE_9bus_PQD_HIL_R2025a.slx for 0.2s (or specified duration),
% resamples the Bus 5 three-phase waveform to 5000 Hz with anti-aliasing,
% and streams it via HTTP POST to the local Python PQD server.

fprintf('\n[start_pqd_stream] Starting IEEE 9-Bus Simulink Stream Bridge...\n');

% Ensure paths
script_dir = fileparts(mfilename('fullpath'));
addpath(script_dir);

try
    summary = run_simulink_pqd('stop_time', 0.2, 'batch_size', 1000);
    fprintf('[start_pqd_stream] Stream session complete. All chunks ingested successfully.\n');
catch ME
    fprintf('[start_pqd_stream] ERROR during streaming session: %s\n', ME.message);
    rethrow(ME);
end
