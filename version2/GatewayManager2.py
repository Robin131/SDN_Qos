# -*- coding: utf-8 -*-
from ryu.lib import hub

from FlowManager2 import FlowManager


# flow entry for switch for gateway
# 0 : check whether from NAT or arp from NAT (arp to controller, nat to 3, others to 1)     ok
# 1 : check whether mac_dst is to this datacenter (yes 3, no 2)                             ok
# 2 : send to other datacenters                                                             ok
# 3 : send to local switch

# flow entry for switch for gateway
# 0 : check whether priority 1 (yes 3, no 1)
# 1 : send pkt to other gateway for Qos (go 2)                                              ok
# 2 : statistics (go 3)                                                                     ok
# 3 : check whether from NAT or arp from NAT (arp to controller, nat to 6, others to 4)     ok
# 4 : check whether mac_dst is to this datacenter (yes 6, no 5)                             ok
# 5 : send to other datacenters                                                             ok
# 6 : send to local switch                                                                  ok

class GatewayManager(object):
    def __init__(self,
                 gateways,
                 potential_gateway,
                 datacenter_id,
                 gateway_flow_table_inquire_time,
                 gateway_port_inquire_time,
                 datapathes):
        super(GatewayManager, self)

        self.gateways = gateways
        self.potential_gateway = potential_gateway
        self.datacenter_id = datacenter_id
        self.gateway_flow_table_inquire_time = gateway_flow_table_inquire_time
        self.gateway_port_inquire_time = gateway_port_inquire_time
        self.datapathes = datapathes

        # dpid -> amount of flow
        self.dpid_flow = {}
        self.temp_dpid_flow = {}

        # dpid -> {port_no -> speed}

    def register_gateway(self, ev):
        datapath = ev.datapath
        dpid = datapath.id

        self.dpid_flow[dpid] = 0
        self.temp_dpid_flow[dpid] = 0

        if dpid in self.potential_gateway.keys():
            self.gateways[dpid] = self.potential_gateway[dpid]

        FlowManager.install_missing_flow_for_gateway(datapath)
        FlowManager.install_this_datacenter_flow(datapath, self.datacenter_id)
        FlowManager.check_priority_on_gateway(datapath)

        record = self.gateways[dpid]
        for (key, value) in record.items():
            if key == 'NAT':
                FlowManager.install_NAT_flow_for_gateway(datapath, value)
            # port to other datacenters
            elif isinstance(key, int):
                FlowManager.install_other_datacenter_flow(datapath, key, value)

        return

    # a hub to inquire flow table info on gateway
    def inquiry_gateway_flow_table_info(self):
        while (True):
            hub.sleep(self.gateway_flow_table_inquire_time)
            table_ids = [2]
            for gw_id in self.gateways.keys():
                gw = self.datapathes[gw_id]
                ofproto = gw.ofproto
                parser = gw.ofproto_parser

                for id in table_ids:
                    req = parser.OFPFlowStatsRequest(datapath=gw, table_id=id)
                    gw.send_msg(req)

    # a hub to inquire gre port connecting datacenters
    def inquiry_gateway_datacenter_port(self):
        while (True):
            hub.sleep(self.gateway_port_inquire_time)
            for gw_id in self.gateways.keys():
                for dst, port_no in self.gateways[gw_id]:
                    if type(dst) == int:
                        datapath = self.datapathes[gw_id]
                        ofp_parser = datapath.ofproto_parser

                        req = ofp_parser.OFPPortStatsRequest(datapath, 0, port_no)
                        datapath.send_msg(req)


    # handle gateway statistics info
    def gateway_statistics_handler(self, ev):
        msg = ev.msg
        dp = msg.datapath
        dpid = dp.id

        for stat in ev.msg.body:
            eth_src = stat.match.get('eth_src')
            if eth_src is None:
                continue

            # decode dpid
            hex_str = ''
            for i in range(len(eth_src[1])):
                if eth_src[1][i] == 'f':
                    hex_str += eth_src[0][i]
            dpid = int(hex_str, 16)

            # record flow amount
            byte_count = stat.byte_count
            byte_difference = self.temp_dpid_flow[dpid] - byte_count
            self.temp_dpid_flow[dpid] = byte_count
            self.dpid_flow[dpid] = byte_difference
        return

    # handle datacenter port info
    def gateway_port_reply_handler(self, ev):




