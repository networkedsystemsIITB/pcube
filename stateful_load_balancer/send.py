#!/usr/bin/env python3

from scapy.all import sendp
from scapy.all import Packet
from scapy.all import IntField, LongField

import sys
from random import seed,uniform,choice
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
TOTAL_EXP_TIME = int(sys.argv[2])

IFACE = "eth0"
THREAD_THRESHOLD = 100
MIN_PACKET_LENGTH, MAX_PACKET_LENGTH = 5,20

EXPERIMENT_STARTS = datetime.now()

#Experiment knobs
NUM_THREADS = 30

TIME_STEP = [5,15,25]
TIME_STEP_PROB = [0.3,0.4,0.3]

FLOW_LENGTH = [30,200,1000]
FLOW_LENGTH_PROB = [0.5,0.5,0]

THREAD_SLEEP_PROB = [0.99,0.01]
###

seed(101)
np.random.seed(0)

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

class Flow(threading.Thread):

	def __init__(self, fid):
		threading.Thread.__init__(self)
		self.fid = fid
		self.created_at = datetime.now()
		self.modified_at = datetime.now()
		self.time_step = list(TIME_STEP)
		self.time_step_prob = list(TIME_STEP_PROB)
		self.thread_sleep = [0,np.random.choice(self.time_step, p=self.time_step_prob)]
		self.thread_sleep_prob = list(THREAD_SLEEP_PROB)


	def run(self):

		# sleep(np.random.choice([0.5,1,1.5], p=[0.25,0.5,0.25]))

		fid = self.fid
		subfid = 0
		means = [1e-5, 1e-4]
		mean = choice(means)
		curr_time_step = self.thread_sleep[1]
		EXPERIMENT_STARTS_timestamp = EXPERIMENT_STARTS.timestamp()
		log = open('timelog/' + str(fid) + '.log', 'w')

		while (datetime.now() - EXPERIMENT_STARTS).total_seconds() < TOTAL_EXP_TIME:
	
			subfid += 1
			time_gone = datetime.now() - self.modified_at
			
			if(time_gone.total_seconds() > curr_time_step):
				curr_time_step = np.random.choice(self.time_step, p=self.time_step_prob)
				self.thread_sleep = [0,curr_time_step]
				self.thread_sleep_prob.reverse()
				self.modified_at = datetime.now()
				mean = choice(means)

			if self.fid > 0:
				sleep(np.random.choice(self.thread_sleep, p=self.thread_sleep_prob))

			delay = 0
			while delay <= 0:
				delay = np.random.normal(mean, 0.1*mean)

			payload = "SYN-" + str(fid) + "-" + str(subfid)
			p = LoadBalancePkt(syn=1, fid=fid, subfid=subfid, packet_id=0) / payload
			# p.show()
			sleep(delay)
			sendp(p, iface = IFACE)
			log.write(str(datetime.now().timestamp() -
                            EXPERIMENT_STARTS_timestamp) + " %d %d %d\n"%(1,fid,subfid))

			for i in range(np.random.choice(FLOW_LENGTH, p=FLOW_LENGTH_PROB)):
				payload = "Data-" + str(fid) + "-" + str(subfid) + '-' + ((str(i)+'-')*int(uniform(MIN_PACKET_LENGTH,MAX_PACKET_LENGTH)))
				p = LoadBalancePkt(fid=fid, subfid=subfid, packet_id=i) / payload
				# p.show()
				sleep(delay)
				sendp(p, iface = IFACE)
				log.write(str(datetime.now().timestamp() - EXPERIMENT_STARTS_timestamp) + " %d %d %d\n"%(0,fid,subfid))

			payload = "FIN-" + str(fid) + "-" + str(subfid)
			p = LoadBalancePkt(fin=1, fid=fid, subfid=subfid, packet_id=i) / payload
			# p.show()
			sleep(delay)
			sendp(p, iface = IFACE)
			log.write(str(datetime.now().timestamp() - EXPERIMENT_STARTS_timestamp) + " %d %d %d\n"%(2,fid,subfid))
		
		log.close()


