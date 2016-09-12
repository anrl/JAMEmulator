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

def startNAT(root, inetIntf='wlan0', subnet='10.0/8'):
    """Start NAT/forwarding between Mininet and external network
    root: node to access iptables from
    inetIntf: interface for internet access
    subnet: Mininet subnet (default 10.0/8)="""

    # Identify the interface connecting to the mininet network
    localIntf = root.defaultIntf()

    # Flush any currently active rules
    root.cmd('iptables -F')
    root.cmd('iptables -t nat -F')

    # Create default entries for unmatched traffic
    root.cmd('iptables -P INPUT ACCEPT')
    root.cmd('iptables -P OUTPUT ACCEPT')
    root.cmd('iptables -P FORWARD DROP')

    # Configure NAT
    root.cmd('iptables -I FORWARD -i', localIntf, '-d', subnet, '-j DROP')
    root.cmd('iptables -A FORWARD -i', localIntf, '-s', subnet, '-j ACCEPT')
    root.cmd('iptables -A FORWARD -i', inetIntf, '-d', subnet, '-j ACCEPT')
    root.cmd('iptables -t nat -A POSTROUTING -o ', inetIntf, '-j MASQUERADE')

    # Instruct the kernel to perform forwarding
    root.cmd('sysctl net.ipv4.ip_forward=1')

def stopNAT( root ):
    """Stop NAT/forwarding between Mininet and external network"""
    # Flush any currently active rules
    root.cmd('iptables -F')
    root.cmd('iptables -t nat -F')

    # Instruct the kernel to stop forwarding
    root.cmd('sysctl net.ipv4.ip_forward=0')

def fixNetworkManager(root, intf):
    """Prevent network-manager from messing with our interface,
       by specifying manual configuration in /etc/network/interfaces
       root: a node in the root namespace (for running commands)
       intf: interface name"""
    cfile = '/etc/network/interfaces'
    line = '\niface %s inet manual\n' % intf
    config = open(cfile).read()
    if line not in config:
        print '*** Adding', line.strip(), 'to', cfile
        with open(cfile, 'a') as f:
            f.write(line)
        # Probably need to restart network-manager to be safe -
        # hopefully this won't disconnect you
        root.cmd('service network-manager restart')

def connectToInternet(network, switch='s0', rootip='10.254', subnet='10.0/8'):
    """Connect the network to the internet
       switch: switch to connect to root namespace
       rootip: address for interface in root namespace
       subnet: Mininet subnet"""
    switch = network.get(switch)
    prefixLen = subnet.split('/')[1]

    # Create a node in root namespace
    root = Node('root', inNamespace=False)

    # Prevent network-manager from interfering with our interface
    fixNetworkManager(root, 'root-wlan0')

    # Create link between root NS and switch
    link = network.addLink(root, switch)
    link.intf1.setIP(rootip, prefixLen)

    # Start network that now includes link to root namespace
    network.start()

    # Start NAT and establish forwarding
    startNAT(root)

    # Establish routes from end hosts
    for host in network.hosts:
        host.cmd('ip route flush root 0/0')
        host.cmd('route add -net', subnet, 'dev', host.defaultIntf())
        host.cmd('route add default gw', rootip)

    return root

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
    topo = Ethernet(config) 
    net = Mininet(topo, host=CPULimitedHost, link=TCLink)
    setLogLevel('info')
    root = connectToInternet(net)
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
    stopNAT(root)
    net.stop()
