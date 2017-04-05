from mininext.topo import Topo

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
            raise RuntimeError("Invalid topology:"
                               + "%s has duplicate eth" %i)

class JAMTopo(Topo):

    def __init__(self, config):
        Topo.__init__(self)
        checkDupEth(config)
        groups = ['cloud', 'fog', 'device']
        nodes = dict()

        for i in groups:
            if (i in config):
                for j in config[i]:
                    cpu = j['cpu'] if 'cpu' in j else 1.0
                    nodes[j['name']] = self.addHost(j['name'], cpu=cpu)
        if ('switch' in config):
            for i in config['switch']:
                nodes[i['name']] = self.addSwitch(i['name'])
        else:
            raise RuntimeError("Topology must have at least one switch")
        if ('link' in config):
            for i in config['link']:
                bw = i['bw'] if 'bw' in i else 100
                delay = i['delay'] if 'delay' in i else '0ms'
                loss = i['loss'] if 'loss' in i else 0
                self.addLink(nodes[i['node1']], nodes[i['node2']],
                             bw=bw, delay=delay, loss=loss)
