# -*- coding: utf-8 -*-
from FlowManager2 import FlowManager


# flow entry for switch for gateway
# 0 : check whether from NAT or arp from NAT (arp to controller, nat to 3, others to 1)     ok
# 1 : check whether mac_dst is to this datacenter (yes 3, no 2)                             ok
# 2 : send to other datacenters                                                             ok
# 3 : send to local switch

class GatewayManager(object):
    def __init__(self,
                 gateways,
                 potential_gateway,
                 datacenter_id):
        super(GatewayManager, self)

        self.gateways = gateways
        self.potential_gateway = potential_gateway
        self.datacenter_id = datacenter_id


    def register_gateway(self, ev):
        datapath = ev.datapath
        dpid = datapath.id

        if dpid in self.potential_gateway.keys():
            self.gateways[dpid] = self.potential_gateway[dpid]

        FlowManager.install_missing_flow_for_gateway(datapath)
        FlowManager.install_this_datacenter_flow(datapath, self.datacenter_id)

        record = self.gateways[dpid]
        for (key, value) in record.items():
            if key == 'NAT':
                FlowManager.install_NAT_flow_for_gateway(datapath, value)
            # port to other datacenters
            elif isinstance(key, int):
                FlowManager.install_other_datacenter_flow(datapath, key, value)

        return