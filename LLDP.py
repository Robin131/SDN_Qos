# -*- coding: utf-8 -*-
import struct
import six

from ryu.lib.packet import packet, ethernet
from ryu.lib.packet import lldp
from ryu.ofproto.ether import ETH_TYPE_LLDP
from ryu.lib import hub

from ryu.lib.dpid import dpid_to_str, str_to_dpid

class LLDPPacket(object):

    @staticmethod
    def lldp_packet(dpid, port_no, dl_addr, ttl):
        pkt = packet.Packet()

        dst = lldp.LLDP_MAC_NEAREST_BRIDGE
        src = dl_addr                          
        ethertype = ETH_TYPE_LLDP
        eth_pkt = ethernet.ethernet(dst, src, ethertype)
        pkt.add_protocol(eth_pkt)

        tlv_chassis_id = lldp.ChassisID(
            subtype= lldp.ChassisID.SUB_LOCALLY_ASSIGNED,
            chassis_id= dpid_to_str(dpid).encode('ascii')
        )

        tlv_port_id = lldp.PortID(
            subtype= lldp.PortID.SUB_PORT_COMPONENT,
            port_id= struct.pack('i', port_no)
        )

        tlv_ttl = lldp.TTL(ttl=ttl)             # time to live
        tlv_end = lldp.End()

        tlvs = (tlv_chassis_id, tlv_port_id, tlv_ttl, tlv_end)
        lldp_pkt = lldp.lldp(tlvs)
        pkt.add_protocol(lldp_pkt)

        pkt.serialize()
        return pkt.data

    @staticmethod
    def lldp_parse(data):
        pkt = packet.Packet(data)
        i = iter(pkt)
        eth_pkt = six.next(i)
        assert type(eth_pkt) == ethernet.ethernet

        lldp_pkt = six.next(i)
        assert type(lldp_pkt) == lldp.lldp

        tlv_chassis_id = lldp_pkt.tlvs[0]
        chassis_id = tlv_chassis_id.chassis_id

        return str_to_dpid(chassis_id)


class LLDPListener(object):
    def __init__(self, datapathes, dpid_potrs, dpid_to_dpid, topo, DEFAULT_TTL):
        super(LLDPListener, self).__init__()

        self.DEFAULT_TTL = DEFAULT_TTL
        self.datapathes = datapathes
        self.dpid_ports = dpid_potrs
        self.dpid_to_dpid = dpid_to_dpid
        self.topo = topo


    def _send_lldp_packet(self, dp):
        # print("send llpd packet")
        lldp_data = LLDPPacket.lldp_packet(dp.id, 0,
                                           '00:00:00:00:00:00', self.DEFAULT_TTL)

        actions = []
        for port in self.dpid_ports[dp.id].values():
            # print(port)
            actions.append(dp.ofproto_parser.OFPActionSetField(eth_src=port.hw_addr))  # 设置源地址??
            actions.append(dp.ofproto_parser.OFPActionOutput(port.port_no))  # 从指定端口发出

        out = dp.ofproto_parser.OFPPacketOut(
            datapath=dp, in_port=dp.ofproto.OFPP_CONTROLLER,
            buffer_id=dp.ofproto.OFP_NO_BUFFER, actions=actions,
            data=lldp_data
        )

        dp.send_msg(out)

    def install_lldp_flow(self, ev):
        dp = ev.datapath
        ofproto = dp.ofproto
        ofproto_parser = dp.ofproto_parser

        match = ofproto_parser.OFPMatch(
            eth_type=ETH_TYPE_LLDP,
            eth_dst=lldp.LLDP_MAC_NEAREST_BRIDGE
        )

        actions = [ofproto_parser.OFPActionOutput(
            ofproto.OFPP_CONTROLLER,
            ofproto.OFPCML_NO_BUFFER
        )]

        inst = [ofproto_parser.OFPInstructionActions(
            ofproto.OFPIT_APPLY_ACTIONS, actions
        )]

        mod = ofproto_parser.OFPFlowMod(datapath=dp, match=match, instructions=inst)

        dp.send_msg(mod)

    def lldp_packet_in(self, ev):
        # print('receive a lldp packet')
        msg = ev.msg
        dp = msg.datapath
        dpid = dp.id
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        # 只接受lldp包
        try:
            src_mac = eth.src
            src_dpid = LLDPPacket.lldp_parse(msg.data)
        except:
            return
        # print('receive a lldp packet, dpid, src_dpid:', dpid, src_dpid)

        for port in self.dpid_ports[src_dpid].values():
            if port.hw_addr == src_mac:
                src_port_no = port.port_no

        # 添加端口连接情况
        flag = False
        for key, value in self.dpid_to_dpid.items():
            if key[0] == dpid and value == src_dpid:
                flag = True
                break
            else:
                continue
        if not flag:
            self.dpid_to_dpid[(src_dpid, src_port_no)] = dpid

        # 向topo图中添加边
        self.topo.add_edge(src_dpid, dpid)

    def lldp_loop(self):
        while True:
            hub.sleep(2)
            # print("lldp detect")
            for dp in self.datapathes.values():
                self._send_lldp_packet(dp)

            hub.sleep(5)
            # print("test:check dpid_to_dpid", self.dpid_to_dpid)
            # print("nodes:", self.topo.nodes())
            # print("edges:", self.topo.edges())







