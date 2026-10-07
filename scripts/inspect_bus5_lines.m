cur_dir = fileparts(mfilename('fullpath'));
project_root = fileparts(cur_dir);
addpath(fullfile(project_root, 'IEEE_9bus'));
load_system('IEEE_9bus_PQD_DISTURBANCES');

b5 = get_param('IEEE_9bus_PQD_DISTURBANCES/Bus_5 230 KV', 'Handle');
lines = find_system('IEEE_9bus_PQD_DISTURBANCES', 'FindAll', 'on', 'Type', 'line');
count = 0;
for i = 1:length(lines)
    src = get_param(lines(i), 'SrcBlockHandle');
    dst = get_param(lines(i), 'DstBlockHandle');
    if src == b5 || any(dst == b5)
        count = count + 1;
        src_name = 'none';
        if src > 0, src_name = get_param(src, 'Name'); end
        dst_str = '';
        for d = dst
            if d > 0
                dst_str = [dst_str ' ' get_param(d, 'Name')];
            end
        end
        fprintf('Line %d: Src=%s -> Dst=%s\n', count, src_name, dst_str);
    end
end
