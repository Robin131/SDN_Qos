# -*- coding: utf-8 -*-
from ryu.ofproto import ofproto_v1_3 as ofp_13
import six
import math

from MacManager2 import MacManager

class FlowManager(object):

    TABLE6_MISSING_FLOW_ADDRESS = '00:00:00:00:00:00'
    TABLE8_MISSING_FLOW_ADDRESS = '00:00:00:00:00:01'


    def __init__(self,
                 datapathes,
                 gateways):
        super(FlowManager, self).__init__()

        self.datapathes = datapathes
        self.gateways = gateways

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
    def add_flow_with_timeout(datapath, priority,
                 match, instructions, idle_timeout=0, table_id=0, buffer_id=None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        if not buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, flags=ofproto.OFPFF_SEND_FLOW_REM,
                                    table_id=table_id, instructions=instructions,
                                    idle_timeout=idle_timeout)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority, match=match,
                                    table_id=table_id, buffer_id=buffer_id,
                                    instructions=instructions,
                                    idle_timeout=idle_timeout)
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
        actions5 = [
            parser.OFPActionSetField(eth_dst=FlowManager.TABLE6_MISSING_FLOW_ADDRESS),
            parser.OFPActionOutput(
                ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER
            )
        ]
        actions8 = [
            parser.OFPActionSetField(eth_dst=FlowManager.TABLE8_MISSING_FLOW_ADDRESS),
            parser.OFPActionOutput(
                ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER
            )
        ]

        instructions0 = [parser.OFPInstructionGotoTable(table_id=1)]
        instructions1 = [parser.OFPInstructionGotoTable(table_id=2)]
        instructions2 = [parser.OFPInstructionGotoTable(table_id=7)]
        instructions3 = [parser.OFPInstructionGotoTable(table_id=8)]
        instructions4 = [parser.OFPInstructionGotoTable(table_id=6)]
        instructions6 = [parser.OFPInstructionGotoTable(table_id=8)]
        instructions5 = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions5)]
        instructions7 = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        instructions8 = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions8)]

        FlowManager.add_flow(dp, 0, match, instructions0, table_id=0)
        FlowManager.add_flow(dp, 0, match, instructions1, table_id=1)
        FlowManager.add_flow(dp, 0, match, instructions2, table_id=2)
        FlowManager.add_flow(dp, 0, match, instructions3, table_id=3)
        FlowManager.add_flow(dp, 0, match, instructions4, table_id=4)
        FlowManager.add_flow(dp, 0, match, instructions5, table_id=5)
        FlowManager.add_flow(dp, 0, match, instructions6, table_id=6)
        FlowManager.add_flow(dp, 0, match, instructions7, table_id=7)
        FlowManager.add_flow(dp, 0, match, instructions8, table_id=8)

        return

    # install missing flow for gateway
    # TODO
    @staticmethod
    def install_missing_flow_for_gateway(dp):
        ofproto = dp.ofproto
        parser = dp.ofproto_parser

        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(
            ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER
        )]
        instruction0 = [parser.OFPInstructionGotoTable(table_id=1)]
        instruction1 = [parser.OFPInstructionGotoTable(table_id=2)]
        instruction2 = [parser.OFPInstructionGotoTable(table_id=3)]
        instruction3 = [parser.OFPInstructionGotoTable(4)]
        instruction4 = [parser.OFPInstructionGotoTable(5)]
        instruction6 = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]

        FlowManager.add_flow(dp, 0, match, instruction0, table_id=0)
        FlowManager.add_flow(dp, 0, match, instruction1, table_id=1)
        FlowManager.add_flow(dp, 0, match, instruction2, table_id=2)
        FlowManager.add_flow(dp, 0, match, instruction3, table_id=3)
        FlowManager.add_flow(dp, 0, match, instruction4, table_id=4)
        FlowManager.add_flow(dp, 0, match, instruction6, table_id=6)

        return

    @staticmethod
    def install_NAT_flow_for_gateway(dp, nat_port):
        ofproto = dp.ofproto
        parser = dp.ofproto_parser

        # arp from NAT
        match = parser.OFPMatch(in_port=nat_port, eth_dst='ff:ff:ff:ff:ff:ff')
        actions = [parser.OFPActionOutput(
            ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER
        )]
        instructions = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]

        FlowManager.add_flow(dp, 2, match, instructions, table_id=3)

        # data pkt to local switch
        match = parser.OFPMatch(in_port=nat_port)
        instructions = [parser.OFPInstructionGotoTable(6)]

        FlowManager.add_flow(dp, 1, match, instructions, table_id=3)
        return

    @staticmethod
    def install_other_datacenter_flow(dp, datacenter_id, port):
        ofproto = dp.ofproto
        parser = dp.ofproto_parser

        dst_mac_value = MacManager.get_datacenter_id_value_with_datacenter_id(datacenter_id)
        dst_mac_mask = MacManager.get_datacenter_id_mask()

        match = parser.OFPMatch(eth_dst=(dst_mac_value, dst_mac_mask))
        actions = [parser.OFPActionOutput(port)]
        instructions = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]

        FlowManager.add_flow(dp, 1, match, instructions, table_id=5)
        return

    # check whether pkt is to this datacenter in gateway
    @staticmethod
    def install_this_datacenter_flow(dp, datacenter_id):
        ofproto = dp.ofproto
        parser = dp.ofproto_parser

        dst_mac_value = MacManager.get_datacenter_id_value_with_datacenter_id(datacenter_id)
        dst_mac_mask = MacManager.get_datacenter_id_mask()

        match = parser.OFPMatch(eth_dst=(dst_mac_value, dst_mac_mask))
        instructions = [parser.OFPInstructionGotoTable(6)]

        FlowManager.add_flow(dp, 1, match, instructions, table_id=4)

    # install statistics flow entry for gateway
    @staticmethod
    def install_statistics_flow(gw, dpids, datacenter_id):
        ofproto = gw.ofproto
        parser = gw.ofproto_parser

        for dpid in dpids:
            dst = MacManager.get_vmac_value_with_datacenter_id_and_dpid(datacenter_id, dpid)
            mask = MacManager.get_mask_for_datacenter_id_and_dpid()

            match = parser.OFPMatch(eth_src=(dst, mask))
            instructions = [parser.OFPInstructionGotoTable(3)]

            FlowManager.add_flow(gw, 1, match, instructions, table_id=2)
        return


    # install flow entry to distinguish private subnet and Internet
    @staticmethod
    def install_subnet_flow(ev, subnets):
        dp = ev.datapath
        ofproto = dp.ofproto
        parser = dp.ofproto_parser

        for subnet in subnets:
            match = parser.OFPMatch(eth_type=0x800, ipv4_dst=subnet)
            instructions = [parser.OFPInstructionGotoTable(table_id=4)]
            FlowManager.add_flow(dp, 1, match, instructions, table_id=3)

    # install sending flow for both ovs and gateway
    # adjust table_id according to dpid
    def install_wildcard_sending_flow(self, dp, out_port, dst_dpid, buffer_id=None, table_id=7):
        dpid = dp.id
        parser = dp.ofproto_parser
        ofproto = dp.ofproto

        vmac_value = MacManager.get_vmac_value_with_wildcard_on_dpid(dst_dpid)
        vmac_mask = MacManager.get_vmac_mask_with_wildcard_on_dpid()

        match = parser.OFPMatch(eth_dst=(vmac_value, vmac_mask))
        actions = [parser.OFPActionOutput(out_port)]
        instruction = [parser.OFPInstructionActions(
            ofproto.OFPIT_APPLY_ACTIONS, actions
        )]

        # if gateway then install in table_6
        if dpid in self.gateways.keys():
            FlowManager.add_flow(datapath=dp, priority=1, match=match, instructions=instruction,
                                 table_id=6, buffer_id=buffer_id)
        else:
            FlowManager.add_flow(datapath=dp, priority=1, match=match, instructions=instruction,
                                 table_id=table_id, buffer_id=buffer_id)

    @staticmethod
    def install_adjust_datacenter_flow(ev, datacenter_id):
        dp = ev.datapath
        ofproto = dp.ofproto
        parser = dp.ofproto_parser

        datacenter_id_value = MacManager.get_datacenter_id_value_with_datacenter_id(datacenter_id)
        datacenter_id_mask = MacManager.get_datacenter_id_mask()

        match = parser.OFPMatch(eth_dst=(datacenter_id_value, datacenter_id_mask))
        instructions = [parser.OFPInstructionGotoTable(7)]

        FlowManager.add_flow(dp, 1, match, instructions, table_id=6, buffer_id=None)

        return

    # check priority in gateway
    # only check priority 1
    @staticmethod
    def check_priority_on_gateway(gateway):
        ofproto = gateway.ofproto
        parser = gateway.ofproto_parser

        level_value = MacManager.get_vmac_value_with_tenant_level(1)
        mask = MacManager.get_tenant_level_mask()

        match = parser.OFPMatch(eth_src=(level_value, mask))
        instructions = [parser.OFPInstructionGotoTable(3)]
        FlowManager.add_flow(gateway, 1, match, instructions, table_id=0)

        return

    @staticmethod
    def substitute_missing_flow(dp):
        ofproto = dp.ofproto
        parser = dp.ofproto_parser

        # first delete flow entry
        match = parser.OFPMatch()
        instructions = [parser.OFPInstructionGotoTable(7)]

        cookie = cookie_mask = 0
        idle_timeout = hard_timeout = 0

        req = parser.OFPFlowMod(dp, cookie, cookie_mask, 2,
                                ofproto.OFPFC_DELETE_STRICT,
                                idle_timeout, hard_timeout,
                                0, ofproto.OFP_NO_BUFFER,
                                ofproto.OFPP_ANY, ofproto.OFPG_ANY,
                                ofproto.OFPFF_SEND_FLOW_REM,
                                match, instructions)
        dp.send_msg(req)

        # then install new one
        match = parser.OFPMatch()
        instructions = [parser.OFPInstructionGotoTable(3)]
        FlowManager.add_flow(dp, 0, match, instructions, table_id=2)

    @staticmethod
    def install_arp_flow_entry(dp):
        ofproto = dp.ofproto
        parser = dp.ofproto_parser

        match = parser.OFPMatch(eth_dst='ff:ff:ff:ff:ff:ff')
        actions = [parser.OFPActionOutput(
            ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER
        )]
        instructions = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]

        FlowManager.add_flow(dp, 1, match, instructions, table_id=3)


    def install_gateway_adjustment_flow_entry(self, dpid):
        dp = self.datapathes[dpid]
        parser = dp.ofproto_parser
        ofproto = dp.ofproto

        for gateway_id in self.gateways.keys():
            vmac_value = MacManager.get_vmac_value_with_wildcard_on_dpid(gateway_id)
            vmac_mask = MacManager.get_vmac_mask_with_wildcard_on_dpid()

            match = parser.OFPMatch(eth_dst=(vmac_value, vmac_mask))
            instructions = [parser.OFPInstructionGotoTable(table_id=5)]

            FlowManager.add_flow(datapath=dp, priority=1, match=match, instructions=instructions,
                      table_id=4, buffer_id=None)

        return

    @staticmethod
    def install_balance_flow_entry_for_gateway(gateway, dpid, this_datacenter_id, out_port,
                                               meter_id=None):
        parser = gateway.ofproto_parser
        ofproto = gateway.ofproto

        value = MacManager.get_vmac_value_with_datacenter_id_and_dpid(this_datacenter_id, dpid)
        mask = MacManager.get_mask_for_datacenter_id_and_dpid()

        match = parser.OFPMatch(eth_src=(value, mask))
        actions = [parser.OFPActionOutput(out_port)]
        if not meter_id:
            instructions = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        else:
            instructions = [
                parser.OFPInstructionMeter(meter_id, ofproto.OFPIT_METER),
                parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)
            ]

        FlowManager.add_flow(datapath=gateway, priority=1, match=match, instructions=instructions,
                             table_id=1, buffer_id=None)
        return

    @staticmethod
    def install_limit_speed_flow_entry_for_gateway(gateway, dpid, this_datacenter_id, meter_id):
        parser = gateway.ofproto_parser
        ofproto = gateway.ofproto

        value = MacManager.get_vmac_value_with_datacenter_id_and_dpid(this_datacenter_id, dpid)
        mask = MacManager.get_mask_for_datacenter_id_and_dpid()

        match = parser.OFPMatch(eth_src=(value, mask))
        instructions = [
            parser.OFPInstructionMeter(meter_id, ofproto.OFPIT_METER),
            parser.OFPInstructionGotoTable(2)
        ]
        FlowManager.add_flow(datapath=gateway, priority=1, match=match, instructions=instructions,
                             table_id=1, buffer_id=0)
        return




