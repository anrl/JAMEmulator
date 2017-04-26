#!/usr/bin/python
import os
import pwd
import grp
import inspect
import shutil
import networkx as nx

from sys import argv, exit
from yaml import dump
from geopy.distance import vincenty

def setFilePerms(path):
    uid = pwd.getpwnam("quagga").pw_uid
    gid = grp.getgrnam("quagga").gr_gid
    os.chown(path, uid, gid)


""" Calculate the propagation delay(ms) between nodes 
    based on their geographical location """
def getDelay(node1, node2): 
    if (not "Latitude" in node1 or not "Longitude" in node1): return 0
    if (not "Latitude" in node2 or not "Longitude" in node2): return 0
    loc1 = (node1["Latitude"], node1["Longitude"])
    loc2 = (node2["Latitude"], node2["Longitude"])
    distance = vincenty(loc1, loc2).kilometers
    return float(distance) / (0.68 * 299.792458)


"""Takes an integer and encodes it as a MAC substring"""
def mac(integer):
    if (isinstance(integer, basestring)):
        integer = int(integer)
    if (integer > 255):
        raise ValueError("Cannot encode values larger than 255")
    encoding = str(hex(integer))
    
    if (integer < 16):
        return "0" + encoding[2:]
    else:
        return encoding[2:]


"""Takes a router's name and coverts it to a bgp id"""
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

        if (node2 == "s0" or node2["name"][0] == "h"): continue    
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
        # Setup route server separately
        if (router["name"] == "rs"): continue
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
        print "usage: sudo python jambuilder.py input output"
        exit()
    script, fileIn, fileOut = argv 
    
    if not fileIn.endswith(".gml"):
        print "support for gml formatted graphs only"
        exit()
    graph = nx.read_gml(fileIn, label="id")
    yaml = dict()
    yaml.update({"device":[], "switch":[], "router":[], "link":[]})
    # Add global switch
    yaml["switch"].append({"name":"s0"})

    for node in graph.nodes():
        if (node > 254):
            raise RuntimeError("Topologies with more than 255" 
                               + "nodes are not supported")
        host = "h" + str(node)
        router = "r" + str(node)
        subnet = str(node)
        yaml["device"].append({"name": host,
                               "cmd": [
                                    "route add -net 172.0.0.0 " 
                                    + "netmask 255.255.0.0 "
                                    + "gw 10.0." + subnet  + ".1 "
                                    + "dev " + host + "-eth0",

                                    "route add -net 10.0.0.0 "
                                    + "netmask 255.255.0.0 "
                                    + "gw 10.0." + subnet  + ".1 "
                                    + "dev " + host + "-eth0"
                               ]})
        yaml["router"].append({"name": router,  
                               "loIP": "10.0." + subnet + ".0/24"})
        # Add a link to connect host to router
        yaml["link"].append({
            "node1": {"name": router,
                      "interface": router + "-eth0",
                      "ip": "10.0." + subnet + ".1/24",
                      "mac": "00:00:00:00:00:" + mac(node) + ":01"},
            "node2": {"name": host,
                      "interface": host + "-eth0", 
                      "ip": "10.0." + subnet + ".2/24", 
                      "mac": "00:00:00:00:00:" + mac(node) + ":02"} 
        })

    numintf = {}
    subnetCount = 0
    for edge in graph.edges():
        if (subnetCount > 65025):
            raise RuntimeError("Topologies with more than 65025 subnets are "
                               + "not supported")
        router1 = "r" + str(edge[0])
        router2 = "r" + str(edge[1])
        
        if router1 in numintf: numintf[router1] += 1 
        else: numintf[router1] = 1

        if router2 in numintf: numintf[router2] += 1 
        else: numintf[router2] = 1 

        subnet = str(subnetCount / 255) + "." + str(subnetCount % 255) 
        delay = getDelay(graph.node[edge[0]],graph.node[edge[1]]) / 2
        yaml["link"].append({
            "node1": {"name": router1,
                      "interface": router1 + "-eth" + str(numintf[router1]),
                      "ip": "172." + subnet + ".1/24", 
                      "mac": "ff:00:00:" 
                             + mac(subnetCount / 255) + ":" 
                             + mac(subnetCount % 255) + ":01"}, 
            "node2": {"name": router2,
                      "interface": router2 + "-eth" + str(numintf[router2]),
                      "ip": "172." + subnet + ".2/24", 
                      "mac": "ff:00:00:" 
                             + mac(subnetCount / 255) + ":" 
                             + mac(subnetCount % 255) + ":02"},
            "delay": (str(delay) + "ms")
        })
        subnetCount += 1
    # Connect all other routers to the global switch
    for router in yaml["router"]:
        if (router["name"] == "rs"): continue
        name = router["name"]
        yaml["link"].append({
            "node1": {"name": name,
                      "interface": name + "-eth" + str(numintf[name] + 1), 
                      "ip": "172.0.254." + name[1:] + "/24", 
                      "mac": "ff:ff:00:00:00:" + mac(name[1:])}, 
            "node2": "s0"
        })
    createQuaggaConfigs(yaml)
    dump(yaml, open(fileOut, "w"), default_flow_style=False)