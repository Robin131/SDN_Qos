# flow table for gateway
# 0 : local subnet
# 1 : different subnet in this datacenter
# 2 : other datacenter
# 3 : NAT
#


import six
import IPy

from ryu.lib.packet import packet, ethernet, ipv4

class GatewayManager(object):
    def __init__(self, datapathes, possibie_gatewats, arp_table_datacenter, gateways, gateway_arp_table, dpid_to_vmac,
                 flow_manager, subnet, mac_manager, datacenter_id, arp_table, pmac_to_vmac,
                 topo_manager, gateway_in_subnet, gateway_vmac, datacenter_sunbet, NAT_ip_mac,
                 gateway_NAT, host_queue):
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
        self.gateway_in_subnet = gateway_in_subnet
        self.gateway_vmac = gateway_vmac
        self.datacenter_sunbet = datacenter_sunbet
        self.NAT_ip_mac = NAT_ip_mac
        self.gateway_NAT = gateway_NAT
        self.host_queue = host_queue

    def register_gateway(self, dpid):

        # add gateway
        self.gateways[dpid] = self.possible_gateways[dpid]
        self.gateway_vmac[dpid] = self.dpid_to_vmac[dpid]

        gateway = self.datapathes[dpid]
        parser = gateway.ofproto_parser
        ofproto = gateway.ofproto

        # first find which port is the outer port(connect to own subnet)
        outer_ports = []
        for (port_no, dst) in self.gateways[dpid].items():
            if dst != self.gateway_in_subnet[dpid]:
                outer_ports.append(port_no)

        # drop all pkts from outer port in table 0 if they cannot match any inner host
        # NAT arp is handled later
        for port in outer_ports:
            match = parser.OFPMatch(in_port=port)
            actions = []
            instruction = [
                parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions),
            ]
            self.flow_manager.add_flow(datapath=gateway, priority=1, match=match, instructions=instruction,
                                       table_id=0, buffer_id=None)


        # add flow entry for each port
        # for other subnet port, add flow according to ip wildcard
        # for datacenter port, add flow entry according to ip wildcard
        # send other pkt to Internet port
        for (port_no, dst) in self.gateways[dpid].items():
            # datacenter port or Internet port
            if type(dst) == type('1'):
                if dst == 'NAT':
                    # change the mac address to NAT mac for pkts to Internet
                    match = parser.OFPMatch()
                    nat_mac = self.NAT_ip_mac[self.gateway_NAT[dpid]]
                    actions = [
                        parser.OFPActionSetField(eth_dst=nat_mac),
                        parser.OFPActionOutput(port_no),
                        # parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)
                    ]
                    instruction = [
                        parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)
                    ]
                    self.flow_manager.add_flow(datapath=gateway, priority=0, match=match, instructions=instruction,
                                  table_id=3, buffer_id=None)

                    # install flow entry to send NAT arp pkts to controller in table 0
                    match = parser.OFPMatch(eth_type=0x0806, in_port=port_no)
                    actions = [parser.OFPActionOutput(
                        ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER
                    )]
                    instruction = [
                        parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)
                    ]
                    self.flow_manager.add_flow(datapath=gateway, priority=2, match=match, instructions=instruction,
                                               table_id=0, buffer_id=None)


                    continue
                else:
                    datacenter_id = int(dst)
                    for subnet in self.datacenter_sunbet[datacenter_id]:
                        subnet_ip = self.subnet[subnet]
                        match = parser.OFPMatch(eth_type=0x800, ipv4_dst=subnet_ip)
                        actions = [parser.OFPActionOutput(port_no)]
                        instruction = [
                            parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions),
                        ]
                        self.flow_manager.add_flow(datapath=gateway, priority=1, match=match, instructions=instruction,
                                                   table_id=2, buffer_id=None)
            # different subnet port
            else:
                # first check whether this subnet is the one this gateway is in
                if dst == self.gateway_in_subnet[dpid]:
                    continue
                else:
                    subnet_ip = self.subnet[dst]
                    match = parser.OFPMatch(eth_type=0x800, ipv4_dst=subnet_ip)
                    actions = [parser.OFPActionOutput(port_no)]
                    instruction = [
                        parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions),
                        parser.OFPInstructionGotoTable(table_id=2)
                    ]
                    self.flow_manager.add_flow(datapath=gateway, priority=2, match=match, instructions=instruction,
                                table_id=1, buffer_id=None)


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
        for (id, ip_address) in self.subnet.items():
            if ip in IPy.IP(ip_address):
                subnet_id = id
            else:
                continue
        ports = []
        for (port_no, dst) in self.gateways[dpid].items():
            if dst == subnet_id:
                ports.append(port_no)
            else:
                continue
        return ports

    # get id of datacenter who has this ip
    def _get_datacenter_id_with_ip(self, ip):
        for key in self.arp_table_datacenter.keys():
            if ip in self.arp_table_datacenter[key]:
                return key
            else:
                continue
        return -1

    # get port_no to a certain datacenter on a certain gateway
    def _get_port_no_for_datacenter(self, datacenter_id, gateway_id):
        for (port_no, dst) in self.gateways[gateway_id].items():
            if dst == datacenter_id:
                return port_no
            else:
                continue
        return -1

    def _get_subnet_with_ip(self, ip):
        for (id, mask) in self.subnet.items():
            if ip in IPy.IP(mask):
                return id
            else:
                continue
        return -1


    def gateway_packet_in_handler(self, ev):
        msg = ev.msg
        dp = msg.datapath
        dpid = dp.id
        ofproto = dp.ofproto
        parser = dp.ofproto_parser
        in_port = msg.match['in_port']
        pkt = packet.Packet(msg.data)

        i = iter(pkt)
        eth_pkt = six.next(i)
        assert type(eth_pkt == ethernet.ethernet)

        ipv4_pkt = six.next(i)
        assert type(ipv4_pkt == ipv4.ipv4)

        src_ip = ipv4_pkt.src
        dst_ip = ipv4_pkt.dst

        # test
        print('packet in from gateway ' + str(dpid) + ', src=' + str(eth_pkt.src) + ', dst_ip=' + str(dst_ip))

        dst_datacenter_id = self._get_datacenter_id_with_ip(dst_ip)

        # dst is in this datacenter
        # may 1.come from different subnet 2.Internet or other datacenters 3.come from this subnet to other subnet
        # send with vmac instead of ip address
        if dst_datacenter_id == self.datacenter_id:
            # first check whether dst is in this subnet
            this_subnet_id = self.gateway_in_subnet[dpid]
            dst_subnet_id = self._get_subnet_with_ip(dst_ip)

            # dst_ip is in this subnet, then the situation should be 1, 2
            # send with mac
            if dst_subnet_id == this_subnet_id:
                pmac = self.arp_table[self.datacenter_id][dst_ip]
                vmac = self.pmac_to_vmac[pmac]

                # get shortest path to this host from this gateway
                dst_dpid = self.mac_manager.get_dpid_with_vmac(vmac)
                path = self.topo_manager.get_path(dpid, dst_dpid)

                # install sending flow entry
                out_port = path[0][1]
                match = parser.OFPMatch(eth_type=0x800, ipv4_dst=dst_ip)
                actions = [
                    parser.OFPActionSetField(eth_dst=vmac),
                    parser.OFPActionOutput(out_port)
                ]
                instruction = [
                    parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)
                ]
                self.flow_manager.add_flow(datapath=dp, priority=1, match=match, instructions=instruction,
                                           table_id=0, buffer_id=msg.buffer_id)

                # send the packet back
                actions = [parser.OFPActionOutput(out_port)]
                data = None
                if msg.buffer_id == ofproto.OFP_NO_BUFFER:
                    data = msg.data
                out_packet = parser.OFPPacketOut(datapath=dp, buffer_id=msg.buffer_id,
                                                 in_port=in_port, actions=actions, data=data)
                dp.send_msg(out_packet)
                return

            # dst_ip is in other subnet, then the situation should be 3
            # send to certain port according to subnet_id
            else:
                # test
                print('should not add such flow for gateway')
                # # install flow entry
                # # TODO use wildcard here to reduce flow entry
                # out_port = self._get_out_port_with_ip(dst_ip, dpid)[0]
                # match = parser.OFPMatch(eth_type=0x800, ipv4_dst=dst_ip)
                # actions = [
                #     parser.OFPActionOutput(out_port)
                # ]
                # instruction = [
                #     parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)
                # ]
                # self.flow_manager.add_flow(datapath=dp, priority=1, match=match, instructions=instruction,
                #                            table_id=0, buffer_id=msg.buffer_id)
                #
                # # send the pkt back
                # actions = [parser.OFPActionOutput(out_port)]
                # data = None
                # if msg.buffer_id == ofproto.OFP_NO_BUFFER:
                #     data = msg.data
                # out_packet = parser.OFPPacketOut(datapath=dp, buffer_id=msg.buffer_id,
                #                                  in_port=in_port, actions=actions, data=data)
                # dp.send_msg(out_packet)
                # return


        # dst is in other datacenters' record
        # 1.same subnet but different datacenter  2.different subnet in different datacenter
        elif dst_datacenter_id != -1:
            out_port = self._get_datacenter_id_with_ip(dst_ip)
            if out_port == -1:
                print('gateway ' + str(dpid) + ' cannot connect to datacenter ' + str(dst_datacenter_id))
                return
            # install flow entry
            # TODO use wildcard here to reduce flow entry
            match = parser.OFPMatch(eth_type=0x800, ipv4_dst=dst_ip)
            actions = [
                parser.OFPActionOutput(out_port)
            ]
            instruction = [
                parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)
            ]
            self.flow_manager.add_flow(datapath=dp, priority=1, match=match, instructions=instruction,
                                       table_id=0, buffer_id=msg.buffer_id)

            # send pkt back
            actions = [parser.OFPActionOutput(out_port)]
            data = None
            if msg.buffer_id == ofproto.OFP_NO_BUFFER:
                data = msg.data
            out_packet = parser.OFPPacketOut(datapath=dp, buffer_id=msg.buffer_id,
                                             in_port=in_port, actions=actions, data=data)
            dp.send_msg(out_packet)

        # dst in not in any of the datacenters
        # we consider this pkt should be sent to Internet (although it may not(wrong ip))
        else:
            out_port = self.get_internet_port(dpid)
            # TODO how to reduce flow here ??
            # TODO should dst_mac be changed to NAT mac?
            # TODO NAT pmac or vmac ??






        return








