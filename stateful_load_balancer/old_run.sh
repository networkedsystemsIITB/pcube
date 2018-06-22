rm distributed_stateful_load_balancer_$1.json
sudo mn -c
THIS_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
source $THIS_DIR/../../../../env.sh
P4C_BM_SCRIPT=$P4C_BM_PATH/p4c_bm/__main__.py
SWITCH_PATH=$BMV2_PATH/targets/simple_switch/simple_switch
CLI_PATH=$BMV2_PATH/tools/modified_runtime_CLI.py

$P4C_BM_SCRIPT p4src/distributed_stateful_load_balancer_$1.p4 --json distributed_stateful_load_balancer_$1.json
# This gives libtool the opportunity to "warm-up"
sudo $SWITCH_PATH >/dev/null 2>&1
sudo PYTHONPATH=$PYTHONPATH:$BMV2_PATH/mininet/ python old_topo.py \
 	--behavioral-exe $SWITCH_PATH \
    --json distributed_stateful_load_balancer_$1.json \
 	--cli $CLI_PATH