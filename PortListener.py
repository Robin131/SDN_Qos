from ryu.ofproto.ofproto_v1_3 import OFPMPF_REQ_MORE
from ryu.lib import hub

class PortListener(object):
    def __init__(self, datapathes, sleep_time):
        super(PortListener, self).__init__()
        self.datapathes = datapathes
        self.sleep_time = sleep_time

    def _send_port_desc_status_request(self, datapath):
        ofp_parser = datapath.ofproto_parser
        req = ofp_parser.OFPPortDescStatsRequest(datapath, OFPMPF_REQ_MORE)
        datapath.send_msg(req)

    def _send_port_statistics_stats_request(self, datapath):
        ofp = datapath.ofproto
        ofp_parser = datapath.ofproto_parser

        req = ofp_parser.OFPPortStatsRequest(datapath, OFPMPF_REQ_MORE, ofp.OFPP_ANY)
        datapath.send_msg(req)

    def inquiry_all_port_desc_stats(self):
        hub.sleep(self.sleep_time)
        for dp in self.datapathes:
            self._send_port_desc_status_request(dp)

    def inquiry_all_port_statistics_stats(self):
        hub.sleep(self.sleep_time)
        for dp in self.datapathes:
            self._send_port_desc_status_request(dp)

    def port_statistics_stats_handler(self, ev):
        print(ev.msg.body)

    def port_desc_stats_handler(self, ev):
        print(ev.msg.body)