import networkx as nx

if __name__=='__main__':
    d = {'a': 1, 'b': 4, 'c': 2}
    c = sorted(d.items(), key=lambda x: x[1])[0][0]

    print(c)


    # G = nx.DiGraph()
    # G.add_node(1)
    # G.add_node(2)
    # G.add_node(3)
    # G.add_node(5)
    # G.add_node(4)
    #
    # G.add_edge(3, 1)
    # G.add_edge(2, 4)
    # G.add_edge(3, 4)
    # G.add_edge(3, 5)
    # G.add_edge(4, 5)
    #
    # p = nx.shortest_path_length(G, source=3)
    # print(p)