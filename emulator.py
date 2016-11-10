#!/usr/bin/python

from sys import argv, exit, __stdout__
from yaml import load
from select import poll, POLLIN
from subprocess import Popen, PIPE

from mininet.net import Mininet
from mininet.topo import Topo
from mininet.log import setLogLevel
from mininet.node import CPULimitedHost, Controller, OVSKernelSwitch
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.clean import Cleanup

from console import ConsoleApp

def checkDupEth(config):
    hosts = list()
    nodes = list()
    groups = ['cloud', 'fog', 'device', 'mobile'] 
    
    for i in groups:
        if (i in config):
            for j in config[i]:
                hosts.append(j['name'])
    if ('link' in config):
        for i in config['link']:
            nodes.append(i['node1'])
            nodes.append(i['node2'])
    for i in hosts:
        if nodes.count(i) > 1:
            raise RuntimeError("Invalid topology: %s has duplicate eth interface" %i)


def logOutput(group, config, outfiles, errfiles):   
    if (group in config): 
        for i in config[group]:
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
        net = Mininet(host=CPULimitedHost, controller=Controller, 
                      link=TCLink, switch=OVSKernelSwitch)
        c0 = net.addController('c0')   
        groups = ['cloud', 'fog', 'device']     
        for i in groups:
            if (i in config): 
                for j in config[i]:
                    cpu = j['cpu'] if 'cpu' in j else 1.0
                    net.addHost(j['name'], cpu=cpu)
        if ('mobile' in config): 
            for i in config['mobile']:
                cpu = i['cpu'] if 'cpu' in i else 1.0
                net.addStation(i['name'], cpu=cpu)
        if ('switch' in config):
            for i in config['switch']:
                net.addSwitch(i['name'])
        if ('accessPoint' in config):
            for i in config['accessPoint']:
                net.addBaseStation(i['name'])       
        if ('link' in config):
            for i in config['link']:
                bw = i['bw'] if 'bw' in i else 100
                delay = i['delay'] if 'delay' in i else '0ms'
                loss = i['loss'] if 'loss' in i else 0
                net.addLink(i['node1'], i['node2'], bw=bw, delay=delay, loss=loss)             
        net.build()
        net.addNAT().configDefault()
        c0.start()
        for i in getattr(net, 'switches'): 
            i.start([c0])     
        # outfiles, errfiles = {}, {}
        # for i in groups:
        #     logOutput(i, config, outfiles, errfiles)
        # for host, line in monitorFiles(outfiles, timeoutms=500):
        #     if host:
        #         print '%s: %s' % (host.name, line)
        app = ConsoleApp(net)
        app.mainloop()
        net.stop()
    except:
        Cleanup.cleanup()
        raise