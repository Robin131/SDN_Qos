# -*- coding: utf-8 -*-

# vmac
# 1 2 : 3 4 : 5 6 : 7 8 : 9 0 : a b
# 1 datacenter_id
# 2 tenant_level
# 3456 tenant_id
# 7890 switch_id
# ab vm_id
import six

class MacManager(object):
    def __init__(self):
        super(MacManager, self).__init__()

    @staticmethod
    def get_vmac_new_switch(dpid, datacenter_id):

        vmac_datacenter_id = MacManager._generate_datacenter_vmac(datacenter_id)
        vmac_tenant_level = '0'
        vmac_tenant_id = '00:00'
        vmac_switch_id = MacManager._generate_switch_id_vmac(dpid)
        vmac_vm_id = '00'

    @staticmethod
    def _generate_datacenter_vmac(datacenter_id):
        assert(datacenter_id <= 15)
        return str(hex(datacenter_id))[-1]

    @staticmethod
    def _generate_switch_id_vmac(switch_id):
        assert(switch_id < 256 * 256)
        hex_str = str(hex(switch_id))
        xPos = hex_str.find('x')
        pure_hex_str = hex_str[xPos+1 :]
        pure_hex_str = '0' * (4 -len(pure_hex_str)) + pure_hex_str
        pure_hex_str = pure_hex_str[0:2] + ':' + pure_hex_str[2:]
        return pure_hex_str

    @staticmethod
    def get_tenant_id_with_vmac(vmac):
        return MacManager._get_tenant_id(vmac)

    @staticmethod
    def _get_tenant_id(vmac):
        split = vmac.split(':')
        tenant_hex = split[1] + split[2]
        return int(tenant_hex, 16)