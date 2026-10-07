% scripts/inspect_bus5_ports_detail.m
cur_dir = fileparts(mfilename('fullpath'));
project_root = fileparts(cur_dir);
addpath(fullfile(project_root, 'IEEE_9bus'));
load_system('IEEE_9bus_PQD_DISTURBANCES');

b5 = 'IEEE_9bus_PQD_DISTURBANCES/Bus_5 230 KV';
ph = get_param(b5, 'PortHandles');
disp('Bus 5 PortHandles:');
disp(ph);
for i = 1:length(ph.LConn)
    line_h = get_param(ph.LConn(i), 'Line');
    disp(['LConn' num2str(i) ' Line: ' num2str(line_h)]);
end
for i = 1:length(ph.RConn)
    line_h = get_param(ph.RConn(i), 'Line');
    disp(['RConn' num2str(i) ' Line: ' num2str(line_h)]);
end
