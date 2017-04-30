import inspect
import os
from mininext.topo import Topo
from mininext.services.quagga import QuaggaService

def checkDupEth(config):
    hosts = list()
    nodes = list()
    groups = ["cloud", "fog", "device"]

    for i in groups:
        if (i in config):
            for j in config[i]:
                hosts.append(j["name"])
    if ("link" in config):
        for i in config["link"]:
            nodes.append(i["node1"])
            nodes.append(i["node2"])
    for i in hosts:
        if nodes.count(i) > 1:
            raise RuntimeError("Invalid topology:"
                               + "%s has duplicate eth interface" %i)


class JAMTopo(Topo):
    def __init__(self, config):
        Topo.__init__(self)
        checkDupEth(config)
        groups = ["cloud", "fog", "device"]
        nodes = dict()

        for i in groups:
            if (i in config):
                for j in config[i]: 
                    # Check if the CPU resources available to host are restricted
                    cpu = j["cpu"] if "cpu" in j else 1.0      
                    if ("ip" in j): 
                        self.addHost(j["name"], ip=ip, cpu=cpu)
                    else:
                        self.addHost(j["name"], cpu=cpu)


        if (not "switch" in config or len(config["switch"]) == 0):
            raise RuntimeError("Topology must have at least one switch")
        else:
            for i in config["switch"]:
                self.addSwitch(i["name"])

        if ("router" in config):
            # Directory where this file / script is located"
            selfPath = os.path.dirname(os.path.abspath(
            inspect.getfile(inspect.currentframe())))  # script directory
            # Initialize a service helper for Quagga with default options
            quaggaSvc = QuaggaService(autoStop=False)
            # Path configurations for mounts
            quaggaBaseConfigPath = selfPath + "/configs/"
            
            for i in config["router"]:
                # Create an instance of a host, called a quaggaContainer
                self.addHost(name=i["name"],
                             hostname=i["name"],
                             privateLogDir=True,
                             privateRunDir=True,
                             inMountNamespace=True,
                             inPIDNamespace=True,
                             inUTSNamespace=True)

                # Configure and setup the Quagga service for this node
                quaggaSvcConfig = \
                    {"quaggaConfigPath": quaggaBaseConfigPath + i["name"]}
                self.addNodeService(node=i["name"], service=quaggaSvc,
                                    nodeConfig=quaggaSvcConfig)
        
        if ("link" in config):
            for i in config["link"]:            
                bw = i["bw"] if "bw" in i else 100
                delay = i["delay"] if "delay" in i else "0ms"
                loss = i["loss"] if "loss" in i else 0     

                if isinstance(i["node1"], dict): 
                    name1 = i["node1"]["name"]
                else: 
                    name1 = i["node1"]
                if isinstance(i["node2"], dict): 
                    name2 = i["node2"]["name"]
                else: 
                    name2 = i["node2"]    
                self.addLink(name1, name2, bw=bw, delay=delay, loss=loss)