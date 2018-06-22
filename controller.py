# -*- coding: utf-8 -*-
import six
import networkx as nx
import copy
from multiprocessing import Queue

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
from GatewayManager import GatewayManager
from RouteChanger import RouteChanger


class Controller(app_manager.RyuApp):

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    DEFAULT_TTL = 120           # default ttl for LLDP packet
    PORT_INQUIRY_TIME = 10      # default time interval for port inquiry
    PORT_SPEED_CAL_INTERVAL = 5     # default time interval to calculate port speed

    # port_speed
    DEFAULT_SS_BW = 300        # default bandwidth between switch

    def __init__(self, *args, **kwargs):
        super(Controller, self).__init__(*args, **kwargs)

        # record for network configuration

        # arp table for different tenants
        self.arp_table = {              # {tenant_id ->{ip -> mac}}
                        1:
                            {
                                '191.168.1.1':'00:00:00:00:00:01',
                                '191.168.1.2':'00:00:00:00:00:02',
                                '191.168.1.3':'00:00:00:00:00:03',
                                '192.168.1.4':'00:00:00:00:00:04',
                                '191.168.1.4':'00:00:00:00:00:05',
                                '192.168.111.1':'10:00:00:00:00:00',
                                '193.168.1.1':'00:00:00:00:04:00',
                                '191.168.1.6':'00:00:00:00:00:09',
                                '191.168.1.10':'00:00:00:00:01:00',
                                '191.168.1.11':'00:00:00:00:02:00'
                            },

                        2:
                            {
                                '191.168.1.1':'00:00:00:00:00:0a',
                                '191.168.1.2':'00:00:00:00:00:0b',
                                '191.168.1.3':'00:00:00:00:00:0c',
                                '191.168.1.10':'00:00:00:00:03:00',
                                '191.168.1.11':'00:00:00:00:05:00'
                            }
        }
        # arp table for different datacenter
        # TODO for different tenant
        self.arp_table_datacenter = {                                               # {datacenter_id -> [ip]}
            1 : ['191.168.1.1',
                 '191.168.1.2',
                 '191.168.1.3',
                 '191.168.1.4',
                 '192.168.1.4',
                 '192.168.111.1',
                 '191.168.1.6'],
            2 : ['192.168.1.6',
                 '193.168.1.7',
                 '192.168.1.8']
        }

        self.gateway_arp_table = {                                                  # dpid -> ip
            10 : '191.1.1.1',
            11 : '192.1.1.1',
            12 : '191.1.1.2',
            13 : '193.1.1.1'
        }
        self.host_pmac = {                                                          # pmac -> tenant_id
                        '00:00:00:00:00:01' : 1,
                        '00:00:00:00:00:02' : 1,
                        '00:00:00:00:00:03' : 1,
                        '00:00:00:00:00:04' : 1,
                        '00:00:00:00:00:05' : 1,
                        '10:00:00:00:00:00' : 1,
                        '00:00:00:00:04:00' : 1,
                        '00:00:00:00:00:09' : 1,
                        '00:00:00:00:01:00' : 1,
                        '00:00:00:00:02:00' : 1,
                        '00:00:00:00:00:0a' : 2,
                        '00:00:00:00:00:0b' : 2,
                        '00:00:00:00:00:0c' : 2,
                        '00:00:00:00:03:00' : 2,
                        '00:00:00:00:05:00' : 2
        }
        self.tenant_level = {
            1 : 1,
            2 : 2
        }
        self.tenant_speed = {
            1 : 1024 * 8,
            2 : 1024
        }
        self.datacenter_id = 1
        self.subnet = {                                                           # {subnet_id -> 'ip/mask'}
            1 : '191.0.0.0/8',
            2 : '192.0.0.0/8',
            3 : '193.0.0.0/8'
        }

        # record possible gateways for this controller
        # {gateway_id -> {port_no -> 'subnet_number in other datacenter'/ subnet_number in this datacenter/ 'NAT'}}
        # if datacenter_id  == 0, then the port is for Internet
        self.possible_gateways = {
            10: {1:1, 2:1, 3:2, 4:'1', 5:'3'},
            11: {1:2, 2:1, 3:'1', 4:'3'},
            12: {1:1, 2:3, 3:'1', 4:'2'},
            13: {1:3, 2:1, 3:'1', 4:'2'}
        }
        # record which subnet the gateway is in
        self.gateway_in_subnet = {
            10 : 1,
            11 : 2,
            12 : 1,
            13 : 3
        }
        # record subnet for every datacenter
        # datacenter_id -> [subnet_id]
        self.datacenter_subnet = {
            1 : [1, 2],
            2 : [1, 3]
        }
        # record host in which gateway
        # src_pmac -> gateway_id
        # TODO different tenant
        self.host_gateway = {
            '00:00:00:00:00:01': 10,
            '00:00:00:00:00:02': 10,
            '00:00:00:00:00:03': 10,
            '00:00:00:00:00:04': 11,
            '00:00:00:00:00:05': 10,
            '10:00:00:00:00:00': 10,
            '00:00:00:00:04:00': 13,
            '00:00:00:00:00:09': 10,
            '00:00:00:00:00:0a': 10,
            '00:00:00:00:00:0b': 10,
            '00:00:00:00:00:0c': 10,
            '00:00:00:00:03:00': 12,
            '00:00:00:00:05:00': 12,
            '00:00:00:00:01:00': 12,
            '00:00:00:00:02:00': 12
        }
        # record ip:mac for NAT
        self.NAT_ip_mac = {
            '191.0.0.6':'00:00:00:00:00:06',
            '191.0.0.7':'00:00:00:00:00:07'
        }
        # record NAT for each gateway
        # gateway_id -> NAT ip
        self.gateway_NAT = {
            10:'191.0.0.6',
            11:'191.0.0.7'
        }
        # record all datacenter_id
        self.all_datacenter_id = [
            1, 2
        ]

        # data in controller
        self.vmac_to_pmac = {                               # {vmac -> pmac}
            '21:00:01:00:02:01': '00:00:00:00:02:00',
            '22:00:02:00:01:04': '00:00:00:00:05:00',
            '22:00:02:00:02:02': '00:00:00:00:03:00',
            '21:00:01:00:03:01': '00:00:00:00:04:00',
            '21:00:01:00:01:01': '00:00:00:00:01:00'
        }
        self.pmac_to_vmac = {                               # {pmac -> vmac}
            '00:00:00:00:02:00': '21:00:01:00:02:01',
            '00:00:00:00:05:00': '22:00:02:00:01:04',
            '00:00:00:00:03:00': '22:00:02:00:02:02',
            '00:00:00:00:04:00': '21:00:01:00:03:01',
            '00:00:00:00:01:00': '21:00:01:00:01:01'
        }
        self.dpid_to_vmac = {}                              # {dpid -> vmac}
        self.datapathes = {}                                # {dpid -> datapath}
        self.dpid_to_ports = {}                             # {dpid -> ports}
        self.dpid_to_dpid = {}                              # {(dpid, port_id) -> dpid}
        self.switch_topo = nx.Graph()                       # switch topo
        self.port_speed = {}                                # {dpid -> {remote_dpid -> 'max_speed' - 'cur_speed'}}
        self.meters = {}                                    # {dpid -> {meter_id -> band_id}}
        self.gateways = {}                                  # {dpid -> {port_no -> datacenter_id}}
        self.gateway_vmac = {}                               # {dpid -> vmac}
        self.host_queue = {}                                # gateway_id -> queue for host

        # components
        # self.utils = U.Utils()
        self.lldp_listener = LLDPListener(datapathes=self.datapathes,
                                          dpid_potrs=self.dpid_to_ports,
                                          dpid_to_dpid=self.dpid_to_dpid,
                                          topo=self.switch_topo,
                                          DEFAULT_TTL=self.DEFAULT_TTL,
                                          port_speed=self.port_speed)
        self.flow_manager = FlowModifier(datapathes=self.datapathes,
                                         datacenter_id=self.datacenter_id,
                                         all_datacenter_id=self.all_datacenter_id)
        self.mac_manager = MacManager(pmac_to_vmac=self.pmac_to_vmac,
                                      vmac_to_pmac=self.vmac_to_pmac,
                                      tenant_level=self.tenant_level)
        self.topoManager = TopoManager(topo=self.switch_topo,
                                       dpid_to_dpid=self.dpid_to_dpid,
                                       gateways=self.gateways)
        self.arp_manager = ArpManager(arp_table=self.arp_table,
                                      pmac_to_vmac=self.pmac_to_vmac,
                                      gateway_arp_table=self.gateway_arp_table,
                                      dpid_to_vmac=self.dpid_to_vmac,
                                      topo_manager=self.topoManager,
                                      mac_manager=self.mac_manager,
                                      NAT_ip_mac=self.NAT_ip_mac)
        self.port_listener = PortListener(datapathes=self.datapathes,
                                          sleep_time=self.PORT_INQUIRY_TIME,
                                          dpid_to_dpid=self.dpid_to_dpid,
                                          port_speed=self.port_speed,
                                          calculate_interval=self.PORT_SPEED_CAL_INTERVAL,
                                          bandwidth_between_switch=self.DEFAULT_SS_BW)
        self.meter_manager = MeterModifier(meters=self.meters)
        self.route_changer = RouteChanger(port_speed=self.port_speed,
                                          flow_manager=self.flow_manager,
                                          dpid_to_dpid=self.dpid_to_dpid)
        self.host_manager = HostManager(arp_table=self.arp_table,
                                        host_pmac=self.host_pmac,
                                        mac_manager=self.mac_manager,
                                        datacenter_id=self.datacenter_id,
                                        pmac_to_vmac=self.pmac_to_vmac,
                                        vmac_to_pmac=self.vmac_to_pmac,
                                        meter_manager=self.meter_manager,
                                        tenant_speed=self.tenant_speed,
                                        flow_manager=self.flow_manager,
                                        host_gateway=self.host_gateway,
                                        datapathes=self.datapathes,
                                        topo_manager=self.topoManager,
                                        host_queue=self.host_queue)


        self.gateways_manager = GatewayManager(datapathes=self.datapathes,
                                               possibie_gatewats=self.possible_gateways,
                                               gateways=self.gateways,
                                               gateway_arp_table=self.gateway_arp_table,
                                               dpid_to_vmac=self.dpid_to_vmac,
                                               flow_manager=self.flow_manager,
                                               subnet=self.subnet,
                                               mac_manager=self.mac_manager,
                                               arp_table_datacenter=self.arp_table_datacenter,
                                               datacenter_id=self.datacenter_id,
                                               arp_table=self.arp_table,
                                               pmac_to_vmac=self.pmac_to_vmac,
                                               topo_manager=self.topoManager,
                                               gateway_in_subnet=self.gateway_in_subnet,
                                               gateway_vmac=self.gateway_vmac,
                                               datacenter_sunbet=self.datacenter_subnet,
                                               NAT_ip_mac=self.NAT_ip_mac,
                                               gateway_NAT=self.gateway_NAT,
                                               host_queue=self.host_queue)





        # hub
        self.install_host_flow_for_gateway_hub = hub.spawn(self.host_manager.install_host_flow_entry_gateway)
        # self.port_desc_info_hub = hub.spawn(self.port_listener.inquiry_all_port_desc_stats)
        # self.port_statistics_info_hub = hub.spawn(self.port_listener.inquiry_all_port_statistics_stats)
        # self.topo_detect_hub = hub.spawn(self.lldp_listener.lldp_loop)
        # self.route_calculater_hub = hub.spawn(self.route_changer.change_route)

        # test



    def _register(self, datapath):
        dpid = datapath.id
        self.datapathes[dpid] = datapath

        ports = copy.copy(datapath.ports)
        self.dpid_to_ports[dpid] = ports

        # create vmac for this datapath
        vmac = self.mac_manager.get_vmac_new_switch(datapath=dpid,
                                                    datacenter_id=self.datacenter_id)

        self.dpid_to_vmac[dpid] = vmac
        self.lldp_listener.lldp_detect(datapath)

        self.meters[dpid] = {}

    def _unregister(self, datapath):
        # TODO
        return


    @set_ev_cls(ofp_event.EventOFPStateChange, [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def switch_state_change_handler(self, ev):
        dp = ev.datapath
        dpid = dp.id

        # when a switch connect
        if ev.state == MAIN_DISPATCHER:
            # check whether it connect twice
            if dpid in self.datapathes.keys():
                return

            # install lldp packet flow entry, missing flow entry
            self.lldp_listener.install_lldp_flow(ev)
            self._register(dp)

            # check whether this is a gateway
            if dpid in self.possible_gateways.keys():
                self.gateways_manager.register_gateway(dpid)
                self.flow_manager.install_missing_flow_for_gateway(ev)
            else:
                self.flow_manager.install_missing_flow(ev)
                # install flow for same subnet in different datacenter
                self.flow_manager.intall_flow_entry_for_same_subnet_in_different_datacenter(ev)

            return

        elif ev.state == DEAD_DISPATCHER:
            self._unregister(dp)
            return

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        dp = msg.datapath
        dpid = dp.id

        ofproto = dp.ofproto
        parser = dp.ofproto_parser
        pkt = packet.Packet(msg.data)

        eth = pkt.get_protocols(ethernet.ethernet)[0]
        dst = eth.dst
        src = eth.src
        in_port = msg.match['in_port']

        # check the protocol
        # ethernet protocol
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
            print('the src is ' + str(src))
            tenant_id = self.mac_manager.get_tenant_id_with_vmac(src)
            self.arp_manager.handle_arp(datapath=dp, in_port=in_port, pkt_ethernet=eth,
                                        pkt_arp=special_pkt, tenant_id=tenant_id,
                                        topoManager=self.topoManager,
                                        whole_packet=pkt)
            return

        # then check whether this ev is from gateway (not arp and lldp)
        if dpid in self.gateways.keys():
            self.gateways_manager.gateway_packet_in_handler(ev)
            return

        # check if the source has no record
        if not src in self.pmac_to_vmac.keys() and not src in self.vmac_to_pmac.keys():
            # first check whether this is pmac for host(not a vmac for host or switch, not a pmac for port that connect ovs)
            if src in self.host_pmac.keys():
                # test
                print('new host coming!!==============' + src)
                self.host_manager.register_host(ev)

        # if src is a vmac, which means this host has been registered
        elif src in self.vmac_to_pmac.keys():
            # first check whether dst is a host vmac or is a gateway vmac
            if dst in self.vmac_to_pmac.keys() or dst in self.gateway_vmac.values():
                # then check whether it is in this datacenter
                if self.mac_manager.get_datacenter_id_with_vmac(dst) == self.datacenter_id:
                    # test
                    print('pkt from ' + src + ' to ' + dst)

                    # find the route
                    dst_dpid = self.mac_manager.get_dpid_with_vmac(dst)
                    path = self.topoManager.get_path(dpid, dst_dpid)
                    # install flow entry for only this switch
                    datapath = self.datapathes[dpid]
                    port = path[0][1]
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

                # if dst is not in this datacenter
                else:
                    # send the pkt to the corresponding gateway
                    # first get the gateway_id for src
                    datacenter_id = self.mac_manager.get_datacenter_id_with_vmac(dst)
                    tenant_id = self.mac_manager.get_tenant_id_with_vmac(src)
                    src_ip = None
                    for ip,mac in self.arp_table[tenant_id].items():
                        if self.pmac_to_vmac[mac] == src:
                            src_ip = ip
                            break
                    assert src_ip is not None
                    gateway_id = self.host_gateway[self.vmac_to_pmac[src]]

                    # then get path from dpid to gateway_id
                    path = self.topoManager.get_path(dpid, gateway_id)
                    for (switch, port) in path:
                        match = parser.OFPMatch()
                        match.append_field(
                            header=ofproto_v1_3.OXM_OF_ETH_DST_W,
                            mask=self.flow_manager.get_datacenter_id_mask(),
                            value=self.flow_manager.get_datacenter_id_value(datacenter_id)
                        )
                        actions = [parser.OFPActionOutput(port)]
                        instructions = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]

                        s = self.datapathes[switch]
                        self.flow_manager.add_flow(datapath=s,
                                                   priority=4,
                                                   match=match,
                                                   instructions=instructions,
                                                   table_id=2,
                                                   buffer_id=msg.buffer_id)

                    s = self.datapathes[dpid]
                    actions = [parser.OFPActionOutput(path[0][1])]
                    data = None
                    if msg.buffer_id == ofproto.OFP_NO_BUFFER:
                        data = msg.data
                    out_packet = parser.OFPPacketOut(datapath=s, buffer_id=msg.buffer_id,
                                                     in_port=in_port, actions=actions, data=data)
                    s.send_msg(out_packet)
                    return

            else:
                # TODO what iare those 33:00.... mac ?
                # print(str(src) + ' to ' + dst)
                # print('Unkonown host for ' + dst)
                return




        else:
            # print('wrong logic for scr. ' + 'This packet is from ' + src + ' to ' + dst + ', the ovs is ' + dpid_to_str(dpid))
            return

    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def port_statistics_stats_reply_handler(self, ev):
        # test
        # print('ports statis info reply==========================')
        self.port_listener.port_statistics_stats_handler(ev)

    @set_ev_cls(ofp_event.EventOFPPortDescStatsReply, MAIN_DISPATCHER)
    def port_desc_stats_reply_handler(self, ev):
        print('ports desc info reply==========================')
        self.port_listener.port_desc_stats_handler(ev)






