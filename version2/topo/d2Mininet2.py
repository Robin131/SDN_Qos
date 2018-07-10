from mininet.cli import CLI
from mininet.log import setLogLevel, info,error
from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.link import TCLink

if __name__ == "__main__":
    default_hs_bw = 10
    default_ss_bw = 10
    default_gs_bw = 10
    default_ng_bw = 10

    setLogLevel("info")
    net = Mininet(switch=OVSSwitch, listenPort = 6633, ipBase='191.0.0.1/4')

    mycontroller = RemoteController("RemoteController")
    net.controllers = [mycontroller]
    net.nameToNode["RemoteController"] = mycontroller

    # host
    # tenant 1
    host1 = net.addHost('h1', ip="191.168.2.1", mac='00:00:00:00:01:01')
    host2 = net.addHost('h2', ip="192.168.2.2", mac='00:00:00:00:01:02')

    # tenant 2
    host3 = net.addHost('h3', ip="191.168.2.1", mac='00:00:00:00:01:03')
    host4 = net.addHost('h4', ip="192.168.2.2", mac='00:00:00:00:01:04')

    # switch
    switch1 = net.addSwitch('s1', ip="191.168.3.1", datapath='user')
    switch2 = net.addSwitch('s2', ip="191.168.3.2", datapath='user')

    # gateway
    gateway1 = net.addSwitch('g1', ip="191.1.1.1", dpid='A')
    gateway2 = net.addSwitch('g2', ip="191.1.1.1", dpid='B')


    # host - switch
    # tenant 1
    net.addLink(host1, switch1, 1, 1, cls=TCLink, bw=default_hs_bw)
    net.addLink(host2, switch2, 1, 1, cls=TCLink, bw=default_hs_bw)

    # tenant 2
    net.addLink(host3, switch1, 1, 2, cls=TCLink, bw=default_hs_bw)
    net.addLink(host4, switch2, 1, 2, cls=TCLink, bw=default_hs_bw)


    # switch - switch
    net.addLink(switch1, switch2, 3, 3, cls=TCLink, bw=default_ss_bw)

    # switch - gateway
    net.addLink(switch1, gateway1, 4, 1, cls=TCLink, bw=default_gs_bw)
    net.addLink(switch1, gateway2, 5, 1, cls=TCLink, bw=default_gs_bw)

    net.addLink(switch2, gateway1, 4, 2, cls=TCLink, bw=default_gs_bw)
    net.addLink(switch2, gateway2, 5, 2, cls=TCLink, bw=default_gs_bw)

    # gateway - gateway
    net.addLink(gateway1, gateway2, 4, 5)

    # # nat
    # net.addNAT(name = 'nat0',
    #            connect = gateway1,
    #            inNamespace = False,
    #            mac='00:00:00:00:00:06').configDefault()
    #
    # net.addNAT(name = 'nat1',
    #            connect = gateway2,
    #            inNamespace = False,
    #            mac='00:00:00:00:00:07').configDefault()

    net.start()
    CLI(net)
    net.stop()