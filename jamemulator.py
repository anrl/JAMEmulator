#!/usr/bin/python

from sys import argv, exit
from yaml import load

from mininet.log import setLogLevel
from mininet.node import CPULimitedHost, OVSController, OVSKernelSwitch
from mininet.link import TCLink
from mininet.clean import cleanup

from mininext.cli import CLI
from mininext.net import MiniNExT
from mininext.node import Node

from jamtopo import JAMTopo
from console import ConsoleApp

def setupIntfs(net, config):
    if ("link" in config):
        for i in config["link"]:
            node1 = i["node1"]
            node2 = i["node2"]  

            if (isinstance(node1, dict)):
                n1 = net.get(node1["name"])
                if ("ip" in node1):
                    n1.setIP(node1["ip"], intf=node1["interface"])
                if ("mac" in node1):
                    n1.setMAC(node1["mac"], intf=node1["interface"])
            
            if (isinstance(node2, dict)): 
                n2 = net.get(node2["name"])
                if ("ip" in node2):
                    n2.setIP(node2["ip"], intf=node2["interface"])
                if ("mac" in node2):
                    n2.setMAC(node2["mac"], intf=node2["interface"])


def startNAT(root, inetIntf="eth0", subnet="10.0/8"):
    """Start NAT/forwarding between Mininet and external network
       root: node to access iptables from
       inetIntf: interface for internet access
       subnet: Mininet subnet (default 10.0/8)="""

    # Identify the interface connecting to the mininet network
    localIntf =  root.defaultIntf()
    # Flush any currently active rules
    root.cmd("iptables -F")
    root.cmd("iptables -t nat -F")
    # Create default entries for unmatched traffic
    root.cmd("iptables -P INPUT ACCEPT")
    root.cmd("iptables -P OUTPUT ACCEPT")
    root.cmd("iptables -P FORWARD DROP")
    # Configure NAT
    root.cmd("iptables -I FORWARD -i", localIntf, "-d", subnet, "-j DROP")
    root.cmd("iptables -A FORWARD -i", localIntf, "-s", subnet, "-j ACCEPT")
    root.cmd("iptables -A FORWARD -i", inetIntf, "-d", subnet, "-j ACCEPT")
    root.cmd("iptables -t nat -A POSTROUTING -o ", inetIntf, "-j MASQUERADE")
    # Instruct the kernel to perform forwarding
    root.cmd("sysctl net.ipv4.ip_forward=1")


def stopNAT(root):
    """Stop NAT/forwarding between Mininet and external network"""
    # Flush any currently active rules
    root.cmd("iptables -F")
    root.cmd("iptables -t nat -F")
    # Instruct the kernel to stop forwarding
    root.cmd("sysctl net.ipv4.ip_forward=0")


def fixNetworkManager(root, intf):
    """Prevent network-manager from messing with our interface,
       by specifying manual configuration in /etc/network/interfaces
       root: a node in the root namespace (for running commands)
       intf: interface name"""

    cfile = "/etc/network/interfaces"
    line = "\niface %s inet manual\n" % intf
    config = open(cfile).read()
    if (line) not in config:
        print "*** Adding", line.strip(), "to", cfile
        with open(cfile, "a") as f:
            f.write(line)
        # Probably need to restart network-manager to be safe -
        # hopefully this won"t disconnect you
        root.cmd("service network-manager restart")

def connectToInternet(network, switch, rootip="10.254", subnet="10.0/8"):
    """Connect the network to the internet
       switch: switch to connect to root namespace
       rootip: address for interface in root namespace
       subnet: Mininet subnet"""
    switch = network.get(switch)
    prefixLen = subnet.split("/")[1]

    # Create a node in root namespace
    root = Node("root", inNamespace=False)
    # Prevent network-manager from interfering with our interface
    fixNetworkManager(root, "root-eth0")
    # Create link between root NS and switch
    link = network.addLink(root, switch)
    link.intf1.setIP(rootip, prefixLen)
    # Start network that now includes link to root namespace
    network.start()
    # Start NAT and establish forwarding
    startNAT(root)

    # Establish routes from end hosts
    for host in network.hosts:
        host.cmd("ip route flush root 0/0")
        host.cmd("route add -net", subnet, "dev", host.defaultIntf())
        host.cmd("route add default gw", rootip)
    return root

def runCmds(net, config):
    groups = ["cloud", "fog", "device", "router"]
    for i in groups:
        if (i in config):
            for j in config[i]:
                if ("cmd" in j):
                    cmdList = j["cmd"]
                else: continue
                # Get the host on which to run the commmand 
                host = net.get(j["name"])
                # Check if the command list is not a list
                if (not isinstance(cmdList, list)):
                    host.cmd(cmdList)
                # Otherwise run all the commands in the list
                else: 
                    for c in cmdList:
                        host.cmd(c)

if __name__ == "__main__":
    if len(argv) < 2:
        print "usage: sudo python emulator.py config"
        exit()
    script, filename = argv
    data = open(filename)
    config = load(data)
    setLogLevel("info")
    try:
        net = MiniNExT(JAMTopo(config), controller=OVSController, link=TCLink,
                       host=CPULimitedHost, switch=OVSKernelSwitch)
        setupIntfs(net, config)
        net.start()
        # Configure and start NAT connectivity
        # rootnode = connectToInternet(net, config["switch"][0]["name"])
        # print "*** Hosts are running and should have internet connectivity"
        runCmds(net, config)
        print "*** Type 'exit' or control-D to shut down network"
        CLI(net)
        # Shut down NAT
        # stopNAT(rootnode)
        net.stop()
    except:
        cleanup()
        raise