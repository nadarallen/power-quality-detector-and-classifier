cur_dir = fileparts(mfilename('fullpath'));
project_root = fileparts(cur_dir);
addpath(fullfile(project_root, 'IEEE_9bus'));
load_system('IEEE_9bus_PQD_DISTURBANCES');

b5 = get_param('IEEE_9bus_PQD_DISTURBANCES/Bus_5 230 KV', 'PortHandles');
for i = 1:3
    lh = get_param(b5.RConn(i), 'Line');
    disp(['--- RConn' num2str(i) ' Line: ' num2str(lh) ' ---']);
    ch = get_param(lh, 'LineChildren');
    disp(['LineChildren: ' mat2str(ch)]);
    d_ports = get_param(lh, 'DstPortHandle');
    disp(['DstPortHandle: ' mat2str(d_ports)]);
    for p = d_ports
        disp(['  Port parent: ' get_param(get_param(p, 'Parent'), 'Name')]);
    end
end
