% scripts/test_breaker_switching.m
addpath('IEEE_9bus');
load_system('IEEE_9bus_PQD_DISTURBANCES');

% Let's test a simple circuit with ThreePhaseBreaker
test_mdl = 'test_brk_simple';
new_system(test_mdl);
load_system(test_mdl);

add_block('spsThreePhaseBreakerLib/Three-Phase Breaker', [test_mdl '/Breaker']);
disp('Breaker dialog parameters:');
disp(get_param([test_mdl '/Breaker'], 'DialogParameters'));

close_system(test_mdl, 0);