class ConstFlow(threading.Thread):
	
	def __init__(self):
		threading.Thread.__init__(self)

	def run(self):
		while((datetime.now() - EXPERIMENT_STARTS).total_seconds() < TOTAL_EXP_TIME):
			p = LoadBalancePkt(fid=4294967295, subfid=4294967295, packet_id=4294967295) / ""
			sendp(p, iface = IFACE)

def draw_histogram():
	x = []
	syn,fin = [], []
	fmap = {}
	for i in range(NUM_THREADS):
		fid = (HOSTNAME * THREAD_THRESHOLD) + i
		with open("timelog/" + str(fid) + '.log') as f:
			for row in f:
				time,index,fid,subfid = row.split()
				time,index = float(time), int(index)
				x.append(time)
				if index == 1: 
					syn.append(time)
					fmap[(fid,subfid)] = {'syn':time}
				elif index == 2: 
					fin.append(time)
					fmap[(fid,subfid)]['fin'] = time

	x.sort()
	flow_rate,STEP = [], 0.5
	flow_rate_smooth = []
	for i in np.arange(0,int(x[-1])+1,STEP):
		fcount = 0
		for k in fmap:
			if fmap[k]['syn'] < i and fmap[k]['fin'] >i:
				fcount += 1
				flow_rate_smooth.append(i)
		flow_rate.append(fcount)

	pd.DataFrame(x).plot(kind='density',figsize=(TOTAL_EXP_TIME,1))
	for s in syn: plt.axvline(s,color='r')
	for f in fin: plt.axvline(f,color='g')
	ax = plt.gca()
	ax.set_xlim((x[0],x[-1]))
	plt.xlabel('Time (in seconds)');plt.ylabel('Percentage of packets')
	plt.savefig('packets_%d_%d-%d.png'%(NUM_THREADS, TOTAL_EXP_TIME,HOSTNAME), bbox_inches='tight')
	# plt.show()

	pd.DataFrame(flow_rate_smooth).plot(kind='density')
	ax = plt.gca()
	ax.set_xlim((flow_rate_smooth[0],flow_rate_smooth[-1]))
	plt.xlabel('Time (in seconds)');plt.ylabel('Percentage of flows')
	plt.savefig('flow_density_%d_%d-%d.png'%(NUM_THREADS, TOTAL_EXP_TIME,HOSTNAME), bbox_inches='tight')
	# plt.show()

	plt.plot(np.arange(0,int(x[-1])+1,STEP),flow_rate)
	ax = plt.gca()
	plt.xlabel('Time (in seconds)');plt.ylabel('Number of flows')
	ax.set_ylim((0,NUM_THREADS+2))
	plt.savefig('flows_%d_%d-%d.png'%(NUM_THREADS, TOTAL_EXP_TIME,HOSTNAME), bbox_inches='tight')
	plt.show()

def start_threads():
	threadLock = threading.Lock()
	threads = []

	for i in range(NUM_THREADS):
		try:
			t = Flow((HOSTNAME * THREAD_THRESHOLD) + i)
			t.start()
			threads.append(t)
		except:
		   print("Error: unable to start flow")

	for t in threads:
		t.join()

def experiment_info():
	info = open('experiment-%d.info'%HOSTNAME, 'w')
	info.write("Experiment time = %ds\n"%TOTAL_EXP_TIME)
	info.write("Number of threads = %d\n"%NUM_THREADS)
	info.write("Time steps: [%d,%d,%d]\n"%tuple(TIME_STEP))
	info.write("Time steps probability: [%f,%f,%f]\n"%tuple(TIME_STEP_PROB))
	info.write("Flow length: [%d,%d,%d]\n"%tuple(FLOW_LENGTH))
	info.write("Flow length probability: [%f,%f,%f]\n"%tuple(FLOW_LENGTH_PROB))
	info.write("Thread sleep probability: [%f,%f]\n"%tuple(THREAD_SLEEP_PROB))
	info.close()

def main():
	experiment_info()
	start_threads()
	draw_histogram()

if __name__ == '__main__':
	main()