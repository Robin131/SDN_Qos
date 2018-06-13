from mininet.cli import CLI
from mininet.log import setLogLevel, info,error
from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch

if __name__ == "__main__":
    setLogLevel("info")
    net = Mininet(switch=OVSSwitch, listenPort = 6633, ipBase='191.0.0.1/4')

    mycontroller = RemoteController("RemoteController")
    net.controllers = [mycontroller]
    net.nameToNode["RemoteController"] = mycontroller

    # host
    host1 = net.addHost('h1', ip="191.168.1.1", mac='00:00:00:00:00:01')
    host2 = net.addHost('h2', ip="191.168.1.2", mac='00:00:00:00:00:02')
    host3 = net.addHost('h3', ip="191.168.1.3", mac='00:00:00:00:00:03')
    host4 = net.addHost('h4', ip="192.168.1.4", mac='00:00:00:00:00:04')
    host5 = net.addHost('h5', ip="191.168.1.4", mac='00:00:00:00:00:05')

    # switch
    switch1 = net.addSwitch('s1', ip="191.168.2.1", datapath='user')
    switch2 = net.addSwitch('s2', ip="191.168.2.2", datapath='user')
    switch3 = net.addSwitch('s3', ip="192.168.2.1", datapath='user')
    switch4 = net.addSwitch('s4', ip="191.168.2.3", datapath='user')

    # gateway
    gateway1 = net.addSwitch('g1', ip="191.1.1.1", dpid='A')
    gateway2 = net.addSwitch('g2', ip="192.1.1.1", dpid='B')

    # host - switch
    net.addLink(host1, switch1, 1, 1)
    net.addLink(host2, switch1, 1, 2)
    net.addLink(host3, switch2, 1, 1)
    net.addLink(host4, switch3, 1, 1)
    net.addLink(host5, switch4, 1, 1)

    # switch - switch
    net.addLink(switch1, switch2, 3, 2)
    net.addLink(switch2, switch4, 4, 2)

    # switch - gateway
    net.addLink(switch1, gateway1, 4, 2)
    net.addLink(switch2, gateway1, 3, 1)
    net.addLink(switch3, gateway2, 2, 1)

    # gateway - gateway
    net.addLink(gateway1, gateway2, 3, 2)

    # nat
    net.addNAT(name = 'nat0',
               connect = gateway1,
               inNamespace = False,
               mac='00:00:00:00:00:06').configDefault()

    net.addNAT(name = 'nat1',
               connect = gateway2,
               inNamespace = False,
               mac='00:00:00:00:00:07').configDefault()

    net.start()
    CLI(net)
    net.stop()