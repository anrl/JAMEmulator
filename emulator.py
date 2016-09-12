#!/usr/bin/python

from sys import argv
from yaml import load

from mininet.net import Mininet
from mininet.cli import CLI
from mininet.log import setLogLevel
from mininet.node import CPULimitedHost
from mininet.link import TCLink
from mininet.node import Node

from ethernet import Ethernet


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

def addWiFi(net, config):    
    if ('station' in config):
        for i in config['station']:
            net.addStation(i['name'])
    if ('baseStation' in config):
        for i in config['baseStation']:
           net.addBaseStation(i['name'])

if __name__ == '__main__':
    script, filename = argv
    data = open(filename)
    config = load(data)
    checkDupEth(config)
    setLogLevel('info')
    topo = Ethernet(config) 
    net = Mininet(topo, host=CPULimitedHost, link=TCLink)
    net.addNAT().configDefault()
    net.start()
    #addWiFi(net,config)

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
