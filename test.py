import networkx as nx
import matplotlib.pyplot as plt

if __name__ == '__main__':
    G = nx.Graph()
    dic1 = [(1, 2, {'weight': 1}), (2, 4, {'weight': 2}),

            (1, 3, {'weight': 3}), (3, 4, {'weight': 4}),

            (1, 4, {'weight': 5}), (5, 6, {'weight': 6})]

    G.add_edges_from(dic1)

    nx.draw(G)
    plt.show()

    print(nx.shortest_path(G, source=2, target=3))
