# -*- coding: utf-8 -*-

# vmac
# 1 2 : 3 4 : 5 6 : 7 8 : 9 0 : a b
# 1 datacenter_id
# 2 tenant_level
# 3456 tenant_id
# 7890 switch_id
# ab vm_id

class MacManager(object):
    def __init__(self, pmac_to_vmac, vmac_to_pmac, tenant_level):
        super(MacManager, self).__init__()

        self.pmac_to_vmac = pmac_to_vmac
        self.vmac_to_pmac = vmac_to_pmac
        self.tenant_level = tenant_level

    # get a new vmac for a new switch
    def get_vmac_new_switch(self, datapath, datacenter_id):
        dpid = datapath

        vmac_datacenter_id = self._generate_datacenter_vmac(datacenter_id)
        vmac_tenant_level = '0'
        vmac_tenant_id = '00:00'
        vmac_switch_id = self._generate_switch_id_vmac(dpid)
        vmac_vm_id = '00'

        return vmac_datacenter_id + vmac_tenant_level + ':' + vmac_tenant_id \
               + ':' + vmac_switch_id + ':' + vmac_vm_id

    # get a new vmac for a new host
    def get_vmac_new_host(self, dpid, port_id, datacenter_id, tenant_id):
        vmac_datacenter_id = self._generate_datacenter_vmac(datacenter_id)
        vmac_tenant_level = str(hex(self.tenant_level[tenant_id]))[-1]
        vmac_tenant_id = self._generate_tenant_id_vmac(tenant_id)
        vmac_switch_id = self._generate_switch_id_vmac(dpid)
        vmac_vm_id = self._generate_vm_id_vmac(port_id)
        return vmac_datacenter_id + vmac_tenant_level + ':' + vmac_tenant_id \
               + ':' + vmac_switch_id + ':' + vmac_vm_id

    # get dpid with a vmac of host
    def get_dpid_with_vmac(self, vmac):
        return self._get_dpid(vmac)

    def get_port_id_with_vmac(self, vmac):
        return self._get_port_id(vmac)

    def get_tenant_id_with_vmac(self, vmac):
        return self._get_tenant_id(vmac)

    def get_datacenter_id_with_vmac(self, vmac):
        return self._get_datacenter_id(vmac)

    def _get_tenant_id(self, vmac):
        split = vmac.split(':')
        tenant_hex = split[1] + split[2]
        return int(tenant_hex, 16)

    def _get_dpid(self, vmac):
        split = vmac.split(':')
        dpid_hex = split[3] + split[4]
        return int(dpid_hex, 16)

    def _get_datacenter_id(self, vmac):
        datacenter_id_hex = vmac[0]
        return int(datacenter_id_hex, 16)

    def _get_port_id(self, vmac):
        split = vmac.split(':')
        return int(split[5], 16)

    def _generate_datacenter_vmac(self, datacenter_id):
        assert(datacenter_id <= 15)
        return str(hex(datacenter_id))[-1]

    def _generate_switch_id_vmac(self, switch_id):
        assert(switch_id < 256 * 256)
        hex_str = str(hex(switch_id))
        xPos = hex_str.find('x')
        pure_hex_str = hex_str[xPos+1 : ]
        pure_hex_str = '0' * (4 -len(pure_hex_str)) + pure_hex_str
        pure_hex_str = pure_hex_str[0:2] + ':' + pure_hex_str[2:]
        return pure_hex_str

    def _generate_tenant_id_vmac(self, tenant_id):
        return self._generate_switch_id_vmac(tenant_id)

    def _generate_vm_id_vmac(self, port_id):
        assert(port_id < 256)
        hex_str = str(hex(port_id))
        xPos = hex_str.find('x')
        pure_hex_str = hex_str[xPos + 1:]
        pure_hex_str = '0' * (2 - len(pure_hex_str)) + pure_hex_str
        return pure_hex_str


