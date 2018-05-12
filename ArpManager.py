from ryu.lib.packet import arp
from ryu.lib.packet import packet, ethernet

class ArpManager(object):
    def __init__(self, arp_table, pmac_to_vmac):
        super(ArpManager, self).__init__()

        self.arp_table = arp_table
        self.pmac_to_vmac = pmac_to_vmac

    def handle_arp(self, datapath, in_port, pkt_ethernet, pkt_arp, tenant_id):
        parser = datapath.ofproto_parser
        if not pkt_arp.opcode == arp.ARP_REQUEST:
            # TODO deal with arp reply becuase there is something wired in Ping process
            return
        # test
        elif pkt_arp.opcode == arp.ARP_REPLY:
            print('test pass!!')
        dst_ip = pkt_arp.dst_ip
        dst_pmac = ''
        # get dst_pmac
        if dst_ip in self.arp_table[tenant_id].keys():
            dst_pmac = self.arp_table[tenant_id][dst_ip]
        else:
            return

        if not dst_pmac in self.pmac_to_vmac.keys():
            print('arp error:no such host recorded for ip:', dst_ip)
            return
        dst_vmac = self.pmac_to_vmac[dst_pmac]
        # test
        print('This packet is from ' + pkt_ethernet.src + ' and is to ' + dst_ip)

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
