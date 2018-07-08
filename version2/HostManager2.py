from ryu.lib.packet import packet, ethernet
from multiprocessing import Queue
from ryu.lib import hub

from MacManager2 import MacManager
from FlowManager2 import FlowManager

class HostManager(object):
    def __init__(self,
                 host_pmac,
                 mac_manager,
                 datacenter_id,
                 pmac_to_vmac,
                 vmac_to_pmac):
        super(HostManager, self).__init__()

        self.host_pmac = host_pmac
        self.mac_manager = mac_manager
        self.datacenter_id = datacenter_id
        self.pmac_to_vmac = pmac_to_vmac
        self.vmac_to_pmac = vmac_to_pmac

    def register_host(self, ev):
        msg = ev.msg
        dp = msg.datapath
        dpid = dp.id

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]
        src = eth.src
        in_port = msg.match['in_port']

        tenant_id = self.host_pmac[src]
        src_vmac = self.mac_manager.get_vmac_new_host(
            dpid=dpid, port_id=in_port,
            datacenter_id=self.datacenter_id,
            tenant_id=tenant_id
        )

        self.pmac_to_vmac[src] = src_vmac
        self.vmac_to_pmac[src_vmac] = src
        print(self.vmac_to_pmac)

        # TODO add meter feature
        FlowManager.transfer_src_pmac_to_vmac(ev, src, src_vmac)
        FlowManager.transfer_dst_vmac_to_pmac(ev, src_vmac, src)
        FlowManager.install_receiving_flow_entry(dp, src, in_port)

        # TODO bulid host queue for gateway

        return