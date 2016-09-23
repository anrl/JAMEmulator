#!/usr/bin/python

from sys import argv, exit, __stdout__
from yaml import load
from select import poll, POLLIN
from subprocess import Popen, PIPE

from mininet.net import Mininet
from mininet.topo import Topo
from mininet.log import setLogLevel
from mininet.node import CPULimitedHost
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.clean import Cleanup

from console import ConsoleApp

class Ethernet(Topo):
    def build(self, config, isWiFi=True):
        if ('cloud' in config): 
            for i in config['cloud']:
                cpu = i['cpu'] if 'cpu' in i else 1.0
                self.addHost(i['name'], cpu=cpu)
        if ('fog' in config): 
            for i in config['fog']:
                cpu = i['cpu'] if 'cpu' in i else 1.0
                self.addHost(i['name'], cpu=cpu)
        if ('device' in config):
            for i in config['device']:
                cpu = i['cpu'] if 'cpu' in i else 1.0
                self.addHost(i['name'], cpu=cpu)
        if ('switch' in config):
            for i in config['switch']:
                self.addSwitch(i['name'])
        if ('link' in config):
            for i in config['link']:
                bw = i['bw'] if 'bw' in i else 100
                delay = i['delay'] if 'delay' in i else '0ms'
                loss = i['loss'] if 'loss' in i else 0
                self.addLink(i['node1'], i['node2'], bw=bw, delay=delay, loss=loss)

def checkDupEth(config):
    hosts = list()
    nodes = list()

    if ('cloud' in config):
        for i in config['cloud']:
            hosts.append(i['name'])
    if ('fog' in config):
        for i in config['fog']:
            hosts.append(i['name'])
    if ('device' in config):
        for i in config['device']:
            hosts.append(i['name'])
    if ('link' in config):
        for i in config['link']:
            nodes.append(i['node1'])
            nodes.append(i['node2'])
    for i in hosts:
        if nodes.count(i) > 1:
            raise RuntimeError("Invalid topology: %s has duplicate eth interface" %i)


def logOutput(config, outfiles, errfiles):   
    if ('cloud' in config): 
        for i in config['cloud']:
            if ('cmd' in i):
                h = net.get(i['name'])
                outfiles[h] = '/tmp/%s.out' % h.name
                errfiles[h] = '/tmp/%s.err' % h.name
                h.cmd('echo >', outfiles[h])
                h.cmd('echo >', errfiles[h])
                h.cmdPrint(i['cmd'], '>', outfiles[h], '2>', errfiles[h], '&')
    if ('fog' in config): 
        for i in config['fog']:
            if ('cmd' in i):
                h = net.get(i['name'])
                outfiles[h] = '/tmp/%s.out' % h.name
                errfiles[h] = '/tmp/%s.err' % h.name
                h.cmd('echo >', outfiles[h])
                h.cmd('echo >', errfiles[h])
                h.cmdPrint(i['cmd'], '>', outfiles[h], '2>', errfiles[h], '&')
    if ('device' in config):
        for i in config['device']:
            if ('cmd' in i):
                h = net.get(i['name'])
                outfiles[h] = '/tmp/%s.out' % h.name
                errfiles[h] = '/tmp/%s.err' % h.name
                h.cmd('echo >', outfiles[h])
                h.cmd('echo >', errfiles[h])
                h.cmdPrint(i['cmd'], '>', outfiles[h], '2>', errfiles[h], '&')


def monitorFiles(outfiles, timeoutms):
    "Monitor set of files and return [(host, line)...]"
    devnull = open( '/dev/null', 'w' )
    tails, fdToFile, fdToHost = {}, {}, {}
    
    for h, outfile in outfiles.iteritems():
        tail = Popen(['tail', '-f', outfile],
                      stdout=PIPE, stderr=devnull)
        fd = tail.stdout.fileno()
        tails[h] = tail
        fdToFile[fd] = tail.stdout
        fdToHost[fd] = h
    # Prepare to poll output files
    readable = poll()
    
    for t in tails.values():
        readable.register(t.stdout.fileno(), POLLIN)
    try:    
        while True:
            fdlist = readable.poll(timeoutms)
            if fdlist:
                for fd, _flags in fdlist:
                    f = fdToFile[fd]
                    host = fdToHost[fd]
                    # Wait for a line of output
                    line = f.readline().strip()
                    yield host, line
            else:
                # If we timed out, return nothing
                yield None, ''
    except KeyboardInterrupt:
        for t in tails.values():
            t.terminate()
        devnull.close()  # Not really necessary

if __name__ == '__main__':    
    if len(argv) < 2: 
        print "usage: sudo python emulator.py config"
        exit()
    script, filename = argv
    data = open(filename)
    config = load(data)
    checkDupEth(config)
    #setLogLevel('info')
    try:
        topo = Ethernet(config) 
        net = Mininet(topo, host=CPULimitedHost, link=TCLink)
        net.addNAT().configDefault()
        net.start()
        #outfiles, errfiles = {}, {}
        #logOutput(config, outfiles, errfiles)
        # for host, line in monitorFiles(outfiles, timeoutms=500):
        #     if host:
        #         print '%s: %s' % (host.name, line)
        app = ConsoleApp(net)
        app.mainloop()
        net.stop()
    except KeyboardInterrupt:
        Cleanup.cleanup()
        
