#!/usr/bin/python

from sys import argv
from yaml import load

from mininet.net import Mininet
from mininet.cli import CLI
from mininet.log import setLogLevel
from mininet.node import CPULimitedHost
from mininet.link import TCLink

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

def createTopo(net, config):
    
    if ('cloud' in config): 
        for i in config['cloud']:
            cpu = i['cpu'] if 'cpu' in i else 1.0
            host = net.addHost(i['name'], cpu=cpu)
    if ('fog' in config): 
        for i in config['fog']:
            cpu = i['cpu'] if 'cpu' in i else 1.0
            host = net.addHost(i['name'], cpu=cpu)
    if ('device' in config):
        for i in config['device']:
            cpu = i['cpu'] if 'cpu' in i else 1.0
            host = net.addHost(i['name'], cpu=cpu)
    if ('switch' in config):
        for i in config['switch']:
            net.addSwitch(i['name'])
    if ('station' in config):
        for i in config['station']:
            net.addStation(i['name'])
    if ('link' in config):
        for i in config['link']:
            bw = i['bw'] if 'bw' in i else 100
            delay = i['delay'] if 'delay' in i else '0ms'
            loss = i['loss'] if 'loss' in i else 0
            net.addLink(i['node1'], i['node2'], bw=bw, delay=delay, loss=loss)

if __name__ == '__main__':
    script, filename = argv
    data = open(filename)
    config = load(data)
    checkDupEth(config) 
    net = Mininet(host=CPULimitedHost, link=TCLink)
    createTopo(net, config)
    setLogLevel('info')
    net.start()

    if ('cloud' in config): 
        for i in config['cloud']:
            if ('cmd' in i):
                host = net.get(i['name'])
                host.cmd(i['cmd'])
    if ('fog' in config): 
        for i in config['fog']:
            if ('cmd' in i):
                host = net.get(i['name'])
                host.cmd(i['cmd']) 
    if ('device' in config):
        for i in config['device']:
            if ('cmd' in i):
                host = net.get(i['name'])
                host.cmd(i['cmd']) 
    CLI(net)
    net.stop()
