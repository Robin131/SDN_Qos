import copy
from MacManager2 import MacManager
from FlowManager2 import FlowManager


# flow entry for switch
# 0 : src_pmac -> src_vmac                                              ok
# 1 : dst_vmac -> dst_pmac                                              ok
# 2 : receiving flow entry (send pkt to host)                           ok
# 3 : check whether ip_dst is public or private (yes 4, no 8)(arp)      ok
# 4 : check whether dst_vmac is a gateway address (yes 5, no 6)         ok
# 5 : add dst_mac according to ip, send to 6                            ok
# 6 : check whether dst_vmac is in local datacenter (yes 7, no 8)       ok
# 7 : send in local datacenter                                          ok
# 8 : send to gateway according to host_vmac                            ok


class SwitchManager(object):
    def __init__(self,
                 datapathes,
                 dpid_to_ports,
                 datacenter_id,
                 dpid_to_vmac,
                 lldp_manager,
                 meters,
                 subnets,
                 potential_gateway):
        super(SwitchManager, self).__init__()

        self.datapathes = datapathes
        self.dpid_to_ports = dpid_to_ports
        self.datacenter_id = datacenter_id
        self.dpid_to_vmac = dpid_to_vmac
        self.lldp_manager = lldp_manager
        self.meters = meters
        self.subnets = subnets
        self.potential_gateway = potential_gateway

    def register_switch(self, ev):
        datapath = ev.datapath
        dpid = datapath.id
        self.datapathes[dpid] = datapath

        ports = copy.copy(datapath.ports)
        self.dpid_to_ports[dpid] = ports

        vmac = MacManager.get_vmac_new_switch(dpid=dpid, datacenter_id=self.datacenter_id)
        self.dpid_to_vmac[dpid] = vmac
        self.lldp_manager.lldp_detect(datapath)

        if dpid in self.potential_gateway.keys():
            return

        FlowManager.install_subnet_flow(ev, self.subnets)       # table 3
        FlowManager.install_adjust_datacenter_flow(ev, self.datacenter_id)
        FlowManager.install_missing_flow_for_switch(ev)

        self.meters[dpid] = {}

    # TODO finish this function
    def unregister_switch(self, datapath):
        return

