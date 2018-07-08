from ryu.lib.packet import packet, ethernet, arp

import six


class ArpManager(object):
    def __init__(self,
                 arp_table,
                 pmac_to_vmac):
        super(ArpManager, self).__init__()

        self.arp_table = arp_table
        self.pmac_to_vmac = pmac_to_vmac

    # create an arp pkt according to original pkt and dst_vmac
    def _create_arp_pkt(self, original_pkt, dst_vmac):
        i = iter(original_pkt)
        pkt_ethernet = six.next(i)
        assert type(pkt_ethernet) == ethernet.ethernet
        pkt_arp = six.next(i)
        assert type(pkt_arp) == arp.arp

        pkt = packet.Packet()
        pkt.add_protocol(ethernet.ethernet(ethertype=pkt_ethernet.ethertype,
                                           dst=pkt_arp.src_mac, src=dst_vmac))
        pkt.add_protocol(arp.arp(opcode=arp.ARP_REPLY,
                                 src_mac=dst_vmac,
                                 src_ip=pkt_arp.dst_ip,
                                 dst_mac=pkt_arp.src_mac,
                                 dst_ip=pkt_arp.src_ip))
        pkt.serialize()
        return pkt

    def handle_arp(self, datapath, in_port, tenant_id, pkt):

        i = iter(pkt)
        pkt_ethernet = six.next(i)
        assert type(pkt_ethernet) == ethernet.ethernet
        pkt_arp = six.next(i)
        assert type(pkt_arp) == arp.arp

        # test
        print(str(pkt_arp.src_mac) + ' ask mac for ' + pkt_arp.dst_ip)

        parser = datapath.ofproto_parser
        dst_ip = pkt_arp.dst_ip
        src_ip = pkt_arp.src_ip
        dst_pmac = ''

        # TODO deal with arp reply becuase there is something wired in Ping process
        if not pkt_arp.opcode == arp.ARP_REQUEST:
            print('Its a reply from ' + pkt_ethernet.src + ' and is to ' + dst_ip)
            return

        # TODO arp for gateway
        # first check whether it is requesting a gateway mac
        if False:
            return
        # TODO NAT ask for host
        elif False:
            return
        # it is one host requesting another host ip
        else:
            # if there is record for this dst_ip, get dst_pmac from arp_table
            if dst_ip in self.arp_table[tenant_id].keys():
                dst_pmac = self.arp_table[tenant_id][dst_ip]
            else:
                return

        if not dst_pmac in self.pmac_to_vmac.keys():
            print('arp error:no such host recorded for ip:', dst_ip)
            print(dst_pmac)
            return
        dst_vmac = self.pmac_to_vmac[dst_pmac]
        # test
        # print('This packet is from ' + pkt_ethernet.src + ' and is to ' + dst_ip)
        print('reply ' + str(pkt_arp.src_mac) + ', the mac for ' + pkt_arp.dst_ip +
              ' is ' + str(dst_vmac))

        # fake a arp pkt and answer
        pkt = self._create_arp_pkt(pkt, dst_vmac)
        actions = [parser.OFPActionOutput(port=in_port)]
        out = datapath.ofproto_parser.OFPPacketOut(
            datapath=datapath, in_port=datapath.ofproto.OFPP_CONTROLLER,
            buffer_id=datapath.ofproto.OFP_NO_BUFFER, actions=actions,
            data=pkt
        )

        datapath.send_msg(out)
