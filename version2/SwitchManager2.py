import copy
from MacManager2 import MacManager

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

    def register_switch(self, datapath):
        dpid = datapath.dpid
        self.datapathes[dpid] = datapath

        ports = copy.copy(datapath.ports)
        self.dpid_to_ports[dpid] = ports

        vmac = MacManager.get_vmac_new_switch(dpid=dpid, datacenter_id=self.datacenter_id)
        self.dpid_to_vmac[dpid] = vmac
        self.lldp_manager.lldp_detect(datapath)

        self.meters[dpid] = {}

    # TODO finish this function
    def unregister_switch(self, datapath):
        return

