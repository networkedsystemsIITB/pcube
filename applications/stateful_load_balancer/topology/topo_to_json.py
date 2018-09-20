import json
from collections import OrderedDict

def get_topo_data(topo_file):
    with open(topo_file,'r') as f:
        data = json.load(f, object_pairs_hook=OrderedDict)
    return data

def read_topo():
    nb_hosts = 0
    nb_switches = 0
    links = []
    with open("topo.txt", "r") as f:
        line = f.readline()[:-1]
        w, nb_switches = line.split()
        assert(w == "switches")
        line = f.readline()[:-1]
        w, nb_hosts = line.split()
        assert(w == "hosts")
        for line in f:
            if not f: break
            a, b = line.split()
            links.append( (a, b) )

    json_data = OrderedDict()

    # Store number of switches and hosts
    json_data["nb_switches"], json_data["nb_hosts"] = int(nb_switches), int(nb_hosts)

    # Store all the links between hosts and switches
    json_data["links"] = OrderedDict()
    for i in range(0,len(links)):
        connection = OrderedDict()
        connection["_0"], connection["_1"] = links[i][0], links[i][1]
        json_data["links"]["_%d"%i] = connection

    # Store adjacency information for switches
    topo_stats = OrderedDict()
    for key in json_data["links"]:
        link = json_data["links"][key]

        a, b = link["_0"], link["_1"]
        if a.startswith("s") and b.startswith("s"):
            try:
                topo_stats[a]["SWITCHES"] += 1
            except:
                topo_stats[a] = {"SERVERS": 0, "SWITCHES": 1}
            try:
                topo_stats[b]["SWITCHES"] += 1
            except:
                topo_stats[b] = {"SERVERS": 0, "SWITCHES": 1}
        elif a.startswith("s"):
            try:
                topo_stats[a]["SERVERS"] += 1
            except:
                topo_stats[a] = {"SERVERS": 1, "SWITCHES": 0}
        elif b.startswith("s"):
            try:
                topo_stats[b]["SERVERS"] += 1
            except:
                topo_stats[b] = {"SERVERS": 1, "SWITCHES": 0}

    json_data["topo_stats"] = topo_stats
    return json_data

data = read_topo()
with open('int_topo.json', 'w') as out:
    json.dump(data, out, indent=4)

