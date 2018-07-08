# -*- coding: utf-8 -*-
import networkx as nx

class TopoManager(object):
    def __init__(self,
                 topo,
                 dpid_to_dpid):
        super(TopoManager, self).__init__()
        self.topo = topo
        self.dpid_to_dpid = dpid_to_dpid

    # return ((ovs, port), (ovs, port), ...)
    def get_path(self, dpid1, dpid2):
        path = self._get_path(dpid1, dpid2)
        path_and_ports = []
        connection_number = len(path) - 1
        for i in range(connection_number):
            port_id = self._get_connection_port_id(path[i], path[i+1])
            path_and_ports.append((path[i], port_id))
        return path_and_ports


    def _get_path(self, dpid1, dpid2):
        return nx.shortest_path(self.topo, dpid1, dpid2)

    def _get_connection_port_id(self, dpid1, dpid2):
        for key, value in self.dpid_to_dpid.items():
            if key[0] == dpid1 and value == dpid2:
                return key[1]

        return -1




