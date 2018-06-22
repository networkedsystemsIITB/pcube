#!/bin/bash

# Copyright 2013-present Barefoot Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

###--- Remove stale json
for j in `seq 1 $2`
do
	rm p4src/distributed_stateful_load_balancer_$1_s$j.json
done

###--- Setup Environment
sudo rm -f *.pcap
sudo mn -c
THIS_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )

source $THIS_DIR/../../../../env.sh

P4C_BM_SCRIPT=$P4C_BM_PATH/p4c_bm/__main__.py

SWITCH_PATH=$BMV2_PATH/targets/simple_switch/simple_switch

# CLI_PATH=$BMV2_PATH/tools/runtime_CLI.py
CLI_PATH=$BMV2_PATH/tools/modified_runtime_CLI.py
# CLI_PATH=$BMV2_PATH/targets/simple_switch/sswitch_CLI.py

###--- Read topo, create json dump of topology
python topo_to_json.py

# This reads the topo.txt file and creates a dictionary with the following things:
# 1. Number of switches
# 2. Number of hosts
# 3. All the links (pair)
# 4. Topology Stats - For each switch, how many hosts and switches are connected to it
# (A host can be a server or a user - Later we will assume that there is only 1 user and rest of the hosts are servers)

### Sample dictionary

# OrderedDict([
#('nb_switches', 4), 
#('nb_hosts', 14), 
#('links', OrderedDict([('_0', OrderedDict([('_0', 'h1'), ('_1', 's1')])), ('_1', OrderedDict([('_0', 'h2'), ('_1', 's1')])), ('_2', OrderedDict([('_0', 'h3'), ('_1', 's2')])), ('_3', OrderedDict([('_0', 'h4'), ('_1', 's2')])), ('_4', OrderedDict([('_0', 'h5'), ('_1', 's2')])), ('_5', OrderedDict([('_0', 'h6'), ('_1', E's3')])), ('_6', OrderedDict([('_0', 'h7'), ('_1', 's3')])), ('_7', OrderedDict([('_0', 'h8'), ('_1', 's3')])), ('_8', OrderedDict([('_0', 'h9'), ('_1', 's3')])), ('_9', OrderedDict([('_0', 'h10'), ('_1', 's4')])), ('_10', OrderedDict([('_0', 'h11'), ('_1', 's4')])), ('_11', OrderedDict([('_0', 'h12'), ('_1', 's4')])), ('_12', OrderedDict([('_0', 'h13'), ('_1', 's4')])), ('_13', OrderedDict([('_0', 'h14'), ('_1', 's4')])), ('_14', OrderedDict([('_0', 's1'), ('_1', 's2')])), ('_15', OrderedDict([('_0', 's1'), ('_1', 's3')])), ('_16', OrderedDict([('_0', 's1'), ('_1', 's4')])), ('_17', OrderedDict([('_0', 's2'), ('_1', 's4')]))])), 
# ('topo_stats', OrderedDict([('s1', {'SWITCHES': 3, 'SERVERS': 2}), ('s2', {'SWITCHES': 2, 'SERVERS': 3}), ('s3', {'SWITCHES': 1, 'SERVERS': 4}), ('s4', {'SWITCHES': 2, 'SERVERS': 5})]))])

# ----------------------------------------------------

###--- Generate p4 for all switches from ip4
python3 p4src/generate_p4.py p4src/distributed_stateful_load_balancer_merged.ip4

# This gets the topology data from topo.json and then using the ip4, generates the P4 for each switch based on the topology.
# # For generation of P4, the following things are done in order:
# 1. Collection of #define constants and expansion of @for loops
# 2. Replace the #defined constants in the code with their value
# 3. Expland @compare statements
# 4. Expand @sum
# 5. Expand @bool
# 6. Expand @sync
# 7. Generation of default actions for tables - creates a template commands.txt for every switch

# -----------------------------------------------------------

###--- Generate commands for sending packets to lowest load server
# 5 is Threshold here
python generate_commands.py $1 5
# Appends results to the template commands.txt to get the final commands.txt

###--- Generate sync_commands.txt
python generate_sync_commands.py
# This generates commands for syncing and forwarding cloned packets (probe packets) - mcast groups are created based on the topology (takes in topo.json)

###--- Compile p4 for all switches
for j in `seq 1 $2`
do
    $P4C_BM_SCRIPT p4src/distributed_stateful_load_balancer_$1_s$j.p4 --json p4src/distributed_stateful_load_balancer_$1_s$j.json
    sudo $SWITCH_PATH >/dev/null 2>&1
done

###--- Burn json for each switch individually using topo.py
sudo PYTHONPATH=$PYTHONPATH:$BMV2_PATH/mininet/ python topo.py \
    --behavioral-exe $SWITCH_PATH \
    --json p4src/distributed_stateful_load_balancer_$1 \
    --cli $CLI_PATH
