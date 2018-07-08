# -*- coding: utf-8 -*-


class GatewayManager(object):
    def __init__(self,
                 gateways,
                 potential_gateway):
        super(GatewayManager, self)

        self.gateways = gateways
        self.potential_gateway = potential_gateway




    def register_gateway(self, ev):
        datapath = ev.datapath
        dpid = datapath.id

        if dpid in self.potential_gateway.keys():
            self.gateways[dpid] = self.potential_gateway[dpid]

        return