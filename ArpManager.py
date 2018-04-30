from ryu.lib.packet import arp
from ryu.lib.packet import packet, ethernet

class ArpManager(object):
    def __init__(self, arp_table, pmac_to_vmac):
        super(ArpManager, self).__init__()

        self.arp_table = arp_table
        self.pmac_to_vmac = pmac_to_vmac

    def handle_arp(self, datapath, port, pkt_ethernet, pkt_arp, tenant_id):
        parser = datapath.ofproto_parser
        if not pkt_arp.opcide == arp.ARP_REQUEST:
            return
        dst_ip = pkt_arp.dst_ip
        dst_mac = ''
        # get dst_pmac
        if dst_ip in self.arp_table[tenent_id].keys():
            dst_mac = self.arp_table[tenant_id][dst_ip]
        else:
            return

        # fake a arp pkt and answer
        pkt = packet.Packet()
        pkt.add_protocol(ethernet.ethernet(ethertype=pkt_ethernet.ehtertype,
                                           dst=pkt_ethernet.src, src=dst_mac))
        pkt.add_protocol(arp.arp(opcode=arp.ARP_REPLY,
                                 src_mac=dst_mac,
                                 src_ip=pkt_arp.dst_ip,
                                 dst_mac=pkt_arp.src_mac,
                                 dst_ip=pkt_arp.src_ip))
        pkt.serialize()
        actions = [parser.OFPActionOutput(port=port)]
        out = dp.ofproto_parser.OFPPacketOut(
            datapath=datapath, in_port=port,
            buffer_id=dp.ofproto.OFP_NO_BUFFER, actions=actions,
            data=pkt
        )

        datapath.send_msg(out)
