from ryu.lib.packet import packet, ethernet
from multiprocessing import Queue
from ryu.lib import hub
from ryu.ofproto import ofproto_v1_3 as ofp_13

class HostManager(object):
    def __init__(self, arp_table, host_pmac, mac_manager, datacenter_id, pmac_to_vmac,
                 vmac_to_pmac, meter_manager, tenant_speed, flow_manager, host_gateway,
                 datapathes, topo_manager, host_queue):
        super(HostManager, self).__init__()

        self.arp_table = arp_table
        self.host_pmac = host_pmac
        self.mac_manager = mac_manager
        self.datacenter_id = datacenter_id
        self.pmac_to_vmac = pmac_to_vmac
        self.vmac_to_pmac = vmac_to_pmac
        self.meter_manager = meter_manager
        self.tenant_speed = tenant_speed
        self.flow_manager = flow_manager
        self.host_gateway = host_gateway
        self.datapathes = datapathes
        self.topo_manager = topo_manager
        self.host_queue = host_queue

    def register_host(self, ev):
        msg = ev.msg
        dp = msg.datapath
        dpid = dp.id

        ofproto = dp.ofproto
        parser = dp.ofproto_parser
        pkt = packet.Packet(msg.data)

        eth = pkt.get_protocols(ethernet.ethernet)[0]
        src = eth.src
        in_port = msg.match['in_port']

        tenant_id = self.get_tenant_id(src)
        src_vmac = self.mac_manager.get_vmac_new_host(dpid=dpid, port_id=in_port,
                                                      datacenter_id=self.datacenter_id,
                                                      tenant_id=tenant_id)
        self.pmac_to_vmac[src] = src_vmac
        self.vmac_to_pmac[src_vmac] = src
        print(self.vmac_to_pmac)
        # install flow table to (pmac -> vmac) when sending (there may be a speed limit)
        # install flow table to (vmac -> pmac) when receving
        # install receiving flow entry for this host
        if tenant_id in self.tenant_speed.keys():
            # test
            print('add meter')
            meter_id = self.meter_manager.add_meter(datapath=dp, speed=self.tenant_speed[tenant_id])
            print('meter id is ' + str(meter_id))
            self.flow_manager.transfer_src_pmac_to_vmac(ev, src, src_vmac, meter_id=meter_id)
        else:
            self.flow_manager.transfer_src_pmac_to_vmac(ev, src, src_vmac)
        self.flow_manager.transfer_dst_vmac_to_pmac(ev, src_vmac, src)
        self.flow_manager.install_receiving_flow_entry(dp, src, in_port)

        # directly put host info in queue
        gateway_id = self.host_gateway[src]

        # get ip for this host
        find = False
        host_ip = ''
        for tenant in self.arp_table.keys():
            for (ip, mac) in self.arp_table[tenant].items():
                if mac == src:
                    host_ip = ip
                    find = True
                    break
            if find == True:
                break


        if gateway_id in self.host_queue.keys():
                self.host_queue[gateway_id].put(
                    {
                        'host_ip':host_ip,
                        'host_vmac':src_vmac
                    }
                )
        else:
                self.host_queue[gateway_id] = Queue(maxsize=-1)
                self.host_queue[gateway_id].put(
                    {
                        'host_ip': host_ip,
                        'host_vmac': src_vmac
                    }
                )



    def get_tenant_id(self, vm_pmac):
        return self.host_pmac[vm_pmac]

    def install_host_flow_entry_gateway(self):
        hub.sleep(5)

        # check whether host queue is empty, if not, install flow entry
        for gateway_id in self.host_queue.keys():
            if not self.host_queue[gateway_id].empty():
                gateway = self.datapathes[gateway_id]
                parser = gateway.ofproto_parser
                ofproto = gateway.ofproto

                while not self.host_queue[gateway_id].empty():
                    record = self.host_queue[gateway_id].get()
                    host_ip = record['host_ip']
                    host_vmac = record['host_vmac']

                    # ask out_port
                    host_dpid = self.mac_manager.get_dpid_with_vmac(host_vmac)
                    path = self.topo_manager.get_path(gateway_id, host_dpid)
                    out_port = path[0][1]

                    # install flow entry for gateway
                    # first install ip flow entry
                    tenant_id = self.mac_manager.get_tenant_id_with_vmac(host_vmac)


                    match = parser.OFPMatch(eth_src=('00:00:0'+str(tenant_id)+':00:00:00','00:ff:ff:00:00:00'),
                                            eth_type=0x800,
                                            ipv4_dst=host_ip
                    )
                    # match.append_field(
                    #     header=ofp_13.OXM_OF_ETH_SRC_W,
                    #     mask=self.flow_manager.get_tenant_id_mask(),
                    #     value=self.flow_manager.get_tenant_id_value(tenant_id)
                    # )
                    actions = [
                        parser.OFPActionSetField(eth_dst=host_vmac),
                        parser.OFPActionOutput(out_port)
                    ]
                    instructions = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]

                    self.flow_manager.add_flow(datapath=gateway, priority=2,
                                               match=match, instructions=instructions, table_id=0, buffer_id=None)

                    # then install vmac flow entry
                    match = parser.OFPMatch(eth_dst=host_vmac)
                    actions = [
                        parser.OFPActionOutput(out_port)
                    ]
                    instructions = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
                    self.flow_manager.add_flow(datapath=gateway, priority=2,
                                               match=match, instructions=instructions, table_id=0, buffer_id=None)

            else:
                continue

        print("finish to install queue flow")

