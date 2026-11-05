% Diagnostic script to check model ports and injection
try
    mdl = 'IEEE_9bus_PQD_DISTURBANCES';
    f_ports = get_param([mdl '/PQD_Fault_Sag'], 'PortConnectivity');
    fprintf('=== PQD_Fault_Sag PortConnectivity ===\n');
    for i = 1:length(f_ports)
        fprintf('Port %s: Type=%s, SrcBlock=%s, DstBlock=%s\n', ...
            f_ports(i).Type, mat2str(f_ports(i).SrcBlock), mat2str(f_ports(i).DstBlock));
    end

    st_ports = get_param([mdl '/PQD_Live_Streamer'], 'PortConnectivity');
    fprintf('\n=== PQD_Live_Streamer PortConnectivity ===\n');
    for i = 1:length(st_ports)
        fprintf('Port %s: Type=%s, DstBlock=%s\n', ...
            st_ports(i).Type, mat2str(st_ports(i).DstBlock));
    end
catch e
    fprintf('Error: %s\n', e.message);
end
