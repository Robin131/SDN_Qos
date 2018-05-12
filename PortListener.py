from ryu.ofproto.ofproto_v1_3 import OFPMPF_REQ_MORE
from ryu.lib import hub

class PortListener(object):
    def __init__(self, datapathes, sleep_time, dpid_to_dpid, port_speed, calculate_interval):
        super(PortListener, self).__init__()
        self.datapathes = datapathes
        self.sleep_time = sleep_time
        self.dpid_to_dpid = dpid_to_dpid
        self.port_speed = port_speed
        self.calculate_interval = calculate_interval

        self.temp_port_speed = {}        # {dpid -> {port_id -> {'duration', 'rx_bytes', 'tx_byes'}}}
        self.port_speed_init = False

    def _init_port_speed(self):
        for (dpid, port_id) in self.dpid_to_dpid.keys():
            self.port_speed[dpid][port_id]['cur_speed'] = 0
            # TODO initiate max speed
            self.port_speed[dpid][port_id]['max_speed'] = -1
        self.port_speed_init = True

    def _send_port_desc_status_request(self, datapath):
        ofp_parser = datapath.ofproto_parser
        req = ofp_parser.OFPPortDescStatsRequest(datapath, 0)
        datapath.send_msg(req)

    def _send_port_statistics_stats_request(self, datapath):
        ofp = datapath.ofproto
        ofp_parser = datapath.ofproto_parser

        req = ofp_parser.OFPPortStatsRequest(datapath, 0, ofp.OFPP_ANY)
        datapath.send_msg(req)

    def inquiry_all_port_desc_stats(self):
        while(True):
            # test
            print('ask all ports for desc info===============')
            hub.sleep(self.sleep_time)
            for dp in self.datapathes.values():
                self._send_port_desc_status_request(dp)

    def inquiry_all_port_statistics_stats(self):
        # wait to iniate
        # TODO change to another appropriate way
        hub.sleep(100)
        if not self.port_speed_init:
            self._init_port_speed()
        while(True):
            # test
            print('ask all ports for statis info===============')
            hub.sleep(self.sleep_time)
            self.temp_port_speed.clear()
            for dp in self.datapathes.values():
                self._send_port_statistics_stats_request(dp)
            hub.sleep(self.calculate_interval)
            for dp in self.datapathes.values():
                self._send_port_statistics_stats_request(dp)


    def port_statistics_stats_handler(self, ev):
        msg = ev.msg
        dp = msg.datapath
        dpid = dp.id

        for stat in ev.msg.body:
            port_id = stat.port_no
            # only calculate speed fpr ports that connect ovs
            if (dpid, port_id) in self.dpid_to_dpid.keys():
                duration = stat.duration_sec
                rx_bytes = stat.rx_bytes
                tx_bytes = stat.tx_bytes

                # if there is no record for this port
                if not dpid in self.temp_port_speed.keys():
                    self.temp_port_speed[dpid][port_id]['duration'] = duration
                    self.temp_port_speed[dpid][port_id]['rx_bytes'] = rx_bytes
                    self.temp_port_speed[dpid][port_id]['tx_bytes'] = tx_bytes
                else:
                    interval = abs(self.temp_port_speed[dpid][port_id]['duration'] - duration)
                    bytes = abs(self.temp_port_speed[dpid][port_id]['rx_bytes'] - rx_bytes +
                                abs(self.temp_port_speed[dpid][port_id]['tx_bytes'] - tx_bytes))
                    speed = bytes / interval
                    self.port_speed[dpid][port_id]['cur_speed'] = speed



    def port_desc_stats_handler(self, ev):
        print(ev.msg.body)