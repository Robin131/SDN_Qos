from collections import defaultdict
from heapq import *
import copy

class RouteCalculater(object):
    """docstring for ClassName"""
    def __init__(self, port_speed):
        super(RouteCalculater, self).__init__()
        print("ERROR!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("Do not initialize this class!!!!!!")


    @classmethod
    def dijkstra_raw(cls,edges, from_node, to_node):
        g = defaultdict(list)
        for l,r,c in edges:
            g[l].append((c,r))
        q, seen = [(0,from_node,())], set()
        while q:
            (cost,v1,path) = heappop(q)
            # cost = -cost
            if v1 not in seen:
                seen.add(v1)
                path = (v1, path)
                if v1 == to_node:
                    return cost,path
                for c, v2 in g.get(v1, ()):
                    # c = -c
                    if v2 not in seen:
                        heappush(q, (cost+c, v2, path))
        return float("inf"),[]


    @classmethod
    def dijkstra(cls,edges, from_node, to_node):
        len_shortest_path = -1
        ret_path=[]
        length,path_queue = cls.dijkstra_raw(edges, from_node, to_node)
        # print("=======")
        # print(path_queue)
        # print("=======")
        if len(path_queue)>0:
            len_shortest_path = length        ## 1. Get the length firstly;
            ## 2. Decompose the path_queue, to get the passing nodes in the shortest path.
            left = path_queue[0]
            ret_path.append(left)        ## 2.1 Record the destination node firstly;
            right = path_queue[1]
            while len(right)>0:
                left = right[0]
                ret_path.append(left)    ## 2.2 Record other nodes, till the source-node.
                right = right[1]
            ret_path.reverse()    ## 3. Reverse the list finally, to make it be normal sequence.
        return len_shortest_path,ret_path


    @classmethod
    def route_calculater(cls,graph_init,src_dp,dst_dp):
        edges = []
        graph_norm = copy.deepcopy(graph_init)
        for key1 in graph_norm:
            for key2 in graph_norm[key1]:
                graph_norm[key1][key2]=1.00/graph_norm[key1][key2]

        dp_nodes = graph_norm.keys()
        print(dp_nodes)

        print(len(dp_nodes))
        graph_length=len(dp_nodes)
        for dp_source in dp_nodes:
            for dp_dest in graph_norm[dp_source]:
                assert dp_source!=dp_dest
                edges.append((dp_source,dp_dest,graph_norm[dp_source][dp_dest]))
        print(edges)

        for nodes in graph_init:
            for in_nodes in graph_init[nodes]:
                print("node: %d,  to_node %d--bandwidth %.3f" %
                    (nodes, in_nodes, graph_init[nodes][in_nodes]))

        for nodes in graph_norm:
            for in_nodes in graph_norm[nodes]:
                print("node: %d,  to_node %d--cost %.3f" %
                    (nodes, in_nodes, graph_norm[nodes][in_nodes]))


        print("=== Result ===")
        length,Shortest_path = cls.dijkstra(edges, src_dp, dst_dp)
        if length!=-1:
            print('length = ',length)
            print('The shortest path is ',Shortest_path)
        else:
            print("Source or dest datapath does not exist or"\
                " no path connects these two datapaths")

        return Shortest_path


# testing =========================================================
if __name__ == '__main__':
    graph_init = {1011:{1012:2.0,1013:1},1012:{1011:2,1014:3},
    1013:{1011:1,1015:5},1014:{1012:3,1015:5},1015:{1013:5,1014:5}}
    src_dp = 1011
    dst_dp = 1015
    RouteCalculater.route_calculater(graph_init,src_dp,dst_dp)