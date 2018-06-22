import sys

if(len(sys.argv) < 3):
	print("format: python topo_generator.py <number of switches> <number of hosts per switch>")
	exit(0)

num_switches = int(sys.argv[1])
num_hosts = int(sys.argv[2])

total_hosts = num_switches * num_hosts

with open('topo.txt','w') as f:
	f.write('switches %d\n'%num_switches)
	f.write('hosts %d\n'%total_hosts)

	host_id = 1
	for i in range(num_switches):
		for j in range(num_hosts):
			f.write('h%d s%d\n' % (host_id,i+1))
			host_id+=1

	for i in range(num_switches):
		for j in range(i+1,num_switches):
			f.write('s%d s%d\n' % (i+1, j+1))