from mininet.topo import Topo


class MyTopo(Topo):

    def __init__(self):
        Topo.__init__(self)

        host1 = self.addHost('h1', ip="191.168.1.1")
        host2 = self.addHost('h2', ip="191.168.1.2")
        host3 = self.addHost('h3', ip="191.168.1.3")
        host4 = self.addHost('h4', ip="192.168.1.4")

        switch1 = self.addSwitch('s1', ip="191.168.2.1", datapath='user')
        switch2 = self.addSwitch('s2', ip="191.168.2.2", datapath='user')
        switch3 = self.addSwitch('s3', ip="192.168.2.1", datapath='user')

        gateway1 = self.addSwitch('g1', ip="176.168.1.1", dpid='A')

        # host - switch
        self.addLink(host1, switch1, 1, 1)
        self.addLink(host2, switch1, 1, 2)
        self.addLink(host3, switch2, 1, 1)
        self.addLink(host4, switch3, 1, 1)

        # switch - switch
        self.addLink(switch1, switch2, 3, 2)

        # switch - gateway
        self.addLink(switch1, gateway1, 4, 2)
        self.addLink(switch2, gateway1, 3, 1)
        self.addLink(switch3, gateway1, 2, 3)


# h1 h2 h3 belongs to same subnet 191
# h4 belongs to subnet 192

#  Datacenter A
#  h1----s1-----g1-------Datacenter b
#       --  -   -  --
#     --     -  -    --
#  h2-        -s2      --s3 --------h4
#               -
#               -
#               h3



topos = {'mytopo': (lambda: MyTopo())}

