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
    host1 = net.addHost('h1', ip="191.168.1.1", mac='00:00:00:00:00:01')
    host2 = net.addHost('h2', ip="191.168.1.2", mac='00:00:00:00:00:02')
    host3 = net.addHost('h3', ip="191.168.1.3", mac='00:00:00:00:00:03')
    host4 = net.addHost('h4', ip="192.168.1.4", mac='00:00:00:00:00:04')
    host5 = net.addHost('h5', ip="191.168.1.4", mac='00:00:00:00:00:05')
    host6 = net.addHost('h6', ip="191.168.1.6", mac='00:00:00:00:00:09')

    # tenant 2
    host7 = net.addHost('h7', ip="191.168.1.1", mac='00:00:00:00:00:0A')
    host8 = net.addHost('h8', ip="191.168.1.2", mac='00:00:00:00:00:0B')
    host9 = net.addHost('h9', ip="191.168.1.3", mac='00:00:00:00:00:0C')

    # switch
    switch1 = net.addSwitch('s1', ip="191.168.2.1", datapath='user')
    switch2 = net.addSwitch('s2', ip="191.168.2.2", datapath='user')
    switch3 = net.addSwitch('s3', ip="192.168.2.1", datapath='user')
    switch4 = net.addSwitch('s4', ip="191.168.2.3", datapath='user')
    switch5 = net.addSwitch('s5', ip="191.168.2.4", datapath='user')

    # gateway
    gateway1 = net.addSwitch('g1', ip="191.1.1.1", dpid='A')
    gateway2 = net.addSwitch('g2', ip="192.1.1.1", dpid='B')
    gateway1_ = net.addSwitch('g1_', ip="191.1.1.1", dpid='E')
    gateway2_ = net.addSwitch('g2_', ip="192.1.1.1", dpid='F')


    # host - switch
    # tenant 1
    net.addLink(host1, switch1, port1=1, port2=1, cls=TCLink, bw=default_hs_bw)
    net.addLink(host2, switch1, 1, 2, cls=TCLink, bw=default_hs_bw)
    net.addLink(host3, switch2, 1, 1, cls=TCLink, bw=default_hs_bw)
    net.addLink(host4, switch3, 1, 1, cls=TCLink, bw=default_hs_bw)
    net.addLink(host5, switch4, 1, 1, cls=TCLink, bw=default_hs_bw)
    net.addLink(host6, switch5, 1, 3, cls=TCLink, bw=default_hs_bw)

    # tenant 2
    net.addLink(host7, switch1, 1, 6, cls=TCLink, bw=default_hs_bw)
    net.addLink(host8, switch1, 1, 7, cls=TCLink, bw=default_hs_bw)
    net.addLink(host9, switch4, 1, 3, cls=TCLink, bw=default_hs_bw)


    # switch - switch
    net.addLink(switch1, switch2, 3, 2, cls=TCLink, bw=default_ss_bw)
    net.addLink(switch2, switch4, 4, 2, cls=TCLink, bw=default_ss_bw)
    net.addLink(switch1, switch5, 5, 1, cls=TCLink, bw=default_ss_bw)
    net.addLink(switch2, switch5, 5, 2, cls=TCLink, bw=default_ss_bw)

    # switch - gateway
    net.addLink(switch1, gateway1, 4, 2, cls=TCLink, bw=default_gs_bw)
    net.addLink(switch2, gateway1, 3, 1, cls=TCLink, bw=default_gs_bw)
    net.addLink(switch3, gateway2, 2, 1, cls=TCLink, bw=default_gs_bw)
    net.addLink(switch1, gateway1_, 8, 2, cls=TCLink, bw=default_gs_bw)
    net.addLink(switch3, gateway2_, 3, 1, cls=TCLink, bw=default_gs_bw)
    net.addLink(switch5, gateway1_, 4, 3, cls=TCLink, bw=default_gs_bw)



    # gateway - gateway
    net.addLink(gateway1, gateway2, 3, 2)
    net.addLink(gateway1_, gateway1, 1, 4)
    net.addLink(gateway1_, gateway2_, 4, 3)
    net.addLink(gateway2, gateway2_, 3, 2)

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