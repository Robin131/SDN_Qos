# -*- coding: utf-8 -*-
import six
import networkx as nx
import copy

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import set_ev_cls
from ryu.controller.handler import MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.lib.packet import packet, ethernet
from ryu.lib.packet import lldp
from ryu.lib.packet import ipv4, tcp, udp, icmp, arp
from ryu.ofproto import ofproto_v1_3
from ryu.lib import hub

from SwitchManager2 import SwitchManager
from LLDPManager import LLDPListener
from MacManager2 import MacManager
from ArpManager2 import ArpManager
from HostManager2 import HostManager
from TopoManager2 import TopoManager
from FlowManager2 import FlowManager
from GatewayManager2 import GatewayManager


class Controller(app_manager.RyuApp):

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    DEFAULT_TTL = 120           # default ttl for LLDP packet
    PORT_INQUIRY_TIME = 10      # default time interval for port inquiry
    PORT_SPEED_CAL_INTERVAL = 5     # default time interval to calculate port speed
    GATEWAY_FLOW_INQUIRY_TIME = 10  # default time interval for gateway flow table inquiry

    # port_speed
    DEFAULT_SS_BW = 300        # default bandwidth between switch
    DEFAULT_GG_BW = 1000       # default bandwidth between gateway in different datacenter

    def __init__(self, *args, **kwargs):
        super(Controller, self).__init__(*args, **kwargs)

        # configurations for the system
        self.datacenter_id = 1
        # arp table for different tenants
        self.arp_table = {  # {tenant_id ->{ip -> mac}}
            1:
                {
                    '191.168.1.1': '00:00:00:00:00:01',
                    '191.168.1.2': '00:00:00:00:00:02',
                    '191.168.1.3': '00:00:00:00:00:03',
                    '192.168.1.4': '00:00:00:00:00:04',
                    '191.168.1.4': '00:00:00:00:00:05',
                    '192.168.111.1': '10:00:00:00:00:00',
                    '193.168.1.1': '00:00:00:00:04:00',
                    '191.168.1.6': '00:00:00:00:00:09',
                    '191.168.1.10': '00:00:00:00:01:00',
                    '191.168.1.11': '00:00:00:00:02:00'
                },

            2:
                {
                    '191.168.1.1': '00:00:00:00:00:0a',
                    '191.168.1.2': '00:00:00:00:00:0b',
                    '191.168.1.3': '00:00:00:00:00:0c',
                    '191.168.1.10': '00:00:00:00:03:00',
                    '191.168.1.11': '00:00:00:00:05:00'
                }
        }

        # pmac -> tenant_id
        self.host_pmac = {
            '00:00:00:00:00:01': 1,
            '00:00:00:00:00:02': 1,
            '00:00:00:00:00:03': 1,
            '00:00:00:00:00:04': 1,
            '00:00:00:00:00:05': 1,
            '10:00:00:00:00:00': 1,
            '00:00:00:00:04:00': 1,
            '00:00:00:00:00:09': 1,
            '00:00:00:00:01:00': 1,
            '00:00:00:00:02:00': 1,
            '00:00:00:00:00:0a': 2,
            '00:00:00:00:00:0b': 2,
            '00:00:00:00:00:0c': 2,
            '00:00:00:00:03:00': 2,
            '00:00:00:00:05:00': 2
        }

        # tenant_id -> tenant_level
        self.tenant_level = {
            1: 1,
            2: 2
        }

        # record all potential subnet
        self.subnets = [
            '191.0.0.0/8',
            '192.0.0.0/8',
            '10.0.0.0/8'
        ]

        # record all potential gateway
        self.potential_gateway = {
            10 : {},
            11 : {},
            12 : {}
        }

        # record all potential gateway_ip
        self.gateway_ip = [
            '191.0.0.1',
            '192.0.0.1'
        ]


        # record for system
        # data in controller
        self.vmac_to_pmac = {}                              # {vmac -> vmac}
        self.pmac_to_vmac = {}                              # {pmac -> vmac}
        self.dpid_to_vmac = {}                              # {dpid -> vmac}
        self.datapathes = {}                                # {dpid -> datapath}
        self.dpid_to_ports = {}                             # {dpid -> ports}
        self.dpid_to_dpid = {}                              # {(dpid, port_id) -> dpid}
        self.switch_topo = nx.Graph()                       # switch topo
        self.port_speed = {}                                # {dpid -> {remote_dpid -> 'max_speed' - 'cur_speed'}}
        self.gateway_port_speed = {}                        # {gateway_id -> {port_no -> speed}}
        self.meters = {}                                    # {dpid -> {meter_id -> band_id}}
        self.gateways = {}                                  # {dpid -> {port_no -> datacenter_id}}
        self.gateway_vmac = {}                               # {dpid -> vmac}
        self.host_queue = {}                                # gateway_id -> queue for host
        self.switch_gateway_connection = {}                 # (switch_id, gateway_id) -> (switch_port, gateway_port)
        self.host_gateway = {}                              # {vmac -> gateway_id}

        # components
        self.flow_manager = FlowManager(
            datapathes=self.datapathes,
            gateways=self.gateways
        )
        self.lldp_manager = LLDPListener(
            datapathes=self.datapathes,
            dpid_potrs=self.dpid_to_ports,
            dpid_to_dpid=self.dpid_to_dpid,
            topo=self.switch_topo,
            DEFAULT_TTL=self.DEFAULT_TTL,
            port_speed=self.port_speed
        )
        self.swtich_manager = SwitchManager(
            datapathes=self.datapathes,
            dpid_to_ports=self.dpid_to_ports,
            datacenter_id=self.datacenter_id,
            dpid_to_vmac=self.dpid_to_vmac,
            lldp_manager=self.lldp_manager,
            meters=self.meters,
            subnets=self.subnets
        )
        self.arp_manager = ArpManager(
            arp_table=self.arp_table,
            pmac_to_vmac=self.pmac_to_vmac,
            gateway_ip=self.gateway_ip,
            gateways=self.gateways,
            dpid_to_vmac=self.dpid_to_vmac,
            switch_gateway_connection=self.switch_gateway_connection,
            datapathes=self.datapathes
        )
        self.mac_manager = MacManager(
            tenant_level=self.tenant_level
        )
        self.host_manager = HostManager(
            host_pmac=self.host_pmac,
            mac_manager=self.mac_manager,
            datacenter_id=self.datacenter_id,
            pmac_to_vmac=self.pmac_to_vmac,
            vmac_to_pmac=self.vmac_to_pmac
        )
        self.topo_manager = TopoManager(
            topo=self.switch_topo,
            dpid_to_dpid=self.dpid_to_dpid
        )
        self.gateway_manager = GatewayManager(
            gateways=self.gateways,
            potential_gateway = self.potential_gateway
        )

        # hub
        self.init_hub = hub.spawn(self.init_controller)


    @set_ev_cls(ofp_event.EventOFPStateChange, [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def switch_state_change_handler(self, ev):
        dp = ev.datapath
        dpid = dp.id

        if ev.state == MAIN_DISPATCHER:
            # check whether it connect twice
            if dpid in self.datapathes.keys():
                return

            # install lldp packet flow entry, missing flow entry
            self.lldp_manager.install_lldp_flow(ev)
            self.swtich_manager.register_switch(ev)

            if dpid in self.potential_gateway:
                self.gateway_manager.register_gateway(ev)

        elif ev.state == DEAD_DISPATCHER:
            self.swtich_manager.unregister_switch(dp)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        dp = msg.datapath
        dpid = dp.id

        ofproto = dp.ofproto
        parser = dp.ofproto_parser
        pkt = packet.Packet(msg.data)
        in_port = msg.match['in_port']

        i = iter(pkt)
        eth_pkt = six.next(i)
        assert type(eth_pkt) == ethernet.ethernet
        dst = eth_pkt.dst
        src = eth_pkt.src

        special_pkt = six.next(i)

        # check the type of this pkt
        # lldp
        if type(special_pkt) == lldp.lldp:
            self.lldp_manager.lldp_packet_in(ev)
            return
        # arp packet
        elif type(special_pkt) == arp.arp:
            # test
            # print('a arp packte is coming===============')
            # print('the src is ' + str(src))
            tenant_id = MacManager.get_tenant_id_with_vmac(src)
            self.arp_manager.handle_arp(
                datapath=dp,
                in_port=in_port,
                tenant_id=tenant_id,
                pkt=pkt
            )
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
            # first check whether dst is a host vmac
            if dst in self.vmac_to_pmac.keys():
                print('pkt from ' + src + ' to ' + dst)

                # find the route
                dst_dpid = MacManager.get_dpid_with_vmac(dst)
                path = self.topo_manager.get_path(dpid, dst_dpid)
                # install flow entry for only this switch
                datapath = self.datapathes[dpid]
                port = path[0][1]
                FlowManager.install_wildcard_sending_flow(
                    dp=datapath,
                    out_port=port,
                    dst_dpid=dst_dpid,
                    buffer_id=msg.buffer_id
                )

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

    def init_controller(self):
        hub.sleep(10)
        # detect connections between switch and gateway
        self._check_switch_gateway_connection()
        # init arp manager for gateway round robin
        self.arp_manager.init_arp()
        # install flow entry for table 4 on ovs (to adjust whether dst is a gateway or not)
        # del the missing flow in table 2 in every ovs and install new one (for register host)
        for dpid in self.datapathes.keys():
            if dpid in self.gateways.keys():
                continue
            else:
                self.flow_manager.install_gateway_adjustment_flow_entry(dpid)
                FlowManager.substitute_missing_flow(self.datapathes[dpid])



    def _check_switch_gateway_connection(self):
        for dpid in self.datapathes.keys():
            if dpid in self.gateways.keys():
                continue
            else:
                for gw_id in self.gateways.keys():
                    # find the port connecting to gateway
                    port1 = self.topo_manager.get_path(dpid, gw_id)[0][1]
                    port2 = self.topo_manager.get_path(gw_id, dpid)[0][1]

                    self.switch_gateway_connection[(dpid, gw_id)] = (port1, port2)
        # test
        print(self.switch_gateway_connection)
        return




























