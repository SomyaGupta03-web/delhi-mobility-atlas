import pickle
import networkx as nx
import osmnx as ox

G = ox.load_graphml("data/interim/delhi_walk_network.graphml")
print(f"Raw graph: {len(G.nodes)} nodes, {len(G.edges)} edges")

components = list(nx.weakly_connected_components(G))
largest = max(components, key=len)
G = G.subgraph(largest).copy()
print(f"Largest connected component: {len(G.nodes)} nodes, {len(G.edges)} edges "
      f"({len(components)} components total)")

WALK_SPEED_MPS = 1.4
for u, v, k, data in G.edges(keys=True, data=True):
    data["weight_min"] = float(data["length"]) / (WALK_SPEED_MPS * 60)

with open("data/interim/delhi_walk_network_weighted.pkl", "wb") as f:
    pickle.dump(G, f)