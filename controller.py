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
from GatewayManager import GatewayManager


class Controller(app_manager.RyuApp):

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    DEFAULT_TTL = 120           # default ttl for LLDP packet
    PORT_INQUIRY_TIME = 10      # default time interval for port inquiry
    PORT_SPEED_CAL_INTERVAL = 5     # default time interval to calculate port speed

    def __init__(self, *args, **kwargs):
        super(Controller, self).__init__(*args, **kwargs)

        # record for network configuration

        # arp table for different tenants
        self.arp_table = {1:{'191.168.1.1':'00:00:00:00:00:01',                 # {tenant_id ->{ip -> mac}}
                          '191.168.1.2':'00:00:00:00:00:02',
                             '191.168.1.3':'00:00:00:00:00:03',
                             '192.168.1.4':'00:00:00:00:00:04',
                            '191.168.1.4':'00:00:00:00:00:05',
                            '192.168.111.1':'10:00:00:00:00:00',
                              '192.168.1.6':'00:00:00:00:00:06',
                              '193.168.1.7':'00:00:00:00:00:07',
                              '192.168.1.8': '00:00:00:00:00:08'}
        }
        # arp table for different datacenter
        self.arp_table_datacenter = {                                               # {datacenter_id -> [ip]}
            1 : ['191.168.1.1', '191.168.1.2', '191.168.1.3', '191.168.1.4', '192.168.1.4', '192.168.111.1'],
            2 : ['192.168.1.6', '193.168.1.7', '192.168.1.8']
        }

        self.gateway_arp_table = {                                                  # dpid -> ip
            10 : '191.1.1.1',
            11 : '192.1.1.1',
            12 : '192.1.1.2',
            13 : '193.1.1.1'
        }
        self.host_pmac = {
                        '00:00:00:00:00:01' : 1,                              # pmac -> tenant_id
                          '00:00:00:00:00:02' : 1,
                          '00:00:00:00:00:03' : 1,
                          '00:00:00:00:00:04' : 1,
                          '00:00:00:00:00:05' : 1,
                          '10:00:00:00:00:00' : 1,
                          '00:00:00:00:00:06' : 1,
                         '00:00:00:00:00:07' : 1,
                         '00:00:00:00:00:08' : 1
        }
        self.tenant_level = {1 : 1}
        self.tenant_speed = {1 : 1024 * 8}
        self.datacenter_id = 1
        self.subnet = {                                                           # {subnet_id -> 'ip/mask'}
            1 : '191.0.0.0/8',
            2 : '192.0.0.0/8',
            3 : '193.0.0.0/8'
        }

        # record possible gateways for this controller {gateway_id -> {port_no -> 'datacenter_id' / subnet_number / 'NAT'}}
        # if datacenter_id  == 0, then the port is for Internet
        self.possible_gateways = {
            # TODO TEST!!!!!!!!
            #10 : {1:1, 2:1, 3:2, 4:'2', 5:'NAT'},
            10 : {1:1, 2:'NAT'},
            11 : {1:2, 2:1, 3:'2', 4:'NAT'},
            12 : {1:2, 2:3, 3:'1'},
            13 : {1:3, 2:2, 3:'1'}
        }
        # record which subnet the gateway is in
        self.gateway_in_subnet = {
            10 : 1,
            11 : 2,
            12 : 2,
            13 : 3
        }
        # record subnet for every datacenter
        # datacenter_id -> [subnet_id]
        self.datacenter_subnet = {
            1 : [1, 2],
            2 : [2, 3]
        }
        # record host in which gateway
        # src_pmac -> gateway_id
        self.host_gateway = {
            '00:00:00:00:00:01': 10,
            '00:00:00:00:00:02': 10,
            '00:00:00:00:00:03': 10,
            '00:00:00:00:00:04': 11,
            '00:00:00:00:00:05': 10,
            '10:00:00:00:00:00': 10,
            '00:00:00:00:00:06': 12,
            '00:00:00:00:00:07': 13,
            '00:00:00:00:00:08': 12
        }
        # record ip:mac for NAT
        self.NAT_ip_mac = {
            '191.0.0.3':'00:00:00:00:00:06'
        }

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
        self.gateway_vmac = {}                               # {dpid -> vmac}

        # components
        # self.utils = U.Utils()
        self.lldp_listener = LLDPListener(datapathes=self.datapathes,
                                          dpid_potrs=self.dpid_to_ports,
                                          dpid_to_dpid=self.dpid_to_dpid,
                                          topo=self.switch_topo,
                                          DEFAULT_TTL=self.DEFAULT_TTL,
                                          port_speed=self.port_speed)
        self.flow_manager = FlowModifier(datapathes=self.datapathes)
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
                                          calculate_interval=self.PORT_SPEED_CAL_INTERVAL)
        self.meter_manager = MeterModifier(meters=self.meters)
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
                                        topo_manager=self.topoManager)


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
                                               datacenter_sunbet=self.datacenter_subnet)





        # hub
        # self.port_desc_info_hub = hub.spawn(self.port_listener.inquiry_all_port_desc_stats)
        # self.port_statistics_info_hub = hub.spawn(self.port_listener.inquiry_all_port_statistics_stats)
        # self.topo_detect_hub = hub.spawn(self.lldp_listener.lldp_loop)
        # self.test_hub = hub.spawn(self.test)

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

        # TODO test!!!!!!!!!!!!!!!!!!
        if dpid == 10:
            eth = pkt.get_protocols(ethernet.ethernet)[0]
            dst = eth.dst
            src = eth.src

            print('eth_src=' + str(src) + ' ' + 'eth_dst=' + str(dst))

            if src == '00:00:00:00:00:06' and dst == 'ff:ff:ff:ff:ff:ff':
                i = iter(pkt)
                eth_pkt = six.next(i)
                special_pkt = six.next(i)

                if type(special_pkt) == arp.arp:
                    print('test pass')
                    if special_pkt.opcode == arp.ARP_REQUEST:
                        print('request')
                    elif special_pkt.opcode == arp.ARP_REPLY:
                        print('reply')
                    print('ip_dst : ' + str(special_pkt.dst_ip))


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
            # TODO if the host is in other datacenter
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
                    src_dpid = self.mac_manager.get_dpid_with_vmac(src)
                    nearest_gateway = self.topoManager.get_nearest_gateway(src_dpid)
                    path = self.topoManager.get_path(src_dpid, nearest_gateway)
                    # install flow entry for switches on path
                    for connect in path:
                        datapath = self.datapathes[connect[0]]
                        port = connect[1]

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






