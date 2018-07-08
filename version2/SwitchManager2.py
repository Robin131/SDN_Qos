import copy
from MacManager2 import MacManager
from FlowManager2 import FlowManager


# flow entry for switch
# 0 : src_pmac -> src_vmac
# 1 : dst_vmac -> dst_pmac
# 2 : receiving flow entry (send pkt to host)
# 3 : check whether dst_vmac is public or private (yes 4, no gw)
# 4 : check whether dst_vmac is a gateway address (yes 6, no 5)
# 5 : check whether dst_vmac is in local datacenter (yes 7, no gw)
# 6 : replace dst_mac according to ip, send to gw
# 7 : send in local datacenter


class SwitchManager(object):
    def __init__(self,
                 datapathes,
                 dpid_to_ports,
                 datacenter_id,
                 dpid_to_vmac,
                 lldp_manager,
                 meters):
        super(SwitchManager, self).__init__()

        self.datapathes = datapathes
        self.dpid_to_ports = dpid_to_ports
        self.datacenter_id = datacenter_id
        self.dpid_to_vmac = dpid_to_vmac
        self.lldp_manager = lldp_manager
        self.meters = meters

    def register_switch(self, ev):
        datapath = ev.datapath
        dpid = datapath.id
        self.datapathes[dpid] = datapath

        ports = copy.copy(datapath.ports)
        self.dpid_to_ports[dpid] = ports

        vmac = MacManager.get_vmac_new_switch(dpid=dpid, datacenter_id=self.datacenter_id)
        self.dpid_to_vmac[dpid] = vmac
        self.lldp_manager.lldp_detect(datapath)
        FlowManager.install_missing_flow_for_switch(ev)

        self.meters[dpid] = {}

    # TODO finish this function
    def unregister_switch(self, datapath):
        return