# class Switch(app_manager.RyuApp):
#     DEFAULT_TTL = 120
#     IDLE_TIME = 10
#     def __init__(self, *args, **kwargs):
#         super(Switch, self).__init__(*args, **kwargs)
#         self.dpid_ports = {}         #dipd -> dp.ports
#         self.dpid_to_dpid = {}       # dpid -> {port -> remote dpid}
#         self.topo = nx.Graph()       #topo图
#         self.switches = {}           # dpid -> dp
#         #self.event = hub.Event()
#         #self.event.set()
#         self.topo_ditct_hub = hub.spawn(self._lldp_loop)
#         #self.threads.append(self.topo_ditct_hub)
#
#     def _register_switch(self, dp):
#         # 获取该switch的所有端口信息
#         dpid = dp.id
#         #print("test:check ports")
#         #print(dp.ports)
#         #print("\n")
#         ports = copy.copy(dp.ports)
#         #print("test:check my ports")
#         #print(ports)
#         self.dpid_ports[dpid] = ports
#         self.switches[dpid] = dp
#
#         # topo图上添加switch
#         self.topo.add_node(dpid)
#
#     @set_ev_cls(ofp_event.EventOFPStateChange, [MAIN_DISPATCHER, DEAD_DISPATCHER])
#     def state_change_handler(self, ev):
#         dp = ev.datapath
#         ofproto = dp.ofproto
#         ofproto_parser = dp.ofproto_parser
#
#         #print("test1\n")
#
#         if ev.state == MAIN_DISPATCHER:
#
#             # 注册交换机
#             self._register_switch(dp)
#
#             # TODO 检查重复链接
#             # TODO 记录交换机上的port地址 感觉这个好像可以不弄？
#             #print("test2\n")
#             # 添加lldp流表
#             match = ofproto_parser.OFPMatch(
#                 eth_type= ETH_TYPE_LLDP,
#                 eth_dst= lldp.LLDP_MAC_NEAREST_BRIDGE
#             )
#
#             #print("test2.1\n")
#
#             actions = [ofproto_parser.OFPActionOutput(
#                 ofproto.OFPP_CONTROLLER,
#                 ofproto.OFPCML_NO_BUFFER
#             )]
#
#             inst = [ofproto_parser.OFPInstructionActions(
#                 ofproto.OFPIT_APPLY_ACTIONS, actions
#             )]
#
#             #print("test3\n")
#
#             mod = ofproto_parser.OFPFlowMod(datapath= dp, match= match, instructions=inst)
#
#             #print("test4\n")
#
#             dp.send_msg(mod)
#
#
#
#
#         # TODO 交换机dead
#
#
#     def send_lldp_packet(self, dp):
#         print("test:send llpd packet")
#         lldp_data = LLDPPacket.lldp_packet(dp.id, 0,
#                                            '00:00:00:00:00:00', self.DEFAULT_TTL)
#
#         actions = []
#         for port in self.dpid_ports[dp.id].values():
#             #print(port)
#             actions.append(dp.ofproto_parser.OFPActionSetField(eth_src=port.hw_addr))#设置源地址??
#             actions.append(dp.ofproto_parser.OFPActionOutput(port.port_no))     #从指定端口发出
#
#         out = dp.ofproto_parser.OFPPacketOut(
#             datapath= dp, in_port= dp.ofproto.OFPP_CONTROLLER,
#             buffer_id= dp.ofproto.OFP_NO_BUFFER, actions= actions,
#             data= lldp_data
#         )
#
#         dp.send_msg(out)
#
#     @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
#     def lldp_packet_in_handler(self, ev):
#
#         print("test:receive a lldp packet")
#         msg = ev.msg
#         dp = msg.datapath
#         dpid = dp.id
#         pkt = packet.Packet(msg.data)
#         eth = pkt.get_protocols(ethernet.ethernet)[0]
#
#         # 只接受lldp包
#         try:
#             src_mac = eth.src
#             src_dpid = LLDPPacket.lldp_parse(msg.data)
#         except:
#             return
#         print("test:receive a lldp packet, dpid:%d, src_dpid:%d", dpid, src_dpid)
#
#         for port in self.dpid_ports[src_dpid].values():
#             if port.hw_addr == src_mac:
#                 src_port_no = port.port_no
#
#         # 添加端口连接情况
#         temp = {}
#         temp[src_port_no] = dpid
#         self.dpid_to_dpid[src_dpid] = copy.copy(temp)
#
#
#         # 向topo图中添加边
#         self.topo.add_edge(src_dpid, dpid)
#
#     def _lldp_loop(self):
#
#         hub.sleep(2)
#         print("test switches")
#         print(self.switches)
#         for dp in self.switches.values():
#             self.send_lldp_packet(dp)
#
#         hub.sleep(2)
#         print("test:check dpid_to_dpid", self.dpid_to_dpid)
#         print("nodes:", self.topo.nodes())
#         print("edges:", self.topo.edges())


