# -*- coding: utf-8 -*-
from ryu.ofproto import ofproto_v1_3 as ofp_13
import six
import math

class FlowModifier(object):
    def __init__(self, datapathes):
        super(FlowModifier, self).__init__()
        self.datapathes = datapathes

    def add_flow(self, datapath, priority,
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

    def install_missing_flow(self, ev):
        dp = ev.datapath
        ofproto = dp.ofproto
        parser = dp.ofproto_parser

        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(
            ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER
        )]

        instruction0 = [
            parser.OFPInstructionGotoTable(table_id=1)
        ]

        instruction1 = [
            parser.OFPInstructionGotoTable(table_id=2)
        ]

        instruction2 = [parser.OFPInstructionActions(
            ofproto.OFPIT_APPLY_ACTIONS, actions
        )]

        self.add_flow(dp, 0, match, instruction0)
        self.add_flow(dp, 0, match, instruction1, table_id=1)
        self.add_flow(dp, 0, match, instruction2, table_id=2)

    def install_missing_flow_for_gateway(self, ev):
        dp = ev.datapath
        ofproto = dp.ofproto
        parser = dp.ofproto_parser

        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(
            ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER
        )]
        instruction = [
            parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)
        ]
        self.add_flow(dp, 0, match, instruction, table_id=0)

    def transfer_src_pmac_to_vmac(self, ev, src, src_vmac, meter_id=None):
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
                        parser.OFPInstructionGotoTable(table_id=2)]
        self.add_flow(datapath=datapath, priority=1, table_id=1, match=match,
                      instructions=instructions)

    # install sending flow ((src, dst) to out_port on datapath)
    def install_sending_flow(self, datapath, out_port, src_vmac, dst_vmac, buffer_id=None, table_id=2):
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto
        actions = [parser.OFPActionOutput(out_port)]
        instruction = [parser.OFPInstructionActions(
            ofproto.OFPIT_APPLY_ACTIONS, actions
        )]
        match = parser.OFPMatch(eth_src=src_vmac, eth_dst=dst_vmac)
        self.add_flow(datapath=datapath, priority=1, match=match, instructions=instruction,
                      table_id=table_id, buffer_id=buffer_id)

    def install_receiving_flow_entry(self, dp, src_pmac ,in_port):
        ofproto = dp.ofproto
        parser = dp.ofproto_parser

        actions = [parser.OFPActionOutput(in_port)]
        instruction = [parser.OFPInstructionActions(
            ofproto.OFPIT_APPLY_ACTIONS, actions
        )]
        match = parser.OFPMatch(eth_dst=src_pmac)
        self.add_flow(datapath=dp, priority=2, match=match, instructions=instruction, table_id=2)

    # wildcard for sending flow (form dp to datapath with id dst_dpid through out_port)
    def install_wildcard_sending_flow(self, dp, out_port, dst_dpid, buffer_id=None, table_id=2):
        dpid = dp.id
        parser = dp.ofproto_parser
        ofproto = dp.ofproto
        match = parser.OFPMatch()

        match.append_field(header=ofp_13.OXM_OF_ETH_DST_W,
                           mask=self._get_switch_id_mask(),
                           value=self._get_switch_id_value(dst_dpid)
                           )
        actions = [parser.OFPActionOutput(out_port)]
        instruction = [parser.OFPInstructionActions(
            ofproto.OFPIT_APPLY_ACTIONS, actions
        )]
        self.add_flow(datapath=dp, priority=1, match=match, instructions=instruction,
                      table_id=table_id, buffer_id=buffer_id)


    # install ip wildcard flow entry for gateway according to subnet ip
    def install_ip_wildcard_flow_with_subnet_ip(self, dpid, subnet_ip, out_port):
        dp = self.datapathes[dpid]
        parser = dp.ofproto_parser
        ofproto = dp.ofproto

        match = parser.OFPMatch(eth_type=0x800)
        match.append_field(header=ofp_13.OXM_OF_IPV4_DST,
                           mask=self._get_sunbet_ip_mask(subnet_ip),
                           value=self._get_subnet_ip_value(subnet_ip))
        actions = [parser.OFPActionOutput(out_port)]
        instruction = [parser.OFPInstructionActions(
            ofproto.OFPIT_APPLY_ACTIONS, actions
        )]
        self.add_flow(datapath=dp, priority=1, match=match, instructions=instruction,
                      table_id=0, buffer_id=None)


        return

    # install missing flow entry for gateway (send to Nat directly)
    def intall_missing_flow_entry_for_gateway(self, gateway_id, nat_port):
        dp = self.datapathes[gateway_id]
        parser = dp.ofproto_parser
        ofproto = dp.ofproto

        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(nat_port)]
        instruction = [parser.OFPInstructionActions(
            ofproto.OFPIT_APPLY_ACTIONS, actions
        )]
        self.add_flow(datapath=dp, priority=1, match=match, instructions=instruction,
                      table_id=0, buffer_id=None)



    def _get_switch_id_mask(self):
        return six.int2byte(0) * 3 + six.int2byte(255) * 2

    def _get_datacenter_id_mask(self):
        return six.int2byte(15 * 16)

    def _get_switch_id_value(self, dpid):
        return six.int2byte(0) * 3 + six.int2byte(int(math.floor(dpid / 256)))\
               + six.int2byte(int(math.floor(dpid % 256)))

    def _get_datacenter_id_value(self, datacenter_id):
        assert datacenter_id < 16
        return six.int2byte(datacenter_id * 16)

    def _get_sunbet_ip_mask(self, subnet_ip):
        unit = int(subnet_ip.split('/')[1])
        return six.int2byte(15) * unit

    def _get_subnet_ip_value(self, subnet_ip):
        ip = subnet_ip.split('/')[0]
        mask_num = subnet_ip.split('/')[1]

        quotient = mask_num // 8
        remainder = mask_num % 8

        res = ''

        for i in range(quotient):
            res += six.int2byte(int(ip[i]))

        end = int(ip[quotient])

        k = 7
        temp = 0
        for i in range(remainder):
            temp += 2**k
            k -= 1

        mask_end = end & temp

        return res + six.int2byte(mask_end)


        # TODO