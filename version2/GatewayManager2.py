# -*- coding: utf-8 -*-
from ryu.lib import hub

from FlowManager2 import FlowManager
from Util2 import Util

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
                 gateway_datacenter_port_max_speed,
                 balance_time_interval,
                 datapathes):
        super(GatewayManager, self)

        self.gateways = gateways
        self.potential_gateway = potential_gateway
        self.datacenter_id = datacenter_id
        self.gateway_flow_table_inquire_time = gateway_flow_table_inquire_time
        self.gateway_port_inquire_time = gateway_port_inquire_time
        self.gateway_datacenter_port_max_speed = gateway_datacenter_port_max_speed
        self.balance_time_interval = balance_time_interval
        self.datapathes = datapathes

        self.balance_threshold = 0.75

        self.dpid_flow = {}                 # dpid(switch) -> amount of flow
        self.temp_dpid_flow = {}            # {dpid -> {'duration', 'byte_count'}}
        self.gateway_port_speed = {}        # dpid -> {port_no -> speed}
        self.temp_port_speed = {}           # {dpid -> {'duration', 'rx_bytes', 'tx_bytes'}}

    def register_gateway(self, ev):
        datapath = ev.datapath
        dpid = datapath.id

        # init statistics record
        self.dpid_flow[dpid] = 0
        Util.add2DimDict(self.temp_dpid_flow, dpid, 'duration', 0)
        Util.add2DimDict(self.temp_dpid_flow, dpid, 'byte_count', 0)

        self.temp_dpid_flow[dpid] = 0
        Util.add2DimDict(self.temp_port_speed, dpid, 'duration', 0)
        Util.add2DimDict(self.temp_port_speed, dpid, 'rx_bytes', 0)
        Util.add2DimDict(self.temp_port_speed, dpid, 'tx_bytes', 0)

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
            duration = stat.duration_sec
            byte_difference = abs(self.temp_dpid_flow[dpid] - byte_count)
            time_interval = abs(duration - self.temp_dpid_flow[dpid][duration])
            speed = byte_difference / time_interval

            self.temp_dpid_flow[dpid]['duration'] = duration
            self.temp_dpid_flow[dpid]['byte_count'] = byte_count
            self.dpid_flow[dpid] = speed
        return

    # handle datacenter port info
    def gateway_port_reply_handler(self, ev):
        msg = ev.msg
        dp = msg.datapath
        dpid = dp.id

        for stat in ev.msg.body:
            duration = stat.duration_sec
            rx_bytes = stat.rx_bytes
            tx_bytes = stat.tx_bytes

            all_bytes = abs(self.temp_port_speed[dpid]['rx_bytes'] - rx_bytes) + \
                abs(self.temp_port_speed[dpid]['tx_bytes'] - tx_bytes)
            time_interval = duration - self.temp_port_speed[dpid]['duration']
            speed = all_bytes / time_interval

            # update record
            self.temp_port_speed[dpid]['duration'] = duration
            self.temp_port_speed[dpid]['rx_bytes'] = rx_bytes
            self.temp_port_speed[dpid]['tx_bytes'] = tx_bytes

            self.gateway_port_speed[dpid] = speed

        return

    # a hub to balance gateway
    def gateway_balance_hub(self):
        hub.sleep(20)
        while(True):
            hub.sleep(self.balance_time_interval)
            max_speed = self.gateway_datacenter_port_max_speed

            for gw_id in self.gateway_port_speed.keys():
                for port_no, speed in self.gateway_port_speed[gw_id].items():
                    # check whether too fast
                    if speed >= self.balance_threshold * max_speed:
                        self.adjust_balabce()
                    else:
                        continue
        return

    # try
