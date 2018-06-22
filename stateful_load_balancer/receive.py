#!/usr/bin/python

from scapy.all import sniff, sendp
from scapy.all import Packet
from scapy.all import ShortField, IntField, LongField, BitField

import sys
import struct

def handle_pkt(pkt):
	pkt = str(pkt)
	if len(pkt) < 12: return
	preamble = pkt[:8]
	preamble_exp = "\x00" * 8
	if preamble != preamble_exp: return
	syn,fin = struct.unpack("<L", pkt[8:12])[0], struct.unpack("<L", pkt[12:16])[0]
	msg = pkt[28:]
	print msg
	sys.stdout.flush()

def main():
	sniff(iface = "eth0",
		  prn = lambda x: handle_pkt(x))

if __name__ == '__main__':
	main()
