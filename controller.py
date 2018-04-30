# -*- coding: utf-8 -*-
import six
import networkx as nx
import copy

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import set_ev_cls
from ryu.controller.handler import MAIN_DISPATCHER, DEAD_DISPATCHER, CONFIG_DISPATCHER
from ryu.lib.packet import packet, ethernet
from ryu.lib.packet import lldp, ether_types
from ryu.lib.packet import ipv4, tcp, udp, icmp, arp
from ryu.ofproto import ofproto_v1_3
from ryu.ofproto import ether, inet
from ryu.lib import hub
from netaddr import IPAddress, IPNetwork
from collections import namedtuple
from ryu.app.wsgi import WSGIApplication

from ryu.lib.dpid import dpid_to_str, str_to_dpid


from LLDP import LLDPListener
from FlowModifier import FlowModifier
from MacManager import MacManager
# import utils as U

class Controller(app_manager.RyuApp):

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    DEFAULT_TTL = 120  # default ttl for LLDP packet
    IDLE_TIME = 10

    def __init__(self, *args, **kwargs):
        super(Controller, self).__init__(*args, **kwargs)

        # tables
        # self.arp_table = self.utils.initIP2MAC()            # {ip -> mac}
        self.vmac_to_pmac = {}                              # {vmac -> pmac}
        self.pmac_to_vmac = {}                              # {pmac -> vmac}
        self.dpid_to_vmac = {}                              # {dpid -> vmac}
        self.datapathes = {}                                # {dpid -> datapath}
        self.dpid_to_ports = {}                             # {dpid -> ports}
        self.dpid_to_dpid = {}                              # {(dpid, port_id) -> dpid}
        self.switch_topo = nx.Graph()                       # switch topo

        # components
        # self.utils = U.Utils()
        self.lldp_listener = LLDPListener(datapathes=self.datapathes,
                                          dpid_potrs=self.dpid_to_ports,
                                          dpid_to_dpid=self.dpid_to_dpid,
                                          topo=self.switch_topo,
                                          DEFAULT_TTL=self.DEFAULT_TTL)
        self.flow_manager = FlowModifier()
        self.mac_manager = MacManager(pmac_to_vmac=self.pmac_to_vmac,
                                      vmac_to_pmac=self.vmac_to_pmac)




        # hub
        self.topo_detect_hub = hub.spawn(self.lldp_listener.lldp_loop)
        self.test_hub = hub.spawn(self.test)


    def _register(self, datapath):
        dpid = datapath.id
        self.datapathes[dpid] = datapath

        ports = copy.copy(datapath.ports)
        self.dpid_to_ports[dpid] = ports

        # create vmac for this datapath
        vmac = self.mac_manager.get_vmac_new_switch(dpid)

        #self.pmac_to_vmac[]
        self.dpid_to_vmac[dpid] = vmac

        return

    def _unregister(self, datapath):
        # TODO
        return


    @set_ev_cls(ofp_event.EventOFPStateChange, [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def switch_state_change_handler(self, ev):
        dp = ev.datapath
        ofproto = dp.ofproto
        ofproto_parser = dp.ofproto_parser
        dpid = dp.id

        # when a switch connect
        if ev.state == MAIN_DISPATCHER:
            # check whether it connect twice
            if dpid in self.datapathes.keys():
                return

            self._register(dp)
            self.lldp_listener.install_lldp_flow(ev)
            self.flow_manager.install_missing_flow(ev)

            return

        elif ev.state == DEAD_DISPATCHER:
            self._unregister(dp)
            return

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        print('receive a packet')
        msg = ev.msg
        dp = msg.datapath
        dpid = dp.id
        pkt = packet.Packet(msg.data)

        # check the protocol
        i = iter(pkt)
        eth_pkt = six.next(i)
        assert type(eth_pkt) == ethernet.ethernet

        lldp_pkt = six.next(i)

        # LLDP packet
        if type(lldp_pkt) == lldp.lldp:
            self.lldp_listener.lldp_packet_in(ev)
            return

        eth = pkt.get_protocols(ethernet.ethernet)[0]
        dst = eth.dst
        src = eth.src
        in_port = msg.match['in_port']

        # check if the source has a vmac
        if not src in self.pmac_to_vmac.keys():
            src_vmac = self.mac_manager.get_vmac_new_host(dpid=dpid, port_id=in_port)
            self.pmac_to_vmac[src] = src_vmac
            self.vmac_to_pmac[src_vmac] = src
            # install flow table to (pmac -> vmac) when sending
            # install flow table to (vmac -> pmac) when receving
            self.flow_manager.transfer_src_pmac_to_vmac(ev, src, src_vmac)
            self.flow_manager.transfer_dst_vmac_to_pmac(ev, src, src_vmac)

            # send the packet if know the dst_vmac
            if dst in self.vmac_to_pmac.keys():
                dst_vmac = self.vmac_to_pmac[dst]
                dpid = self.mac_manager.get_dpid_with_vmac(dst_vmac)
                datapath = self.datapathes[dpid]

                ethertype = eth.ethertype
                pkt.del_protocol(eth)
                pkt.add_protocol_from_head(ethernet.ethernet(ethertype, dst=dst_vmac, src=src_vmac))
                pkt.serialize()

                datapath.send_msg(pkt)
            else:
                # TODO check the ports which connects to a host and send the packet
                print('unknow dst_mac')
                return





    def test(self):
        hub.sleep(10)
        print(self.dpid_to_dpid)


































