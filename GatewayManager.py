
class GatewayManager(object):
    def __init__(self, possibie_gatewats, gateways, gateway_arp_table, dpid_to_vmac, flow_manager):
        super(GatewayManager, self)

        self.possible_gateways = possibie_gatewats
        self.gateways = gateways
        self.flow_manager = flow_manager
        self.gateway_arp_table = gateway_arp_table
        self.dpid_to_vmac = dpid_to_vmac

    def register_gateway(self, dpid):
        self.gateways[dpid] = self.possible_gateways[dpid]
        # install flow table for other datacenter and Nat server
        for (port_no, dst) in self.gateways[dpid].items():
            # datacenter
            if dst != 'NAT':
                self.flow_manager.install_datacenter_flow(self, dst, port_no, dpid)
                return
            # Internet (Nat)
            else:
                gateway_vmac = self.dpid_to_vmac[dpid]
                self.flow_manager.install_internet_flow(gateway_vmac=gateway_vmac,
                                                        out_port=port_no,
                                                        gateway_id=dpid)
                return

    def get_internet_port(self, gateway_id):
        for (port_no, dst) in self.gateways[gateway_id].items():
            if dst == 'NAT':
                return port_no
            else:
                continue








