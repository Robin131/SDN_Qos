from mininet.topo import Topo
from mininet.nodelib import NAT



class MyTopo(Topo):

    def build(self):
        self.hostNum = 5
        self.switchNum = 6
        self.addTopo()



    def addTopo(self):

        # DA :
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
        self.addLink(host1, switch1, 1, 1)
        self.addLink(host2, switch1, 1, 2)
        self.addLink(host3, switch2, 1, 1)
        self.addLink(host4, switch3, 1, 1)
        self.addLink(host5, switch4, 1, 1)

        # switch - switch
        self.addLink(switch1, switch2, 3, 2)
        self.addLink(switch2, switch4, 4, 2)

        # switch - gateway
        self.addLink(switch1, gateway1, 4, 2)
        self.addLink(switch2, gateway1, 3, 1)
        self.addLink(switch3, gateway2, 2, 1)

        # gateway - gateway
        self.addLink(gateway1, gateway2, 3, 2)

        # gateway - NAT
        self.addLink(gateway1, nat1, 5, 1)
        self.addLink(gateway2, nat2, 4, 1)


        # DB :
        host8 = self.addHost('h8', ip="192.168.1.8")
        host6 = self.addHost('h6', ip="192.168.1.6")
        host7 = self.addHost('h7', ip="193.168.1.7")

        switch5 = self.addSwitch('s5', ip="193.168.2.1", datapath='user')
        switch6 = self.addSwitch('s6', ip="192.168.2.2", datapath='user')

        gateway3 = self.addSwitch('g3', ip="192.1.1.2", dpid='C')
        gateway4 = self.addSwitch('g4', ip="193.1.1.1", dpid='D')

        # host - switch
        self.addLink(switch5, host7, 1, 1)
        self.addLink(switch6, host8, 2, 1)
        self.addLink(switch6, host6, 1, 1)

        # switch - switch
        self.addLink(switch5, switch6, 2, 4)

        # switch - gateway
        self.addLink(switch5, gateway4, 3, 1)
        self.addLink(switch6, gateway3, 3, 1)

        # gateway - gateway
        self.addLink(gateway3, gateway4, 2, 2)

        # gateway - NAT



topos = {'mytopo': (lambda: MyTopo())}

