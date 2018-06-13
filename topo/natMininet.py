from mininet.cli import CLI
from mininet.log import setLogLevel, info,error
from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch

if __name__ == "__main__":
    setLogLevel("info")
    net = Mininet(switch=OVSSwitch, listenPort = 6633, ipBase='191.0.0.1/4')

    mycontroller = RemoteController("RemoteController")

    switch1 = net.addSwitch('s1', ip="191.168.2.1", datapath='user')
    gateway1 = net.addSwitch('g1', ip='191.1.1.1', dpid='A')
    host1 = net.addHost('h1', ip='191.168.1.1', mac='00:00:00:00:00:01')
    host2 = net.addHost('h2', ip='191.168.1.2', mac='00:00:00:00:00:02')

    net.addLink(switch1, gateway1, 3, 1)
    net.addLink(switch1, host1, 1, 1)
    net.addLink(switch1, host2, 2, 1)

    net.controllers = [mycontroller]
    net.nameToNode["RemoteController"] = mycontroller

    net.addNAT(name = 'nat0',
               connect = gateway1,
               inNamespace = False,
               mac='00:00:00:00:00:06').configDefault()

    net.start()
    CLI(net)
    net.stop()

