import json
from collections import OrderedDict

from topo_to_json import get_topo_data

data = get_topo_data('int_topo.json')

for switch in data["topo_stats"]:
	data["topo_stats"][switch]["SERVERPLUSONE"] = data["topo_stats"][switch]["SERVERS"] + 1
	data["topo_stats"][switch]["SERVERMINUSONE"] = data["topo_stats"][switch]["SERVERS"] - 1

	data["topo_stats"][switch]["SWITCHPLUSONE"] = data["topo_stats"][switch]["SWITCHES"] + 1
	data["topo_stats"][switch]["SWITCHMINUSONE"] = data["topo_stats"][switch]["SWITCHES"] - 1
	
	data["topo_stats"][switch]["SWITCHPLUSSERVER"] = data["topo_stats"][switch]["SERVERS"] + data["topo_stats"][switch]["SWITCHES"]

with open('topo.json', 'w') as out:
    json.dump(data, out, indent=4)