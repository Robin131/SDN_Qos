from mininet.topo import Topo
from mininet.nodelib import NAT



class MyTopo(Topo):

    def build(self):
        self.hostNum = 5
        self.switchNum = 6
        self.addTopo()



    def addTopo(self):
        default_hs_bw = 10
        default_ss_bw = 10
        default_gs_bw = 10
        default_ng_bw = 10

        host1 = self.addHost('h1', ip="191.168.1.1")
        host2 = self.addHost('h2', ip="191.168.1.2")
        host3 = self.addHost('h3', ip="191.168.1.3")
        host4 = self.addHost('h4', ip="192.168.1.4")
        host5 = self.addHost('h5', ip="191.168.1.4")

        switch1 = self.addSwitch('s1', ip="191.168.2.1", datapath='user')
        switch2 = self.addSwitch('s2', ip="191.168.2.2", datapath='user')
        switch3 = self.addSwitch('s3', ip="192.168.2.1", datapath='user')
        switch4 = self.addSwitch('s4', ip="191.168.2.3", datapath='user')

        gateway1 = self.addSwitch('g1', ip="191.1.1.1", dpid='A')
        gateway2 = self.addSwitch('g2', ip="192.1.1.1", dpid='B')

        nat1 = self.addNode('n1', cls=NAT, ip='191.0.0.1', inNamespace=False)
        nat2 = self.addNode('n2', cls=NAT, ip='192.0.0.1', inNamespace=False)

        # host - switch
        self.addLink(host1, switch1, port1=1, port2=1, bw=default_hs_bw)
        self.addLink(host2, switch1, port1=1, port2=2, bw=default_hs_bw)
        self.addLink(host3, switch2, port1=1, port2=1, bw=default_hs_bw)
        self.addLink(host4, switch3, port1=1, port2=1, bw=default_hs_bw)
        self.addLink(host5, switch4, port1=1, port2=1, bw=default_hs_bw)

        # switch - switch
        self.addLink(switch1, switch2, port1=3, port2=2, bw=default_ss_bw)
        self.addLink(switch2, switch4, port1=4, port2=2, bw=default_ss_bw)

        # switch - gateway
        self.addLink(switch1, gateway1, port1=4, port2=2, bw=default_gs_bw)
        self.addLink(switch2, gateway1, port1=3, port2=1, bw=default_gs_bw)
        self.addLink(switch3, gateway2, port1=2, port2=1, bw=default_gs_bw)

        # gateway - gateway
        self.addLink(gateway1, gateway2, port1=3, port2=2, bw=default_gs_bw)

        # gateway - NAT
        self.addLink(gateway1, nat1, port1=5, port2=1, bw=default_ng_bw)
        self.addLink(gateway2, nat2, port1=4, port2=1, bw=default_ng_bw)


topos = {'mytopo': (lambda: MyTopo())}