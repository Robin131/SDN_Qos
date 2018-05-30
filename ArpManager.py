from ryu.lib.packet import arp
from ryu.lib.packet import packet, ethernet

class ArpManager(object):
    def __init__(self, arp_table, pmac_to_vmac, gateway_arp_table, dpid_to_vmac, topo_manager, mac_manager):
        super(ArpManager, self).__init__()

        self.arp_table = arp_table
        self.pmac_to_vmac = pmac_to_vmac
        self.gateway_arp_table = gateway_arp_table
        self.dpid_to_vmac = dpid_to_vmac
        self.topo_manager = topo_manager
        self.mac_manager = mac_manager


    def handle_arp(self, datapath, in_port, pkt_ethernet, pkt_arp, tenant_id, topoManager, whole_packet):
        parser = datapath.ofproto_parser
        dst_ip = pkt_arp.dst_ip
        if not pkt_arp.opcode == arp.ARP_REQUEST:
            # TODO deal with arp reply becuase there is something wired in Ping process
            print('Its a reply from ' + pkt_ethernet.src + ' and is to ' + dst_ip)
            return

        # first check whether it is requesting a gateway mac
        if dst_ip in self.gateway_arp_table.values():
            src_vmac = pkt_arp.src_mac
            gateway_id = -1
            for (key, value) in self.gateway_arp_table.items():
                if value == dst_ip:
                    gateway_id = key
            gateway_vmac = self.dpid_to_vmac[gateway_id]
            # reply arp packet to src
            pkt = packet.Packet()
            pkt.add_protocol(ethernet.ethernet(ethertype=pkt_ethernet.ethertype,
                                               dst=pkt_arp.src_mac, src=gateway_vmac))
            pkt.add_protocol(arp.arp(opcode=arp.ARP_REPLY,
                                     src_mac=gateway_vmac,
                                     src_ip=pkt_arp.dst_ip,
                                     dst_mac=pkt_arp.src_mac,
                                     dst_ip=pkt_arp.src_ip))
            pkt.serialize()
            actions = [parser.OFPActionOutput(port=in_port)]
            out = datapath.ofproto_parser.OFPPacketOut(
                datapath=datapath, in_port=datapath.ofproto.OFPP_CONTROLLER,
                buffer_id=datapath.ofproto.OFP_NO_BUFFER, actions=actions,
                data=pkt
            )
            datapath.send_msg(out)
            return

        # it is requesting a host ip
        dst_pmac = ''
        # if there is record for this dst_ip, get dst_pmac from arp_table
        if dst_ip in self.arp_table[tenant_id].keys():
            dst_pmac = self.arp_table[tenant_id][dst_ip]
        # else send it to the nearest gateway
        else:
            return

        if not dst_pmac in self.pmac_to_vmac.keys():
            print('arp error:no such host recorded for ip:', dst_ip)
            print(dst_pmac)
            return
        dst_vmac = self.pmac_to_vmac[dst_pmac]
        # test
        # print('This packet is from ' + pkt_ethernet.src + ' and is to ' + dst_ip)

        # fake a arp pkt and answer
        pkt = packet.Packet()
        pkt.add_protocol(ethernet.ethernet(ethertype=pkt_ethernet.ethertype,
                                           dst=pkt_arp.src_mac, src=dst_vmac))
        pkt.add_protocol(arp.arp(opcode=arp.ARP_REPLY,
                                 src_mac=dst_vmac,
                                 src_ip=pkt_arp.dst_ip,
                                 dst_mac=pkt_arp.src_mac,
                                 dst_ip=pkt_arp.src_ip))
        pkt.serialize()
        actions = [parser.OFPActionOutput(port=in_port)]
        out = datapath.ofproto_parser.OFPPacketOut(
            datapath=datapath, in_port=datapath.ofproto.OFPP_CONTROLLER,
            buffer_id=datapath.ofproto.OFP_NO_BUFFER, actions=actions,
            data=pkt
        )

        datapath.send_msg(out)
