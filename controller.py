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
from ArpManager import ArpManager
# import utils as U

class Controller(app_manager.RyuApp):

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    DEFAULT_TTL = 120  # default ttl for LLDP packet
    IDLE_TIME = 10

    def __init__(self, *args, **kwargs):
        super(Controller, self).__init__(*args, **kwargs)

        # tables
        # self.arp_table = self.utils.initIP2MAC()            # {ip -> mac}
        self.arp_table = {1:{'192.168.1.3':'00:00:00:00:00:01',                 # {tenant_id ->{ip -> mac}}
                          '192.168.2.3':'00:00:00:00:00:02'}}
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
        self.arp_manager = ArpManager(arp_table=self.arp_table,
                                      pmac_to_vmac=self.pmac_to_vmac)




        # hub
        self.topo_detect_hub = hub.spawn(self.lldp_listener.lldp_loop)
        # self.test_hub = hub.spawn(self.test)


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

            # install lldp packet flow entry, missing flow entry
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
        # test
        print('a packet coming ==================')
        msg = ev.msg
        dp = msg.datapath
        ofproto = dp.ofproto
        parser = dp.ofproto_parser
        dpid = dp.id
        pkt = packet.Packet(msg.data)

        eth = pkt.get_protocols(ethernet.ethernet)[0]
        dst = eth.dst
        src = eth.src
        in_port = msg.match['in_port']
        # test
        print('This packet is form ' + src + ' to ' + dst)

        # check the protocol
        i = iter(pkt)
        eth_pkt = six.next(i)
        assert type(eth_pkt) == ethernet.ethernet

        special_pkt = six.next(i)

        # LLDP packet
        if type(special_pkt) == lldp.lldp:
            self.lldp_listener.lldp_packet_in(ev)
            return
        # arp packet
        elif type(special_pkt) == arp.arp:
            # test
            print('a arp packte is coming===============')
            print(in_port)
            tenant_id = self.mac_manager.get_tenant_id_with_vmac(src)
            self.arp_manager.handle_arp(datapath=dp, in_port=in_port, pkt_ethernet=eth,
                                        pkt_arp=special_pkt, tenant_id=1)
            return

        # check if the source has no record
        if (not src in self.pmac_to_vmac.keys()) and (not src in self.vmac_to_pmac.keys()):
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
                # install receiving flow entry for this host
                self.flow_manager.transfer_src_pmac_to_vmac(ev, src, src_vmac)
                self.flow_manager.transfer_dst_vmac_to_pmac(ev, src_vmac, src)
                self.flow_manager.install_receiving_flow_entry(dp, src, in_port)

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
        # if src is a vmac
        elif src in self.vmac_to_pmac.keys():
            # if also has dst_vmac
            if dst in self.vmac_to_pmac.keys():
                dst_dpid = self.mac_manager.get_dpid_with_vmac(dst)
                path = self.topoManager.get_path(dpid, dst_dpid)
                # test
                print('should be a ping packet==========================')
                print(path)
                # install flow entry for switches on path
                for connect in path:
                    datapath = self.datapathes[connect[0]]
                    port = connect[1]
                    self.flow_manager.install_sending_flow(datapath, port, src, dst)
                # finally send the packet
                out_port = path[0][1]
                actions = [parser.OFPActionOutput(out_port)]
                out_packet = parser.OFPPacketOut(datapath=dp, buffer_id=msg.buffer_id,
                                                 in_port=in_port, actions=actions, data=msg.data)
                dp.send_msg(out_packet)

            # TODO not simply drop the packet
            else:
                return

        else:
            print('wrong logic for scr')





    # below is the test function
    def test(self):
        while True:
            hub.sleep(7)
            for key, value in self.datapathes.items():
                print(str(key) + '=========================================')
                self.send_flow_stats_request(value)

    def send_flow_stats_request(self, datapath):
        ofp = datapath.ofproto
        ofp_parser = datapath.ofproto_parser

        cookie = cookie_mask = 0
        match = ofp_parser.OFPMatch(eth_src='00:00:00:00:00:01')
        req = ofp_parser.OFPFlowStatsRequest(datapath, 0,
                                         ofp.OFPTT_ALL,
                                         ofp.OFPP_ANY, ofp.OFPG_ANY,
                                         cookie, cookie_mask,
                                         match)
        datapath.send_msg(req)

    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def flow_stats_reply_handler(self, ev):
        flows = []
        for stat in ev.msg.body:
            flows.append('table_id=%s '
                         'duration_sec=%d duration_nsec=%d '
                         'priority=%d '
                         'idle_timeout=%d hard_timeout=%d flags=0x%04x '
                         'cookie=%d packet_count=%d byte_count=%d '
                         'match=%s instructions=%s' %
                         (stat.table_id,
                          stat.duration_sec, stat.duration_nsec,
                          stat.priority,
                          stat.idle_timeout, stat.hard_timeout, stat.flags,
                          stat.cookie, stat.packet_count, stat.byte_count,
                          stat.match, stat.instructions))
        print('FlowStats: %s', flows)



































