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
from TopoManager import TopoManager
# import utils as U

class Controller(app_manager.RyuApp):

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    DEFAULT_TTL = 120  # default ttl for LLDP packet
    IDLE_TIME = 10

    def __init__(self, *args, **kwargs):
        super(Controller, self).__init__(*args, **kwargs)

        # tables
        # self.arp_table = self.utils.initIP2MAC()            # {ip -> mac}
        self.arp_table = {'192.168.1.3':'00:00:00:00:00:01',
                          '192.168.2.3':'00:00:00:00:00:02'}
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
        self.topoManager = TopoManager(topo=self.switch_topo,
                                       dpid_to_dpid=self.dpid_to_dpid)




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
        # print('receive a packet')
        msg = ev.msg
        dp = msg.datapath
        ofproto = dp.ofproto
        parser = dp.ofproto_parser
        dpid = dp.id
        pkt = packet.Packet(msg.data)

        # check the protocol
        i = iter(pkt)
        eth_pkt = six.next(i)
        assert type(eth_pkt) == ethernet.ethernet

        special_pkt = six.next(i)

        # LLDP packet
        if type(special_pkt) == lldp.lldp:
            self.lldp_listener.lldp_packet_in(ev)
            return

        elif type(special_pkt) == arp.arp:
            # TODO deal with arp packet
            return

        eth = pkt.get_protocols(ethernet.ethernet)[0]
        dst = eth.dst
        src = eth.src
        in_port = msg.match['in_port']

        # check if the source has a vmac
        if not src in self.pmac_to_vmac.keys():
            # first check whether this is pmac for host(not a vmac for host or switch, not a pmac for port that connect ovs)
            all_ports_pmac = []
            for id, ports in self.dpid_to_ports.items():
                for p_id, p in ports.items():
                    all_ports_pmac.append(p.hw_addr)
            if not src in self.vmac_to_pmac.keys() and not src in self.dpid_to_vmac.values()\
                    and not src in all_ports_pmac:
                # test
                print('new host coming!!==============' + src)
                src_vmac = self.mac_manager.get_vmac_new_host(dpid=dpid, port_id=in_port)
                self.pmac_to_vmac[src] = src_vmac
                self.vmac_to_pmac[src_vmac] = src
                print(self.pmac_to_vmac)
                # install flow table to (pmac -> vmac) when sending
                # install flow table to (vmac -> pmac) when receving
                self.flow_manager.transfer_src_pmac_to_vmac(ev, src, src_vmac)
                self.flow_manager.transfer_dst_vmac_to_pmac(ev, src_vmac, src)

            # send the packet if know the dst_vmac
            # if dst in self.vmac_to_pmac.keys():
            #     dst_vmac = self.vmac_to_pmac[dst]
            #     # TODO should I install a flow entry here to (dst_pmac -> dst_vmac)?
            #     dpid = self.mac_manager.get_dpid_with_vmac(dst_vmac)
            #     datapath = self.datapathes[dpid]
            #
            #     # TODO add a flow entry avoid packet in next time
            #     actions = [parser.OFPMatch(in_port=in_port, eth_dst=dst)]
            #
            #     # send the packet
            #     ethertype = eth.ethertype
            #     pkt.del_protocol(eth)
            #     pkt.add_protocol_from_head(ethernet.ethernet(ethertype, dst=dst_vmac, src=src_vmac))
            #     pkt.serialize()
            #
            #     datapath.send_msg(pkt)
            #
            #
            #
            # else:
            #     # TODO check the ports which connects to a host and send the packet
            #     print('unknow dst_mac')
            #     return
        # if has this vmac
        else:
            # if also has dst_vmac
            if dst in self.vmac_to_pmac.keys():
                dst_dpid = self.mac_manager.get_dpid_with_vmac(dst)
                path, last_switch = self.topoManager.get_path(dpid, dst_dpid)
                # install flow entry for switches on path
                for connect in path:
                    datapath = self.datapathes[connect[0]]
                    port = connect[1]
                    self.flow_manager.install_sending_flow(datapath, port, src, dst)
                # install flow entry for the last switch
                last_datapath = self.datapathes[last_switch]
                out_port = self.mac_manager.get_port_id_with_vmac(dst)
                self.flow_manager.install_sending_flow(last_datapath, out_port, src, self.vmac_to_pmac[dst])
                # finally send the packet
                actions = [parser.OFPActionOutput(out_port)]
                out_packet = parser.OFPPacketOut(datapath=dp, buffer_id=msg.buffer_id,
                                                 in_port=in_port, actions=actions, data=msg.data)
                dp.send_msg(out_packet)

            # TODO not simply drop the packet
            else:
                return






    def test(self):
        hub.sleep(10)
        print(self.dpid_to_dpid)


































