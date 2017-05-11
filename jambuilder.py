#!/usr/bin/python
import os
import pwd
import grp
import inspect
import shutil
import networkx as nx
import numpy as np

from sys import argv, exit
from yaml import dump
from geopy.distance import vincenty
from macfactory import MACFactory
from ipv4factory import IPV4Factory


def printUsage():
    print "usage: sudo python " + argv[0] + " input output [options]"
    print "    -host n:     the number of hosts on each local network"
    print "    -host m,s:   the number of host on each local network will be"
    print "                 normally distributed with mean m and standard" 
    print "                 deviation s"
    print "    -cloud n:    the number of cloud nodes in the network"
    print "    -fog n:      the number of fog nodes in the network" 


def setFilePerms(path):
    uid = pwd.getpwnam("quagga").pw_uid
    gid = grp.getgrnam("quagga").gr_gid
    os.chown(path, uid, gid)


def hostNumGen(args):
    params = args.split(",")

    if (len(params) == 1):
        def uniform(): 
            n = int(args[0])
            if (n < 0): 
                return 0
            elif (n > 253): 
                return 253
            else:
                return n
        return uniform
    else:
        def normal():
            mu, sigma = params
            sample = np.random.normal(float(mu), float(sigma), 1)[0]
            if (sample < 0): 
                return 0
            elif (sample > 253): 
                return 253
            else: 
                return int(round(sample))
        return normal


""" Calculate the propagation delay(ms) between nodes 
    based on their geographical location """
def getDelay(node1, node2): 
    if (not "Latitude" in node1 or not "Longitude" in node1): 
        return 0
    if (not "Latitude" in node2 or not "Longitude" in node2): 
        return 0
    loc1 = (node1["Latitude"], node1["Longitude"])
    loc2 = (node2["Latitude"], node2["Longitude"])
    distance = vincenty(loc1, loc2).kilometers
    return float(distance) / (0.68 * 299.792458)


""" Takes a router's name and coverts it to a bgp id """
def bgpid(name):
    bgpnum = int(name[1:]) + 1
    return str(bgpnum) + "00" 


def setupVtysh(router, configPath):
    file = open(configPath + "debian.conf", "w")
    file.write("vtysh_enable=yes\n")
    file.write('zebra_options=" --daemon -A 127.0.0.1"\n')
    file.write('bgpd_options=" --daemon -A 127.0.0.1"\n')
    file.close
    setFilePerms(configPath + "debian.conf")

    file = open(configPath + "vtysh.conf", "w")
    file.write("hostname " + router["name"] + "\n")
    file.write("username root nopassword")
    file.close
    setFilePerms(configPath + "vtysh.conf")


def setupZebra(configPath):
    file = open(configPath + "zebra.conf", "w")
    file.write("! Empty config file required to get Zebra to start")
    file.close
    setFilePerms(configPath + "zebra.conf")


def setupBGPD(router, configPath, yaml):    
    file = open(configPath + "bgpd.conf", "w")
    # path logfile for this daemon (BGPD)
    file.write("log file /var/log/quagga/bgpd.log\n\n")
    # the password to use for telnet authentication
    file.write("password bgpuser\n\n")
    # this routers AS number and BGP ID
    file.write("router bgp " + bgpid(router["name"]) +"\n")
    file.write(" bgp router-id " + router["loIP"][:-4] + "2\n")
    # the network this router will advertise
    file.write(" network " + router["loIP"] + "\n\n")

    for i in yaml["link"]:
        node1 = i["node1"]
        node2 = i["node2"]
        # If the link is local then skip it
        if (not "name" in node2 and node2[0] == "s"): 
            continue
        if (node1["name"] == router["name"]): 
            ip = node2["ip"]
            bgpID = bgpid(node2["name"])
        elif (i["node2"]["name"] == router["name"]): 
            ip = node1["ip"]
            bgpID = bgpid(node1["name"])
        else: continue
        file.write(" neighbor " + ip[:-3] + " remote-as " + bgpID + " \n")
        file.write(" neighbor " + ip[:-3] + " description Virtual-AS-" 
                   + bgpID + "\n")
        file.write(" network " + ip + "\n\n")

    file.close
    setFilePerms(configPath + "bgpd.conf")


def createQuaggaConfigs(yaml):
    # Directory where this file / script is located
    selfPath = os.path.dirname(os.path.abspath(
    inspect.getfile(inspect.currentframe())))
    # Clean the configs directory
    shutil.rmtree(selfPath + "/configs/")
    
    for router in yaml["router"]:
        # Path configurations for mounts
        configPath = selfPath + "/configs/" + router["name"] + "/"
        os.makedirs(configPath)

        # This file tells the quagga package which daemons to start.
        file = open(configPath + "daemons", "w")
        file.write("zebra=yes\n")
        file.write("bgpd=yes\n")
        file.write("ospfd=no\n")
        file.write("ospf6d=no\n")
        file.write("ripd=no\n")
        file.write("ripngd=no\n")
        file.write("isisd=no\n")
        file.close

        uid = pwd.getpwnam("quagga").pw_uid
        gid = grp.getgrnam("quagga").gr_gid
        os.chown(configPath + "daemons", uid, gid)

        setupZebra(configPath)
        setupBGPD(router, configPath, yaml)
        setupVtysh(router, configPath)


