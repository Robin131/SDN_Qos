import struct
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

class FlowModifier(object):
    def __init__(self):
        super(FlowModifier, self).__init__()

    def add_flow(self, datapath, priority,
                 match, instructions, table_id=0, buffer_id=None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        if not buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, flags=ofproto.OFPFF_SEND_FLOW_REM,
                                    table_id=table_id, instructions=instructions)
        else:
            mod = parser.OFPFlowMod(datapath=datapat, priority=priority, match=match,
                                    table_id=table_id, buffer_id=buffer_id,
                                    instructions=instructions)
        datapath.send_msg(mod)

    def install_missing_flow(self, ev):
        dp = ev.datapath
        ofproto = dp.ofproto
        parser = dp.ofproto_parser

        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(
            ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER
        )]

        instruction = [parser.OFPInstructionActions(
            ofproto.OFPIT_APPLY_ACTIONS, actions
        )]

        # TODO table 0 中为什么要有miss处理
        self.add_flow(dp, 0, match, instruction)
        # self.utils.add_flow(datapath, 0, match, instruction)
        self.add_flow(dp, 0, match, instruction, table_id=1)

    def transfer_src_pmac_to_vmac(self, ev, src, src_vmac):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        src_pmac = src

        match = parser.OFPMatch(eth_src=src_pmac)
        actions = [parser.OFPActionSetField(eth_dst=src_vmac)]
        instructions = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions),
                        parser.OFPInstructionGotoTable(table_id=1)]
        self.add_flow(datapath=datapath, priority=1, table_id=0, match=match,
                      instructions=instructions)

    def transfer_dst_vmac_to_pmac(self, ev, dst, dst_pmac):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        dst_vmac = dst

        match = parser.OFPMatch(eth_dst=dst_vmac)
        actions = [parser.OFPActionSetField(eth_dst=dst_pmac)]
        instructions = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions),
                        parser.OFPInstructionGotoTable(table_id=1)]
        self.add_flow(datapath=datapath, priority=1, table_id=0, match=match,
                      instructions=instructions)
