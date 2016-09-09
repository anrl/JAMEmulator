from mininet.topo import Topo

class Ethernet(Topo):

    def build(self, config, isWiFi=True):
        if ('cloud' in config): 
            for i in config['cloud']:
                cpu = i['cpu'] if 'cpu' in i else 1.0
                self.addHost(i['name'], cpu=cpu)
        if ('fog' in config): 
            for i in config['fog']:
                cpu = i['cpu'] if 'cpu' in i else 1.0
                self.addHost(i['name'], cpu=cpu)
        if ('device' in config):
            for i in config['device']:
                cpu = i['cpu'] if 'cpu' in i else 1.0
                self.addHost(i['name'], cpu=cpu)
        if ('switch' in config):
            for i in config['switch']:
                self.addSwitch(i['name'])
        if ('link' in config):
            for i in config['link']:
                bw = i['bw'] if 'bw' in i else 100
                delay = i['delay'] if 'delay' in i else '0ms'
                loss = i['loss'] if 'loss' in i else 0
                self.addLink(i['node1'], i['node2'], bw=bw, delay=delay, loss=loss)