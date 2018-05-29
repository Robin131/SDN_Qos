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
from PortListener import PortListener
from HostManager import HostManager
from MeterModifier import MeterModifier
# from GatewayManager import GatewayManager
# import utils as U

class Controller(app_manager.RyuApp):

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    DEFAULT_TTL = 120           # default ttl for LLDP packet
    PORT_INQUIRY_TIME = 10      # default time interval for port inquiry
    PORT_SPEED_CAL_INTERVAL = 5     # default time interval to calculate port speed

    def __init__(self, *args, **kwargs):
        super(Controller, self).__init__(*args, **kwargs)

        # record for network configuration
        self.arp_table = {1:{'192.168.1.1':'00:00:00:00:00:01',                 # {tenant_id ->{ip -> mac}}
                          '192.168.1.2':'00:00:00:00:00:02',
                             '192.168.1.3':'00:00:00:00:00:03',
                             '192.168.1.4':'00:00:00:00:00:04',
                             '192.168.2.1':'00:00:00:00:00:05',
                            '192.168.111.1':'10:00:00:00:00:00'}}
        self.host_pmac = {'00:00:00:00:00:01' : 1,                              # pmac -> tenant_id
                          '00:00:00:00:00:02' : 1,
                          '00:00:00:00:00:03' : 1,
                          '00:00:00:00:00:04' : 1,
                          '00:00:00:00:00:05' : 1,
                          '10:00:00:00:00:00' : 1}
        self.tenant_level = {1 : 1}
        self.tenant_speed = {1 : 1024 * 8}
        self.datacenter_id = 1

        # record possible gateways for this controller {gateway_id -> {port_no -> datacenter_id}}
        # if datacenter_id  == 0, then the port is for Internet
        self.possible_gateways = {10 : {2 : 2},
                                  11 : {2 : 2}}

        # data in controller
        self.vmac_to_pmac = {}                              # {vmac -> pmac}
        self.pmac_to_vmac = {}                              # {pmac -> vmac}
        self.dpid_to_vmac = {}                              # {dpid -> vmac}
        self.datapathes = {}                                # {dpid -> datapath}
        self.dpid_to_ports = {}                             # {dpid -> ports}
        self.dpid_to_dpid = {}                              # {(dpid, port_id) -> dpid}
        self.switch_topo = nx.Graph()                       # switch topo
        self.port_speed = {}                                # {dpid -> {port_id -> 'cur_speed', 'max_speed'}}
        self.meters = {}                                    # {dpid -> {meter_id -> band_id}}
        self.gateways = {}                                  # {dpid -> {port_no -> datacenter_id}}
        self.gateway_mac = {}                               # {dpid -> pmac}

        # components
        # self.utils = U.Utils()
        self.lldp_listener = LLDPListener(datapathes=self.datapathes,
                                          dpid_potrs=self.dpid_to_ports,
                                          dpid_to_dpid=self.dpid_to_dpid,
                                          topo=self.switch_topo,
                                          DEFAULT_TTL=self.DEFAULT_TTL,
                                          port_speed=self.port_speed)
        self.flow_manager = FlowModifier()
        self.mac_manager = MacManager(pmac_to_vmac=self.pmac_to_vmac,
                                      vmac_to_pmac=self.vmac_to_pmac,
                                      tenant_level=self.tenant_level)
        self.topoManager = TopoManager(topo=self.switch_topo,
                                       dpid_to_dpid=self.dpid_to_dpid)
        self.arp_manager = ArpManager(arp_table=self.arp_table,
                                      pmac_to_vmac=self.pmac_to_vmac)
        self.port_listener = PortListener(datapathes=self.datapathes,
                                          sleep_time=self.PORT_INQUIRY_TIME,
                                          dpid_to_dpid=self.dpid_to_dpid,
                                          port_speed=self.port_speed,
                                          calculate_interval=self.PORT_SPEED_CAL_INTERVAL)
        self.host_manager = HostManager(arp_table=self.arp_table,
                                        host_pmac=self.host_pmac)
        self.meter_manager = MeterModifier(meters=self.meters)
        # self.gateways_manager = GatewayManager(possibie_gatewats=self.possible_gateways,
        #                                        gateways=self.gateways)





        # hub
        # self.port_desc_info_hub = hub.spawn(self.port_listener.inquiry_all_port_desc_stats)
        # self.port_statistics_info_hub = hub.spawn(self.port_listener.inquiry_all_port_statistics_stats)
        # self.topo_detect_hub = hub.spawn(self.lldp_listener.lldp_loop)
        # self.test_hub = hub.spawn(self.test)


    def _register(self, datapath):
        dpid = datapath.id
        self.datapathes[dpid] = datapath

        ports = copy.copy(datapath.ports)
        self.dpid_to_ports[dpid] = ports

        # create vmac for this datapath
        vmac = self.mac_manager.get_vmac_new_switch(datapath=dpid,
                                                    datacenter_id=self.datacenter_id)

        #self.pmac_to_vmac[]
        self.dpid_to_vmac[dpid] = vmac
        self.lldp_listener.lldp_detect(datapath)

        self.meters[dpid] = {}

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
        # print('a packet coming ==================')
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
        # print('This packet is from ' + src + ' to ' + dst + ', the ovs is ' + dpid_to_str(dpid))

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
        if not src in self.pmac_to_vmac.keys() and not src in self.vmac_to_pmac.keys():
            # first check whether this is pmac for host(not a vmac for host or switch, not a pmac for port that connect ovs)

            if src in self.host_pmac.keys():
                # test
                print('new host coming!!==============' + src)
                tenant_id = self.host_manager.get_tenant_id(src)
                src_vmac = self.mac_manager.get_vmac_new_host(dpid=dpid, port_id=in_port,
                                                              datacenter_id=self.datacenter_id,
                                                              tenant_id=tenant_id)
                self.pmac_to_vmac[src] = src_vmac
                self.vmac_to_pmac[src_vmac] = src
                print(self.vmac_to_pmac)
                # install flow table to (pmac -> vmac) when sending (there may be a speed limit)
                # install flow table to (vmac -> pmac) when receving
                # install receiving flow entry for this host
                if tenant_id in self.tenant_speed.keys():
                    # test
                    print('add meter')
                    meter_id = self.meter_manager.add_meter(datapath=dp, speed=self.tenant_speed[tenant_id])
                    print('meter id is ' + str(meter_id))
                    self.flow_manager.transfer_src_pmac_to_vmac(ev, src, src_vmac, meter_id=meter_id)
                else:
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
                        self.flow_manager.install_wildcard_sending_flow(dp=datapath,
                                                                        out_port=port,
                                                                        dst_dpid=dst_dpid,
                                                                        buffer_id=msg.buffer_id)

                # finally send the packet
                if len(path) > 0:
                    out_port = path[0][1]
                    actions = [parser.OFPActionOutput(out_port)]
                else:
                    actions = []
                data = None
                if msg.buffer_id == ofproto.OFP_NO_BUFFER:
                    data = msg.data
                out_packet = parser.OFPPacketOut(datapath=dp, buffer_id=msg.buffer_id,
                                                 in_port=in_port, actions=actions, data=data)
                dp.send_msg(out_packet)

            # TODO not simply drop the packet
            else:
                return

        else:
            print('wrong logic for scr. ' + 'This packet is from ' + src + ' to ' + dst + ', the ovs is ' + dpid_to_str(dpid))

    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def port_statistics_stats_reply_handler(self, ev):
        # test
        # print('ports statis info reply==========================')
        self.port_listener.port_statistics_stats_handler(ev)

    @set_ev_cls(ofp_event.EventOFPPortDescStatsReply, MAIN_DISPATCHER)
    def port_desc_stats_reply_handler(self, ev):
        print('ports desc info reply==========================')
        self.port_listener.port_desc_stats_handler(ev)






