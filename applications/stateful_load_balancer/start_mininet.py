#!/usr/bin/python

from mininet.net import Mininet
from mininet.topo import Topo
from mininet.log import setLogLevel, info
from mininet.cli import CLI
from mininet.link import TCLink

from p4_mininet import P4Switch, P4Host

import os
import json
import argparse
import subprocess
from time import sleep
from collections import OrderedDict

_THIS_DIR = os.path.dirname(os.path.realpath(__file__))
_THRIFT_BASE_PORT = 22222

parser = argparse.ArgumentParser(description='Mininet demo')
parser.add_argument('--behavioral-exe', help='Path to behavioral executable',
					type=str, action="store", required=True)
parser.add_argument('--json', help='Path to JSON config file',
					type=str, action="store", required=True)
parser.add_argument('--cli', help='Path to BM CLI',
					type=str, action="store", required=True)

args = parser.parse_args()

class MyTopo(Topo):
	def __init__(self, sw_path, json_path, nb_hosts, nb_switches, links, **opts):
		# Initialize topology and default options
		Topo.__init__(self, **opts)

		for i in xrange(nb_switches):
			switch = self.addSwitch('s%d' % (i + 1),
									sw_path = sw_path,
									json_path = json_path+"_s%d.json"%(i+1),
									thrift_port = _THRIFT_BASE_PORT + i,
									pcap_dump = True,
									device_id = i)

		for h in xrange(nb_hosts):
			host = self.addHost('h%d' % (h + 1))

		for a, b in links:
			self.addLink(a, b)

def get_links(json_links):
    links = []
    for key in json_links:
        link = json_links[key]
        a, b = link["_0"], link["_1"]  
        links.append( (a, b) )
    return links

def main():

	topo_data = None
	with open('topology/topo.json','r') as f:
		topo_data = json.load(f, object_pairs_hook=OrderedDict)

	nb_hosts = topo_data["nb_hosts"]
	nb_switches = topo_data["nb_switches"]

	topo = MyTopo(args.behavioral_exe,
				  args.json,
				  nb_hosts, 
				  nb_switches, 
				  get_links(topo_data["links"]))

	net = Mininet(topo = topo,
				  host = P4Host,
				  switch = P4Switch,
				  controller = None )
	net.start()

	for n in xrange(nb_hosts):
		h = net.get('h%d' % (n + 1))
		for off in ["rx", "tx", "sg"]:
			cmd = "/sbin/ethtool --offload eth0 %s off" % off
			print cmd
			h.cmd(cmd)
		print "disable ipv6"
		h.cmd("sysctl -w net.ipv6.conf.all.disable_ipv6=1")
		h.cmd("sysctl -w net.ipv6.conf.default.disable_ipv6=1")
		h.cmd("sysctl -w net.ipv6.conf.lo.disable_ipv6=1")
		h.cmd("sysctl -w net.ipv4.tcp_congestion_control=reno")
		h.cmd("iptables -I OUTPUT -p icmp --icmp-type destination-unreachable -j DROP")

	sleep(1)

	for i in xrange(nb_switches):
		cmd = [args.cli, "--json", args.json + "_s" + str(i + 1) + ".json" ,
			   "--thrift-port", str(_THRIFT_BASE_PORT + i)]

		with open("src/commands/commands_s%d.txt"%( i+1 ), "r") as f:
			print " ".join(cmd)
			try:
				output = subprocess.check_output(cmd, stdin = f)
				print output
			except subprocess.CalledProcessError as e:
				print e
				print e.output

		with open("src/commands/sync_commands_s%d.txt"%( i+1 ), "r") as f:
			print " ".join(cmd)
			try:
				output = subprocess.check_output(cmd, stdin = f)
				print output
			except subprocess.CalledProcessError as e:
				print e
				print e.output



	sleep(1)

	print "Ready !"

	CLI( net )
	net.stop()

if __name__ == '__main__':
	setLogLevel( 'info' )
	main()
