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
    host1 = net.addHost('h1', ip="191.168.1.10", mac='00:00:00:00:01:00')
    host2 = net.addHost('h2', ip="191.168.1.11", mac='00:00:00:00:02:00')
    host4 = net.addHost('h4', ip="193.168.1.1", mac='00:00:00:00:04:00')

    # tenant 2
    host3 = net.addHost('h3', ip="191.168.1.10", mac='00:00:00:00:03:00')
    host5 = net.addHost('h5', ip="191.168.1.11", mac='00:00:00:00:05:00')

    # switch
    switch1 = net.addSwitch('s1', ip="191.168.2.10", datapath='user')
    switch2 = net.addSwitch('s2', ip="191.168.2.11", datapath='user')
    switch3 = net.addSwitch('s3', ip="191.168.2.12", datapath='user')

    # gateway
    gateway1 = net.addSwitch('g1', ip="191.1.1.2", dpid='C')
    gateway2 = net.addSwitch('g2', ip="193.1.1.1", dpid='D')

    # host - switch
    net.addLink(host1, switch1, port1=1, port2=1, cls=TCLink, bw=default_hs_bw)
    net.addLink(host5, switch1, port1=1, port2=4, cls=TCLink, bw=default_hs_bw)
    net.addLink(host3, switch2, port1=1, port2=2, cls=TCLink, bw=default_hs_bw)
    net.addLink(host2, switch2, port1=1, port2=1, cls=TCLink, bw=default_hs_bw)
    net.addLink(host4, switch3, port1=1, port2=1, cls=TCLink,bw=default_hs_bw)

    # switch - switch
    net.addLink(switch1, switch2, port1=2, port2=3, cls=TCLink, bw=default_ss_bw)

    # switch - gateway
    net.addLink(switch1, gateway1, port1=3, port2=1, cls=TCLink, bw=default_gs_bw)
    net.addLink(switch3, gateway2, port1=2, port2=1, cls=TCLink, bw=default_gs_bw)

    # gateway - gateway
    net.addLink(gateway1, gateway2, 2, 2)
    net.start()
    CLI(net)
    net.stop()