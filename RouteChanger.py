from route_calculater import RouteCalculater
from ryu.lib import hub

class RouteChanger(object):
    def __init__(self, port_speed, flow_manager, dpid_to_dpid):
        super(RouteChanger, self).__init__()
        self.port_speed = port_speed
        self.flow_manager = flow_manager
        self.dpid_to_dpid = dpid_to_dpid

    def change_route(self):
        dpid1 = 1
        dpid2 = 5

        hub.sleep(20)
        print(self.port_speed)
        path = RouteCalculater.route_calculater(self.port_speed, dpid1, dpid2)
        path = self._get_path_in_right_format(path)
        self.flow_manager.change_route(path)
        # test
        print('finish changing route, the new route is ', path)


    def _get_path_in_right_format(self, origin_path):
        path = []
        for i in range(0, len(origin_path)):
            if i == len(origin_path) - 1:
                path.append((origin_path[-1], -1))
                return path
            else:
                for key,value in self.dpid_to_dpid.items():
                    if key[0] == origin_path[i] and value == origin_path[i+1]:
                        path.append((origin_path[i], key[1]))






