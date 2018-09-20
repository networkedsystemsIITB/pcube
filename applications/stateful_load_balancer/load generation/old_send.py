#!/usr/bin/env python3

from scapy.all import sniff, sendp
from scapy.all import Packet
from scapy.all import IntField, LongField

import sys
from random import seed,uniform
import threading
from time import sleep

from datetime import datetime

import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

if len(sys.argv) < 3:
	print("./send.py <client ID> <Experiment Time in seconds>")
	exit(0)

HOSTNAME = int(sys.argv[1])
total_exp_time = int(sys.argv[2])

IFACE = "eth0"
FLOW_THRESHOLD = 50
MIN_SLEEP, MAX_SLEEP = 0.0, 0.3
MIN_PACKET_NUM, MAX_PACKET_NUM = 4, 30
MIN_PACKET_LENGTH, MAX_PACKET_LENGTH = 5,20
CHANGE_FREQUENCY = 20
experiment_starts = datetime.now()
num_threads = 8
np.random.seed(0)

seed(101)

class LoadBalancePkt(Packet):
	name = "LoadBalancePkt"
	fields_desc = [
		LongField("preamble", 0),
		IntField("syn", 0),
		IntField("fin", 0),
		IntField("fid",0),
		IntField("hash",0),
		IntField("count",0),
		IntField("swid", 0),
		IntField("flow_num", 0)
	]

class Flow(threading.Thread):

	def __init__(self, fid):
		threading.Thread.__init__(self)
		self.fid = fid
		self.created_at = datetime.now()
		self.modified_at = datetime.now()

	def run(self):
		fid = self.fid
		subfid = 0
		change_frequency = CHANGE_FREQUENCY 
		means = [0.02, 0.2]
		k = 0
		experiment_starts_timestamp = experiment_starts.timestamp()

		log = open('timelog/' + str(fid) + '.log', 'w')

		while (datetime.now() - experiment_starts).total_seconds() < total_exp_time:
			subfid += 1
			time_gone = datetime.now() - self.modified_at
			if(time_gone.total_seconds() > total_exp_time/change_frequency):
				self.modified_at = datetime.now()
				k += 1
				k = k % len(means)
			mean = means[k]
			delay = 0
			while delay <= 0:
				delay = np.random.normal(mean, 0.1*mean)

			payload = "SYN-" + str(fid) + "-" + str(subfid)
			p = LoadBalancePkt(syn=1  , fid=fid) / payload
			print('syn'+str(fid) + "-" + str(subfid))
			p.show()
			sleep(delay)
			sendp(p, iface = IFACE)
			log.write(str(datetime.now().timestamp() -
                            experiment_starts_timestamp) + "\n")

			# print(fid)
			for i in range(int(uniform(MIN_PACKET_NUM,MAX_PACKET_NUM))):
				payload = "Data-" + str(fid) + "-" + str(subfid) + '-' + ((str(i)+'-')*int(uniform(MIN_PACKET_LENGTH,MAX_PACKET_LENGTH)))
				p = LoadBalancePkt(fid=fid) / payload
				p.show()
				sleep(delay)
				sendp(p, iface = IFACE)
				log.write(str(datetime.now().timestamp() - experiment_starts_timestamp) + "\n")

			payload = "FIN-" + str(fid) + "-" + str(subfid)
			p = LoadBalancePkt(fin=1, fid=fid) / payload
			p.show()
			sleep(delay)
			sendp(p, iface = IFACE)
			log.write(str(datetime.now().timestamp() - experiment_starts_timestamp) + "\n")
		
		log.close()

def draw_histogram():
	x = []
	for i in range(num_threads):
		fid = (HOSTNAME * FLOW_THRESHOLD) + i
		with open("timelog/" + str(fid) + '.log') as f:
			x += [float(j) for j in f.read().split()]


	x.sort()
	pd.DataFrame(x).plot(kind='density')
	plt.ylabel('Percentage')
	plt.show()
	# print(x)

def start_threads():
	threadLock = threading.Lock()
	threads = []

	for i in range(num_threads):
		try:
			t = Flow((HOSTNAME * FLOW_THRESHOLD) + i)
			t.start()
			threads.append(t)
		except:
		   print("Error: unable to start flow")

	for t in threads:
		t.join()

def main():
	start_threads()
	draw_histogram()

if __name__ == '__main__':
	main()