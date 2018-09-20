import sys
import json
from collections import OrderedDict

CREATE_GROUP = "mc_mgrp_create %d\n"
CREATE_NODE = "mc_node_create %d %d\n"
ASSOCIATE_NODE = "mc_node_associate %d %d\n"
MIRRORING_ADD = "mirroring_add %d %d\n"

def generate_sync_commands(topo_stats,commands_path):
	mgrp_no = 1

	#Need to sort keys to keep a one to one mapping for switch number to mcast group
	keylist = topo_stats.keys()
	keylist.sort()

	for key in keylist:
		node_no = 0
		f = open("%s/sync_commands_%s.txt"%(commands_path,key), 'a')
		stat = topo_stats[key]
		num_hosts = stat["SERVERS"]
		num_switches = stat["SWITCHES"]
		total_ports = num_hosts + num_switches
		f.write(CREATE_GROUP % mgrp_no)
		for i in range(1, num_switches + 1):
			f.write(CREATE_NODE % (node_no, num_hosts + i))
			f.write(ASSOCIATE_NODE % (mgrp_no, node_no))
			node_no += 1
		mgrp_no += 1

		for i in range(1, total_ports + 1):
			f.write(MIRRORING_ADD % (i, i))
		f.close()


if __name__ == '__main__':
	if sys.argv < 3:
		print("Usage: python3 generate_sync_commands.py <topology in json> <commands_path>")
		sys.exit()

	topo_file = sys.argv[1]
	commands_path = sys.argv[2]

	with open(topo_file,'r') as f:
		data = json.load(f, object_pairs_hook=OrderedDict)
		generate_sync_commands(data["topo_stats"],commands_path)