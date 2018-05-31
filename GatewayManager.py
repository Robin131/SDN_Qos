# flow table for gateway
# 0 : receive(priority = 0)


import six
import IPy

from ryu.lib.packet import packet, ethernet, ipv4

class GatewayManager(object):
    def __init__(self, datapathes, possibie_gatewats, arp_table_datacenter, gateways, gateway_arp_table, dpid_to_vmac,
                 flow_manager, subnet, mac_manager, datacenter_id, arp_table, pmac_to_vmac,
                 topo_manager):
        super(GatewayManager, self)

        self.datapathes = datapathes
        self.possible_gateways = possibie_gatewats
        self.gateways = gateways
        self.flow_manager = flow_manager
        self.gateway_arp_table = gateway_arp_table
        self.dpid_to_vmac = dpid_to_vmac
        self.subnet = subnet
        self.mac_manager = mac_manager
        self.arp_table_datacenter = arp_table_datacenter
        self.datacenter_id = datacenter_id
        self.arp_table = arp_table
        self.pmac_to_vmac = pmac_to_vmac
        self.topo_manager = topo_manager


    def register_gateway(self, dpid):
        self.gateways[dpid] = self.possible_gateways[dpid]
        # for (port_no, dst) in self.gateways[dpid].items():
        #     # datacenter
        #     if dst != 'NAT':
        #         self.flow_manager.install_datacenter_flow(self, dst, port_no, dpid)
        #         return
        #     # Internet (Nat)
        #     else:
        #         gateway_vmac = self.dpid_to_vmac[dpid]
        #         self.flow_manager.install_internet_flow(gateway_vmac=gateway_vmac,
        #                                                 out_port=port_no,
        #                                                 gateway_id=dpid)
        #         return

    def get_internet_port(self, gateway_id):
        for (port_no, dst) in self.gateways[gateway_id].items():
            if dst == 'NAT':
                return port_no
            else:
                continue

    # get the port id for a certain subnet on gateway with id dpid
    def _get_out_port_with_ip(self, ip, dpid):
        # first look for the subnet id for ip
        subnet_id = -1
        for (id, ip_address) in self.subnet:
            if ip in IPy.IP(ip_address):
                subnet_id = id
            else:
                continue
        ports = []
        for (port_no, dst) in self.gateways[dpid]:
            if dst == subnet_id:
                ports.append(port_no)
            else:
                continue
        return ports

    # get id of datacenter who has this ip
    def _get_datacenter_id_with_ip(self, ip):
        for key in self.arp_table_datacenter:
            if ip in self.arp_table_datacenter[key]:
                return key
            else:
                continue
        return -1

    # get port_no to a certain datacenter on a certain gateway
    def _get_port_no_for_datacenter(self, datacenter_id, gateway_id):
        for (port_no, dst) in self.gateways[gateway_id]:
            if dst == datacenter_id:
                return port_no
            else:
                continue
        return -1


    def gateway_packet_in_handler(self, ev):
        msg = ev.msg
        dp = msg.datapath
        dpid = dp.id
        ofproto = dp.ofproto
        parser = dp.ofproto_parser
        pkt = packet.Packet(msg.data)

        i = iter(pkt)
        eth_pkt = six.next(i)
        assert type(eth_pkt == ethernet.ethernet)

        ipv4_pkt = six.next(i)
        assert type(ipv4_pkt == ipv4.ipv4)

        src_ip = ipv4_pkt.src
        dst_ip = ipv4_pkt.dst

        dst_datacenter_id = self._get_datacenter_id_with_ip(dst_ip)

        # dst is in this datacenter
        # may come from different subnet or Internet or other datacenters
        # send with vmac instead of ip address
        if dst_datacenter_id == self.datacenter_id:
            pmac = self.arp_table[self.datacenter_id][dst_ip]
            vmac = self.pmac_to_vmac[pmac]

            # get shortest path to this host from this gateway
            dst_dpid = self.mac_manager.get_dpid_with_vmac(vmac)
            path = self.topo_manager.get_path(dpid, dst_dpid)

            # install sending flow entry
            out_port = path[0][1]
            match = parser.OFPMatch(dst_ip=dst_ip)
            actions = [
                parser.OFPActionSerField(eth_dst=vmac),
                parser.OFPActionOutput(out_port)
            ]
            instruction = [
                parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)
            ]
            self.flow_manager.add_flow(datapath=dp, priority=1, match=match, instructions=instruction, table_id=0)
            return

        # dst is in other datacenters' record
        # 1.same subnet but different datacenter  2.different subnet in different datacenter
        elif dst_datacenter_id != -1:
            out_port = self._get_datacenter_id_with_ip(dst_ip)
            if out_port == -1:
                print('gateway ' + str(dpid) + ' cannot connect to datacenter ' + str(dst_datacenter_id))
                return
            # install flow entry
            # TODO use wildcard here to reduce flow entry
            match = parser.OFPMatch(dst_ip=dst_ip)
            actions = [
                parser.OFPActionOutput(out_port)
            ]
            instruction = [
                parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)
            ]
            self.flow_manager.add_flow(datapath=dp, priority=1, match=match, instructions=instruction, table_id=0)

        # dst in not in any of the datacenters
        # we consider this pkt should be sent to Internet (although it may not(wrong ip))
        else:
            out_port = self.get_internet_port(dpid)
            # TODO how to reduce flow here ??
            # TODO should dst_mac be changed to NAT mac?
            # TODO NAT pmac or vmac ??






        return








