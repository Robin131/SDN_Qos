import struct
import six
import networkx as nx
import copy

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import set_ev_cls
from ryu.controller.handler import MAIN_DISPATCHER, DEAD_DISPATCHER, CONFIG_DISPATCHER
from ryu.lib.packet import packet, ethernet
from ryu.lib.packet import lldp, ether_types
from ryu.lib.packet import ipv4, tcp, udp, icmp, arp
from ryu.ofproto import ofproto_v1_3
from ryu.ofproto import ether, inet
from ryu.lib import hub
from netaddr import IPAddress, IPNetwork
from collections import namedtuple
from ryu.app.wsgi import WSGIApplication

from ryu.lib.dpid import dpid_to_str, str_to_dpid

class MacManager(object):
    def __init__(self, pmac_to_vmac, vmac_to_pmac):
        super(MacManager, self).__init__()

        self.pmac_to_vmac = pmac_to_vmac
        self.vmac_to_pmac = vmac_to_pmac

    # get a new vmac for a new switch
    def get_vmac_new_switch(self, datapath, tenant_id=1):
        dpid = datapath
        tenant_part = '0' + str(hex(tenant_id))[-1] if tenant_id <=15 else str(hex(tenant_id))[-2:]
        switch_part = '0' + str(hex(dpid))[-1] if dpid <= 15 else str(hex(dpid))[-2:]
        return tenant_part + ':' + '00:' + switch_part + '00:00:00'

    # get a new vmac for a new host
    def get_vmac_new_host(self, dpid, port_id, tenant_id=1):
        tenant_part = '0' + str(hex(tenant_id))[-1] if tenant_id <= 15 else str(hex(tenant_id))[-2:]
        switch_part = '0' + str(hex(dpid))[-1] if dpid <= 15 else str(hex(dpid))[-2:]
        host_part = '0' + str(hex(port_id))[-1] if port_id <= 15 else str(hex(port_id))[-2:]
        return tenant_part + ':' + '00:' + switch_part + ':' + '00:'+ host_part + ':' + '00'

    # get dpid with a vmac of host
    def get_dpid_with_vmac(self, vmac):
        return self._get_dpid(vmac)

    def get_port_id_with_vmac(self, vmac):
        return self._get_port_id(vmac)

    def _get_tenant_id(self, vmac):
        split = vmac.split(':')
        return int(split[0], 16)

    def _get_dpid(self, vmac):
        split = vmac.split(':')
        return int(split[1], 16)

    def _get_port_id(self, vmac):
        split = vmac.split(':')
        return int(split[2], 16)
