#!/usr/bin/python

from sys import argv, exit
import networkx as nx
from yaml import dump
from geopy.distance import vincenty

def getDelay(node1, node2): 
    if (not "Latitude" in node1 or not "Longitude" in node1): return 0
    if (not "Latitude" in node2 or not "Longitude" in node2): return 0
    loc1 = (node1["Latitude"], node1["Longitude"])
    loc2 = (node2["Latitude"], node2["Longitude"])
    distance = vincenty(loc1, loc2).kilometers
    return float(distance) / (0.68 * 299.792458)

if __name__ == '__main__':    
    if len(argv) < 3: 
        print "usage: python graph2yaml.py input output"
        exit()
    script, fileIn, fileOut = argv 
    if not fileIn.endswith(".gml"):
        print "support for gml formatted graphs only"
        exit()
    graph = nx.read_gml(fileIn, label='id')
    yaml = dict()
    yaml.update({"device":[], "switch":[], "link":[]})
    
    for node in graph.nodes():
        yaml["device"].append({"name":"dev" + str(node)})
        yaml["switch"].append({"name":"s" + str(node)})
        yaml["link"].append({"node1":"dev" + str(node), "node2":"s" + str(node)})
    for edge in graph.edges():
        delay = getDelay(graph.node[edge[0]],graph.node[edge[1]])
        yaml["link"].append({"node1":"s" + str(edge[0]), 
                             "node2":"s" + str(edge[1]),
                             "delay": (str(delay) + "ms")})
    dump(yaml, open(fileOut, "w"), default_flow_style=False)
