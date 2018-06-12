from mininet.topo import Topo
from mininet.nodelib import NAT



class MyTopo(Topo):

    def build(self):
        self.hostNum = 5
        self.switchNum = 6
        self.addTopo()



    def addTopo(self):
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