if __name__ == '__main__':
    if len(argv) < 3: 
        printUsage()
        exit()
    fileIn = argv[1]
    fileOut = argv[2]
    
    if not fileIn.endswith(".gml"):
        print "support for gml formatted graphs only"
        exit()
    # Set default values
    getNumHosts = hostNumGen("1")
    numClouds = 0
    numFogs = 0
    # Parse any extra command line arguments and update the default
    # values if specified
    for i in range (3, len(argv)):
        if (argv[i] == "-host" and len(argv) >= i + 2):
            getNumHosts = hostNumGen(argv[i + 1])
        elif (argv[i] == "-cloud" and len(argv) >= i + 2):
            numClouds = int(argv[i + 1])
        elif (argv[i] == "-fog" and len(argv) >= i + 2):
            numFogs = int(argv[i + 1])
    # Parse graph file and get the total number of nodes
    graph = nx.read_gml(fileIn, label="id")
    totalNodes = nx.number_of_nodes(graph)
  
    if (totalNodes > 254):
            raise RuntimeError("Topologies with more than 254 " 
                               + "nodes are not supported")
    if (totalNodes < (numClouds + numFogs)):
        raise RuntimeError("The number of cloud and fog nodes cannot "
                           + "be greater than the total number of "
                           + "nodes in the network")
    # Create a list of each node and its degree in the graph
    nodeDegrees = []
    for node in nx.nodes(graph):
        nodeDegrees.append((node,graph.degree(node)))
    # Sort the list by degree in descending order
    nodeDegrees.sort(key=lambda tup: tup[1], reverse=True)
    # Create the yaml object for the configuration file with the 
    # default lists
    yaml = dict()
    yaml.update({"device":[], "switch":[], "router":[], "link":[]})
    # If the topology has clouds, add a corresponding list to the yaml
    if (numClouds > 0):
        yaml.update({"cloud": []})
    # If the topology has fogs, add a corresponding list to the yaml
    if (numFogs > 0):
        yaml.update({"fog": []})
    # Add global switch
    yaml["switch"].append({"name":"s0-gbl"})
    # Create MAC address generator
    macfact = MACFactory()
    macfact.setSeed("ff:ff:00:00:00:00")
    # Create IPV4 address generator
    ipv4fact = IPV4Factory()
    ipv4fact.setSeed("10.0.0.0")
    # Generate IP for first local network
    loIP = ipv4fact.generate(0)

    while(len(nodeDegrees) > 0):
        # Create the clouds using nodes at the center of the network
        if (numClouds > 0):
            node = nodeDegrees.pop(0)
            group = yaml["cloud"]
            cpu = 0.10
            bw = 100
            numClouds -= 1
        # Create the fogs using nodes at the edge of the network
        elif (numFogs > 0):
            node = nodeDegrees.pop(-1)
            group = yaml["fog"]
            numFogs -= 1
            cpu = 0.05
            bw = 50
        else:
            node = nodeDegrees.pop(0)
            group = yaml["device"]
            cpu = 0.01
            bw = 10
        # Add router and specify its local network
        router = "r" + str(node[0])
        routerIP = ipv4fact.generate()       
        yaml["router"].append({"name": router,  
                               "loIP":  loIP + "/24"})
        # Add a local switch and connect it to the router
        switch = "s0-" + router
        yaml["switch"].append({"name": switch})
        yaml["link"].append({
            "node1": {"name": router,
                      "interface": router + "-eth0",
                      "ip": routerIP + "/24",
                      "mac": macfact.generate()},
            "node2": switch,
            "bw": bw
        })
        nh = getNumHosts()
        for i in range(0,nh):
            host = "h" + str(i) + "-" + router
            hostIP = ipv4fact.generate()
            # Add host and update its route table
            group.append({"name": host,
                         "cpu": cpu,
                         "cmd": [
                             "route add -net 172.0.0.0 " 
                             + "netmask 255.255.0.0 "
                             + "gw " + routerIP + " "
                             + "dev " + host + "-eth0",

                             "route add -net 10.0.0.0 "
                             + "netmask 255.255.0.0 "
                             + "gw " + routerIP + " "
                             + "dev " + host + "-eth0"
                       ]})
            # Add a link to connect host to the local switch
            yaml["link"].append({
                "node1": {"name": host,
                          "interface": host + "-eth0",
                          "ip": hostIP + "/24", 
                          "mac": macfact.generate()},
                "node2": switch,
                "bw": bw,
            })
        # Generate IP for next local network
        loIP = ipv4fact.generate(256 - nh - 1)

    numintf = {}
    ipv4fact.setSeed("172.0.0.0")
    for edge in graph.edges():
        router1 = "r" + str(edge[0])
        router2 = "r" + str(edge[1])
        # Keep track of the number of interfaces on each router
        if (router1 in numintf): 
            numintf[router1] += 1 
        else: 
            numintf[router1] = 1

        if (router2 in numintf): 
            numintf[router2] += 1 
        else: 
            numintf[router2] = 1 
        # Calculate the transmission delay on the link connecting the nodes
        delay = getDelay(graph.node[edge[0]],graph.node[edge[1]])
        # Add the link to the yaml
        yaml["link"].append({
            "node1": {"name": router1,
                      "interface": router1 + "-eth" + str(numintf[router1]),
                      "ip": ipv4fact.generate() + "/24", 
                      "mac": macfact.generate()}, 
            "node2": {"name": router2,
                      "interface": router2 + "-eth" + str(numintf[router2]),
                      "ip": ipv4fact.generate() + "/24", 
                      "mac": macfact.generate()},
            "delay": (str(delay) + "ms")
        })
        # Update IPV4 factory so its ready for next subnet
        ipv4fact.generate(254)
    # Connect all routers to the global switch
    ipv4fact.setSeed("172.0.254.0")
    for router in yaml["router"]:
        name = router["name"]
        yaml["link"].append({
            "node1": {"name": name,
                      "interface": name + "-eth" + str(numintf[name] + 1), 
                      "ip": ipv4fact.generate() + "/24", 
                      "mac": macfact.generate()}, 
            "node2": "s0-gbl"
        })
    createQuaggaConfigs(yaml)
    dump(yaml, open(fileOut, "w"), default_flow_style=False)