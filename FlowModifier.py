# -*- coding: utf-8 -*-
from ryu.ofproto import ofproto_v1_3 as ofp_13
import six
import math

class FlowModifier(object):
    def __init__(self, datapathes):
        super(FlowModifier, self).__init__()
        self.datapathes = datapathes

        self.change_route_priority = 5

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
        instruction0 = [
            parser.OFPInstructionGotoTable(table_id=1)
        ]
        instruction1 = [
            parser.OFPInstructionGotoTable(table_id=2)
        ]
        instruction2 = [
            parser.OFPInstructionGotoTable(table_id=3)
        ]
        self.add_flow(dp, 0, match, instruction0)
        self.add_flow(dp, 0, match, instruction1, table_id=1)
        self.add_flow(dp, 0, match, instruction2, table_id=2)


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
        quotient = unit // 8
        remainder = unit % 8

        for i in range(quotient):
            if i == 0:
                res = six.int2byte(255)
            else:
                res += six.int2byte(255)

        k = 7
        temp = 0
        for i in range(remainder):
            temp += 2 ** k
            k -= 1

        return res + six.int2byte(temp)


    def _get_subnet_ip_value(self, subnet_ip):
        ip = subnet_ip.split('/')[0]
        mask_num = int(subnet_ip.split('/')[1])

        quotient = mask_num // 8
        remainder = mask_num % 8


        for i in range(quotient):
            if i == 0:
                res = six.int2byte(int(ip[i]))
            else:
                res += six.int2byte(int(ip[i]))

        end = int(ip[quotient])

        k = 7
        temp = 0
        for i in range(remainder):
            temp += 2**k
            k -= 1

        mask_end = end & temp

        # test
        print(str(res))

        return res + six.int2byte(mask_end)


    # path: [(dpid, port_id), (dpid, port_id) .....]
    def change_route_for_two_hosts(self, host1_vmac, host2_vmac, path):
        if len(path) <=2:
            return

        path.reverse()

        for i in range(1, len(path)):
            front_index = i - 1
            next_dpid = path[front_index][0]
            this_port = path[i][1]
            this_dpid = path[i][0]

            this_datapath = self.datapathes[this_dpid]
            ofproto = this_datapath.ofproto
            parser = this_datapath.ofproto_parser

            match = parser.OFPMatch()
            match.append_field(header=ofp_13.OXM_OF_ETH_DST_W,
                               mask=self._get_switch_id_mask(),
                               value=self._get_switch_id_value(next_dpid)
                               )
            actions = [parser.OFPActionOutput(this_port)]
            instruction = [parser.OFPInstructionActions(
                ofproto.OFPIT_APPLY_ACTIONS, actions
            )]

            # TODO add idle_time
            self.add_flow(datapath=this_datapath,
                          priority=self.change_route_priority,
                          match=match,
                          instructions=instruction,
                          table_id=2,
                          buffer_id=None)


            if i == len(path) - 1:
                self.change_route_priority += 1































