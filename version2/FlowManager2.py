# -*- coding: utf-8 -*-
from ryu.ofproto import ofproto_v1_3 as ofp_13
import six
import math

from MacManager2 import MacManager

class FlowManager(object):
    def __init__(self,
                 datapathes):
        super(FlowManager, self).__init__()

        self.datapathes = datapathes

    @staticmethod
    def add_flow(datapath, priority,
                 match, instructions, table_id=0, buffer_id=None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        if not buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, flags=ofproto.OFPFF_SEND_FLOW_REM,
                                    table_id=table_id, instructions=instructions)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority, match=match,
                                    table_id=table_id, buffer_id=buffer_id,
                                    instructions=instructions)
        datapath.send_msg(mod)

    @staticmethod
    def transfer_src_pmac_to_vmac(ev, src, src_vmac, meter_id=None):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        src_pmac = src

        match = parser.OFPMatch(eth_src=src_pmac)
        actions = [parser.OFPActionSetField(eth_src=src_vmac)]
        if not meter_id:
            instructions = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions),
                            parser.OFPInstructionGotoTable(table_id=1)]
        else:
            instructions = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions),
                            parser.OFPInstructionMeter(meter_id, ofproto.OFPIT_METER),
                            parser.OFPInstructionGotoTable(table_id=1)]

        FlowManager.add_flow(datapath=datapath, priority=1, table_id=0, match=match,
                      instructions=instructions)

    @staticmethod
    def transfer_dst_vmac_to_pmac(ev, dst, dst_pmac):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        dst_vmac = dst

        match = parser.OFPMatch(eth_dst=dst_vmac)
        actions = [parser.OFPActionSetField(eth_dst=dst_pmac)]
        instructions = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions),
                        parser.OFPInstructionGotoTable(table_id=2)]
        FlowManager.add_flow(datapath=datapath, priority=1, table_id=1, match=match,
                      instructions=instructions)

    @ staticmethod
    def install_receiving_flow_entry(dp, src_pmac ,in_port):
        ofproto = dp.ofproto
        parser = dp.ofproto_parser

        actions = [parser.OFPActionOutput(in_port)]
        instruction = [parser.OFPInstructionActions(
            ofproto.OFPIT_APPLY_ACTIONS, actions
        )]
        match = parser.OFPMatch(eth_dst=src_pmac)
        FlowManager.add_flow(datapath=dp, priority=2, match=match, instructions=instruction, table_id=2)

    # TODO, now just send from 2 to 7
    # install missing flow
    @staticmethod
    def install_missing_flow_for_switch(ev):
        dp = ev.datapath
        ofproto = dp.ofproto
        parser = dp.ofproto_parser

        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(
            ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER
        )]
        instructions0 = [parser.OFPInstructionGotoTable(table_id=1)]
        instructions1 = [parser.OFPInstructionGotoTable(table_id=2)]
        instructions2 = [parser.OFPInstructionGotoTable(table_id=7)]
        instructions7 = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]

        FlowManager.add_flow(dp, 0, match, instructions0, table_id=0)
        FlowManager.add_flow(dp, 0, match, instructions1, table_id=1)
        FlowManager.add_flow(dp, 0, match, instructions2, table_id=2)
        FlowManager.add_flow(dp, 0, match, instructions7, table_id=7)

        return

    @staticmethod
    def install_wildcard_sending_flow(dp, out_port, dst_dpid, buffer_id=None, table_id=7):
        dpid = dp.id
        parser = dp.ofproto_parser
        ofproto = dp.ofproto

        vmac_value = MacManager.get_vmac_value_with_wildcard_on_dpid(dpid)
        vmac_mask = MacManager.get_vmac_mask_with_wildcard_on_dpid()

        match = parser.OFPMatch(eth_src=(vmac_value, vmac_mask))
        actions = [parser.OFPActionOutput(out_port)]
        instruction = [parser.OFPInstructionActions(
            ofproto.OFPIT_APPLY_ACTIONS, actions
        )]
        FlowManager.add_flow(datapath=dp, priority=1, match=match, instructions=instruction,
                      table_id=table_id, buffer_id=buffer_id)


