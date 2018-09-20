########################################################
# 1. generate commands.txt based on threshold
########################################################

import sys
import json
from collections import OrderedDict

if len(sys.argv) < 3:
    print("Format: %s <SERVER_THRESHOLD> <TOPOLOGY>" % sys.argv[0])
    sys.exit()

THRESHOLD = int(sys.argv[1])

def generate(num_servers_left, l):
    if num_servers_left == 1:
        s = ""
        for j in range(THRESHOLD):
            new_l = l + [j]
            min_val = min(new_l)
            min_ind = new_l.index(min_val)
            s += "table_add set_server_dest_port_table set_server_dest_port " + \
                ' '.join([str(i) for i in new_l]) + " => %d %d\n" % (min_val, min_ind + 2)
        return s
    else:
        s = ""
        for j in range(THRESHOLD):
            s += generate(num_servers_left - 1, l + [j])
        return s

def generate_commands(topo_stats):
    keylist = topo_stats.keys()

    for key in keylist:
        template = open('src/commands/commands_template_%s.txt' % key, 'r')
        s = template.read()
        stat = topo_stats[key]
        # Assuming only 1 host
        num_servers = stat['SERVERS'] - 1
        s += generate(num_servers, [])

        commands = open('src/commands/commands_%s.txt' % key, 'w')
        commands.write(s)
        commands.close()
        template.close()

if __name__ == '__main__':
    
    with open(sys.argv[2],'r') as f:
        data = json.load(f, object_pairs_hook=OrderedDict)        
        generate_commands(data["topo_stats"])
