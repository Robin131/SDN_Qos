class HostManager(object):
    def __init__(self, arp_table, host_pmac):
        super(HostManager, self).__init__()

        self.arp_table = arp_table
        self.host_pmac = host_pmac

    def get_tenant_id(self, vm_pmac):
        return self.host_pmac[vm_pmac]