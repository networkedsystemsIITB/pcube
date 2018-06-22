#!/usr/bin/python

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

from scapy.all import sniff, sendp
from scapy.all import Packet
from scapy.all import IntField, LongField

import networkx as nx

import sys
from time import sleep

HOSTNAME = int(sys.argv[1])

class LoadBalancePkt(Packet):
    name = "LoadBalancePkt"
    fields_desc = [
        LongField("preamble", 0),
        IntField("syn", 0),
        IntField("fin", 0),
        IntField("fid",0),
        IntField("subfid",0),
        IntField("packet_id",0),
        IntField("hash",0),
        IntField("count",0),
        IntField("swid", 0),
        IntField("flow_num", 0)
    ]


def main():
    num_flows = 80
    sleep_time = 10e-6
    max_flows = 10e4
    for flow in range(num_flows):
        fid = HOSTNAME*max_flows+flow
        # sleep(sleep_time)
        p = LoadBalancePkt(syn=1  , fid=fid) / ("SYN-" + str(fid))
        # print p.show()
        sendp(p, iface = "eth0")

    for flow in range(num_flows):
        for i in range(2):
            # sleep(sleep_time)
            fid = HOSTNAME*max_flows+flow
            p = LoadBalancePkt(fid=fid) / ("Data-"+str(fid) + "-" + str(i) + "-" + str(i))
            # print p.show()
            sendp(p, iface = "eth0")

    for flow in range(num_flows):
        fid = HOSTNAME*max_flows+flow
        # sleep(sleep_time)
        p = LoadBalancePkt(fin=1  , fid=fid) / ("FIN-" + str(fid))
        # print p.show()
        sendp(p, iface = "eth0")
if __name__ == '__main__':
    main()
