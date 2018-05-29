from ryu.ofproto import ofproto_v1_3 as ofp13
from Util import Util as U

class MeterModifier(object):
    def __init__(self, meters):
        super(MeterModifier, self)

        self.meters = meters
        self.bands = {}                     # {band_id -> speed}

    def _get_new_meter_id(self, datapath):
        dpid = datapath.id
        all_id = list(self.meters[dpid].keys())
        if len(all_id) == 0:
            return 1
        list.sort(all_id)
        return all_id[-1] + 1

    def _get_new_band_id(self):
        all_id = list(self.bands.keys())
        if len(all_id) == 0:
            return 1
        list.sort(all_id)
        return all_id[-1] + 1

    def add_meter(self, datapath, speed, flags=ofp13.OFPMF_KBPS):
        dpid = datapath.id
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        all_band_id = []

        for (meter_id, band_id) in self.meters[dpid].items():
            all_band_id.append((meter_id, band_id))

        final_meter_id = -1
        final_band_id = -1
        for (meter_id, band_id) in all_band_id:
            if self.bands[band_id].rate == speed:
                final_meter_id = meter_id
                final_band_id = band_id
                break

        if final_meter_id == -1:
            final_meter_id = self._get_new_meter_id(datapath)
            final_band_id = self._create_new_band(datapath, speed)

            meter_mod = parser.OFPMeterMod(datapath=datapath,
                                       command=ofp13.OFPMC_ADD,
                                       flags=flags,
                                       meter_id=final_meter_id,
                                       bands=[self.bands[final_band_id]])
            datapath.send_msg(meter_mod)

        U.add2DimDict(self.meters, dpid, final_meter_id, final_band_id)
        return final_meter_id

    def _create_new_band(self, datapath, speed, burst_size=10):
        parser = datapath.ofproto_parser
        new_band_id = self._get_new_band_id()

        band = parser.OFPMeterBandDrop(speed, burst_size)
        self.bands[new_band_id] = band
        return new_band_id


