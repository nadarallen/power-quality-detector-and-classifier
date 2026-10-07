% scripts/test_interruption_topology.m
% Test electrical network behavior under breaker openings

load_system('IEEE_9bus/IEEE_9bus_PQD_DISTURBANCES.slx');

% Check if Line 4 - 5 alone isolates Bus 5
disp('--- Analyzing Bus 5 connections ---');
% Bus 5 is connected to Line 4-5 and Line 5-7 and Load A (125 MW, 50 MVAR).
% In IEEE 9-bus system:
% Bus 4 is connected to Gen 1 (slack) and Line 4-5 and Line 4-6.
% Bus 7 is connected to Gen 2 and Line 5-7 and Line 7-8.
% Therefore, Bus 5 is a pass-through load bus fed from BOTH Bus 4 and Bus 7.
% If ONLY Line 4-5 is disconnected, power flows from Bus 7 via Line 5-7 into Bus 5.
% Thus, the voltage at Bus 5 remains energized (~0.95 pu)!
%
% For an interruption at Bus 5 (feeder/bus isolation):
% Either:
% 1) Breaker is placed at the supply to Bus 5 (or Bus 5 load feeder breaker opens),
%    OR
% 2) Both supply lines (Line 4-5 and Line 5-7) are opened by line breakers, isolating Bus 5,
%    OR
% 3) Breaker is placed in series with Bus 5 measurement / Load A, simulating feeder breaker trip.

disp('Topology analysis completed.');
