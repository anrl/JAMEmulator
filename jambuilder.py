#!/usr/bin/python
import os
import pwd
import grp
import inspect
import networkx as nx

from sys import argv, exit
from yaml import dump
from geopy.distance import vincenty


def getDelay(node1, node2): 
    """Calculate the propagation delay(ms) between nodes 
       based on their geographical location"""
    if (not "Latitude" in node1 or not "Longitude" in node1): return 0
    if (not "Latitude" in node2 or not "Longitude" in node2): return 0
    loc1 = (node1["Latitude"], node1["Longitude"])
    loc2 = (node2["Latitude"], node2["Longitude"])
    distance = vincenty(loc1, loc2).kilometers
    return float(distance) / (0.68 * 299.792458)


def mac(integer):
    if (integer > 255):
        raise ValueError("Cannot encode values larger than 255")
    encoding = str(hex(integer))
    
    if (integer < 16):
        return "0" + encoding[2:]
    else:
        return encoding[2:]

def setupVtysh(router, configPath):
    file = open(configPath + "debian.conf", "w")
    file.write("vtysh_enable=yes\n")
    file.write('zebra_options=" --daemon -A 127.0.0.1"\n')
    file.write('ospfd_options=" --daemon -A 127.0.0.1"\n')
    file.close

    file = open(configPath + "vtysh.conf", "w")
    file.write("hostname " + router + "\n")
    file.write("username root nopassword")
    file.close

    uid = pwd.getpwnam("quagga").pw_uid
    gid = grp.getgrnam("quagga").gr_gid
    os.chown(configPath + "debian.conf", uid, gid)
    os.chown(configPath + "vtysh.conf", uid, gid)


def setupZebra(configPath):
    file = open(configPath + "zebra.conf", "w")
    file.write("! Empty config file required to get Zebra to start")
    file.close

    uid = pwd.getpwnam("quagga").pw_uid
    gid = grp.getgrnam("quagga").gr_gid
    os.chown(configPath + "zebra.conf", uid, gid)


def setupOSPF(router, configPath, yaml):    
    file = open(configPath + "ospfd.conf", "w")
    # path logfile for this daemon (OSPFD)
    file.write("log file /var/log/quagga/ospfd.log\n\n")

    interfaces = []
    for i in yaml["link"]:
        if (i["node1"]["name"] == router): 
            interfaces.append(i["node1"])
        elif (i["node2"]["name"] == router): 
            interfaces.append(i["node2"])

    # setup external connections
    # for i in interfaces:
    #     file.write("interface " + i["interface"] + "\n")
    #     file.write(" ip address " + i["ip"] + "\n")
    #     file.write(" link detect\n\n")
    
    # setup loopback interface
    file.write("interface lo\n")
    # file.write(" ip address 10.0." + router[1:] + ".0/24\n")
    # file.write(" link detect\n\n")

    file.write("router ospf\n")
    for i in interfaces:
        file.write(" network " + i["ip"] + " area 0\n")
    file.write("\n")
    file.write("hostname " + router + "\n\n")
    file.write("line vty\n")
    file.write(" no login\n")
    file.close

    uid = pwd.getpwnam("quagga").pw_uid
    gid = grp.getgrnam("quagga").gr_gid
    os.chown(configPath + "ospfd.conf", uid, gid)


def createQuaggaConfigs(yaml):
    # Directory where this file / script is located
    selfPath = os.path.dirname(os.path.abspath(
    inspect.getfile(inspect.currentframe())))
    
    # Path configurations for mounts
    for router in yaml["router"]:
        configPath = selfPath + "/configs/" + router["name"] + "/"
    
        if not os.path.exists(configPath):
            os.makedirs(configPath)   

        # This file tells the quagga package which daemons to start.
        file = open(configPath + "daemons", "w")
        file.write("zebra=yes\n")
        file.write("bgpd=no\n")
        file.write("ospfd=yes\n")
        file.write("ospf6d=no\n")
        file.write("ripd=no\n")
        file.write("ripngd=no\n")
        file.write("isisd=no\n")
        file.close

        uid = pwd.getpwnam("quagga").pw_uid
        gid = grp.getgrnam("quagga").gr_gid
        os.chown(configPath + "daemons", uid, gid)

        setupZebra(configPath)
        setupOSPF(router["name"], configPath, yaml)
        setupVtysh(router["name"], configPath)


if __name__ == '__main__':    
    if len(argv) < 3: 
        print "usage: sudo python jambuilder.py input output"
        exit()
    script, fileIn, fileOut = argv 
    
    if not fileIn.endswith(".gml"):
        print "support for gml formatted graphs only"
        exit()
    graph = nx.read_gml(fileIn, label="id")
    yaml = dict()
    yaml.update({"device":[], "switch":[], "router":[], "link":[]})
    yaml["switch"].append({"name":"s0"})

    for node in graph.nodes():
        if (node > 254):
            raise RuntimeError("Topologies with more than 255" 
                               + "nodes are not supported")
        host = "h" + str(node)
        router = "r" + str(node)
        subnet = str(node)
        yaml["device"].append({"name": host})
        yaml["router"].append({"name": router,  
                               "loIP": "10.0." + subnet + ".0/24"})
        yaml["link"].append({
            "node1": {"name": host,
                      "interface": host + "-eth0", 
                      "ip": "10.0." + subnet + ".1/24", 
                      "mac": "00:00:00:00:00:" + mac(node) + ":01"}, 
            "node2": {"name": router,
                      "interface": router + "-eth0",
                      "ip": "10.0." + subnet + ".2/24",
                      "mac": "00:00:00:00:00:" + mac(node) + ":02"}
        })

    numintf = {}
    counter = 0
    for edge in graph.edges():
        if (counter > 65025):
            raise RuntimeError("Topologies with more than 65025 links are "
                               + "not supported")
        router1 = "r" + str(edge[0])
        router2 = "r" + str(edge[1])
        
        if router1 in numintf: numintf[router1] += 1 
        else: numintf[router1] = 1

        if router2 in numintf: numintf[router2] += 1 
        else: numintf[router2] = 1 

        subnet = str(counter / 255) + "." + str(counter % 255) 
        delay = getDelay(graph.node[edge[0]],graph.node[edge[1]])
        yaml["link"].append({
            "node1": {"name": router1,
                      "interface": router1 + "-eth" + str(numintf[router1]),
                      "ip": "172." + subnet + ".0/24", 
                      "mac": "ff:00:00:00:" 
                             + mac(counter / 255) + ":" 
                             + mac(counter % 255) + ":00"}, 
            "node2": {"name": router2,
                      "interface": router2 + "-eth" + str(numintf[router2]),
                      "ip": "172." + subnet + ".1/24", 
                      "mac": "ff:00:00:00:" 
                             + mac(counter / 255) + ":" 
                             + mac(counter % 255) + ":01"},
            "delay": (str(delay) + "ms")
        })
        counter += 1
    createQuaggaConfigs(yaml)
    dump(yaml, open(fileOut, "w"), default_flow_style=False)